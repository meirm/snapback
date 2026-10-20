#!/usr/bin/env bash
#
# snapback.sh — project-aware snapshot backups with hard-link rotation.
#
# Bash implementation of snapback. Same commands as the Python CLI, and the same
# safety rules:
#
#   * the snapshot directory is configuration, not a hardcoded name, and it is
#     excluded from its own snapshots;
#   * a restore never deletes anything unless you ask for it with --full, and even
#     then it protects .git, gitignored paths, the snapshot directory and the
#     configuration file;
#   * a failing rsync aborts with a non-zero status instead of reporting success.
#
# Usage:
#   snapback.sh init [--local] [--snapshots-dir DIR]
#   snapback.sh hourly|daily|weekly|monthly [--dry-run]
#   snapback.sh tag <snapshot> <description>
#   snapback.sh list
#   snapback.sh recover <snapshot> [--dry-run] [--keep-existing|--full]
#   snapback.sh undel <snapshot> [--dry-run]
#   snapback.sh sampleconfig
#   snapback.sh help
#
# The original flag form (--hourly, --recover X, --tag A B, ...) still works so
# existing cron entries keep running.
#
set -euo pipefail

VERSION="2.2.0-bash"
PROG="${0##*/}"

# ── Defaults, overridden by the configuration file ───────────────────────────
DIRS='.'
TARGETBASE=''
RSYNC_PARAMS=''
h_snaps=23   # hourly snapshots kept
d_snaps=7    # daily snapshots kept
w_snaps=4    # weekly snapshots kept
m_snaps=12   # monthly snapshots kept

# ── State ───────────────────────────────────────────────────────────────────
is_local=0
PROJECT_ROOT=''
config_file=''
config_file_set=0
dry_run=0

die()  { printf '%s: error: %s\n' "$PROG" "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }
warn() { printf '%s: warning: %s\n' "$PROG" "$*" >&2; }

# ── Portable helpers ────────────────────────────────────────────────────────
_mtime() {
    stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0
}

_human_age() {
    local s="$1"
    if   (( s < 60 ));    then printf '%ss ago' "$s"
    elif (( s < 3600 ));  then printf '%sm ago' "$(( s / 60 ))"
    elif (( s < 86400 )); then printf '%sh ago' "$(( s / 3600 ))"
    else                       printf '%sd ago' "$(( s / 86400 ))"
    fi
}

_absolute() {  # $1 path, $2 base for relative paths
    local p="$1" base="$2"
    if [[ "$p" == /* ]]; then printf '%s\n' "${p%/}"
    else ( cd "$base" 2>/dev/null && cd "$p" 2>/dev/null && pwd -P ) || printf '%s\n' "${base%/}/${p#./}"
    fi
}

# ── Configuration ───────────────────────────────────────────────────────────
load_config() {
    local rc="$1"
    [[ -f "$rc" ]] || die "configuration file not found: $rc"

    if [[ "$rc" == "./.snapshotrc" || "$(cd "$(dirname "$rc")" && pwd -P)/$(basename "$rc")" == "$(pwd -P)/.snapshotrc" ]]; then
        is_local=1
    fi

    # The configuration file is plain shell assignments; read it leniently so an
    # unset variable in it cannot abort the run.
    set +u
    # shellcheck disable=SC1090
    source "$rc"
    set -u

    config_file="$rc"
    DIRS="${DIRS:-.}"
    TARGETBASE="${TARGETBASE:-.snapshots}"
    RSYNC_PARAMS="${RSYNC_PARAMS:-}"
    h_snaps="${h_snaps:-23}"
    d_snaps="${d_snaps:-7}"
    w_snaps="${w_snaps:-4}"
    m_snaps="${m_snaps:-12}"

    if (( is_local )); then
        PROJECT_ROOT="$(cd "$(dirname "$rc")" && pwd -P)"
        [[ "$TARGETBASE" == /* ]] && die "TARGETBASE must be a relative path inside the project in project-local mode (got: $TARGETBASE)"
        [[ "$TARGETBASE" == *..* ]] && die "TARGETBASE must not escape the project (got: $TARGETBASE)"
        TARGETBASE="$PROJECT_ROOT/${TARGETBASE#./}"
    else
        [[ "$TARGETBASE" == /* ]] || die "TARGETBASE must be an absolute path in global mode (got: $TARGETBASE)"
        TARGETBASE="${TARGETBASE%/}"
    fi
}

# Find the configuration to use, in priority order:
#   1. --config PATH or $SNAPSHOTRC
#   2. ./.snapshotrc   (project-local mode)
#   3. ~/.snapshotrc   (global mode)
resolve_config() {
    if (( config_file_set )); then
        load_config "$config_file"
    elif [[ -n "${SNAPSHOTRC:-}" ]]; then
        load_config "$SNAPSHOTRC"
    elif [[ -f "./.snapshotrc" ]]; then
        load_config "./.snapshotrc"
    elif [[ -f "$HOME/.snapshotrc" ]]; then
        load_config "$HOME/.snapshotrc"
    else
        die "no configuration found: run '$PROG init --local' for a project, or '$PROG sampleconfig > ~/.snapshotrc' for global mode"
    fi
}

# ── rsync arguments ─────────────────────────────────────────────────────────
# Paths that a snapshot never contains, and that a restore must therefore never
# delete: .git, gitignored content, the snapshot directory itself and the config.
# Explicit --exclude/--exclude-from are used because merge-rule filters
# (--filter=':- .gitignore') do not protect paths from rsync --delete.
EXCLUDES=()
build_excludes() {
    local exclude_from="${1:-}"
    local base_name
    base_name="$(basename "$TARGETBASE")"
    EXCLUDES=(--exclude=.git --exclude="$base_name" --exclude="$(basename "$config_file")")
    if [[ -n "$exclude_from" && -f "$exclude_from/.gitignore" ]]; then
        EXCLUDES+=(--exclude-from="$exclude_from/.gitignore")
    fi
}

# ── Sources ─────────────────────────────────────────────────────────────────
# Local mode snapshots the whole project; global mode snapshots each DIRS entry
# under its own name inside the snapshot.
SOURCES_LIVE=()
SOURCES_REL=()
collect_sources() {
    SOURCES_LIVE=()
    SOURCES_REL=()
    if (( is_local )); then
        SOURCES_LIVE=("$PROJECT_ROOT")
        SOURCES_REL=(".")
    else
        local d
        for d in $DIRS; do
            SOURCES_LIVE+=("${d%/}")
            SOURCES_REL+=("$(basename "${d%/}")")
        done
    fi
    (( ${#SOURCES_LIVE[@]} )) || die "DIRS is empty: nothing to snapshot"
}

# ── Rotation ────────────────────────────────────────────────────────────────
rotate() {  # $1 kind, $2 max
    local kind="$1" max="$2" i next
    if [[ -d "$TARGETBASE/$kind-$max" ]]; then
        if (( dry_run )); then info "DRY RUN: would remove $kind-$max"
        else rm -rf "$TARGETBASE/$kind-$max"; fi
    fi
    for (( i = max; i >= 1; i-- )); do
        next=$(( i - 1 ))
        if [[ -d "$TARGETBASE/$kind-$next" ]]; then
            if (( dry_run )); then info "DRY RUN: would move $kind-$next -> $kind-$i"
            else mv "$TARGETBASE/$kind-$next" "$TARGETBASE/$kind-$i"; fi
        fi
    done
    if [[ -d "$TARGETBASE/$kind-0" ]]; then
        if (( dry_run )); then info "DRY RUN: would hard-link $kind-0 -> $kind-1"
        else cp -al "$TARGETBASE/$kind-0" "$TARGETBASE/$kind-1"; fi
    fi
}

rsync_snapshot_into() {  # $1 destination snapshot dir
    local dest="$1" idx
    # Exclude .git, the snapshot directory, the config and gitignored content, so a
    # snapshot never contains the tool's own state or the repository internals.
    build_excludes "$( (( is_local )) && printf '%s' "$PROJECT_ROOT" || printf '' )"
    mkdir -p "$dest"
    for idx in "${!SOURCES_LIVE[@]}"; do
        local live="${SOURCES_LIVE[$idx]}" rel="${SOURCES_REL[$idx]}"
        local into="$dest"
        [[ "$rel" != "." ]] && into="$dest/$rel"
        mkdir -p "$into"
        local -a args=(-a --delete "${EXCLUDES[@]}")
        # RSYNC_PARAMS is a space-separated list of extra flags, so word splitting is
        # intended here (e.g. RSYNC_PARAMS='--max-size=10m --exclude=*.pyc').
        # shellcheck disable=SC2206
        [[ -n "$RSYNC_PARAMS" ]] && args+=($RSYNC_PARAMS)
        (( dry_run )) && args+=(--dry-run)
        info "Running: rsync ${args[*]} ${live}/ ${into}/"
        rsync "${args[@]}" "$live/" "$into/" \
            || die "rsync failed (exit $?) while snapshotting $live — snapshot is incomplete"
    done
}

# ── Commands ────────────────────────────────────────────────────────────────
do_backup() {  # $1 kind, $2 max, $3 source snapshot for the coarser rotation
    local kind="$1" max="$2" carry="${3:-}"
    if [[ -n "$carry" ]]; then
        rotate "$kind" "$max"
        if [[ ! -d "$TARGETBASE/$carry" ]]; then
            warn "$carry does not exist yet; nothing to base $kind-0 on (run an hourly first)"
            return 0
        fi
        if (( dry_run )); then info "DRY RUN: would hard-link $carry -> $kind-0"
        else rm -rf "$TARGETBASE/$kind-0"; cp -al "$TARGETBASE/$carry" "$TARGETBASE/$kind-0"; fi
        return 0
    fi
    rotate "$kind" "$max"
    mkdir -p "$TARGETBASE/$kind-0"
    rsync_snapshot_into "$TARGETBASE/$kind-0"
    if (( dry_run )); then info "DRY RUN: nothing was changed"
    else info "Backup completed to $TARGETBASE/$kind-0"; fi
}

do_recover() {  # $1 snapshot, $2 mode: merge|keep|full
    local snap="$1" mode="$2" idx
    local from="$TARGETBASE/$snap"
    [[ -d "$from" ]] || die "snapshot not found: $from"

    build_excludes "$from"
    local -a args=(-a -v "${EXCLUDES[@]}")
    case "$mode" in
        keep) args+=(--ignore-existing) ;;
        full) args+=(--delete) ;;
    esac
    (( dry_run )) && args+=(--dry-run)

    for idx in "${!SOURCES_LIVE[@]}"; do
        local live="${SOURCES_LIVE[$idx]}" rel="${SOURCES_REL[$idx]}"
        local fromdir="$from"
        [[ "$rel" != "." ]] && fromdir="$from/$rel"
        [[ -d "$fromdir" ]] || { warn "no $rel in snapshot $snap; skipping"; continue; }

        info "Running: rsync ${args[*]} ${fromdir}/ ${live}/"
        local rc=0
        rsync "${args[@]}" "$fromdir/" "$live/" || rc=$?
        if (( rc != 0 )); then
            printf '%s: error: rsync failed with status %s while restoring %s\n' "$PROG" "$rc" "$live" >&2
            printf '%s: the project was left partially restored. Protected paths (.git, gitignored\n' "$PROG" >&2
            printf '%s: files, %s, %s) were not touched.\n' "$PROG" "$(basename "$TARGETBASE")" "$(basename "$config_file")" >&2
            exit 1
        fi
    done
    if (( dry_run )); then info "DRY RUN: nothing was changed"
    else info "Recovered $snap into $( (( is_local )) && printf '%s' "$PROJECT_ROOT" || printf '%s' "$DIRS")"; fi
}

do_undel() {  # $1 snapshot
    local snap="$1" idx
    local from="$TARGETBASE/$snap"
    [[ -d "$from" ]] || die "snapshot not found: $from"

    build_excludes "$from"
    local -a args=(-a -v "${EXCLUDES[@]}" --ignore-existing)
    (( dry_run )) && args+=(--dry-run)

    for idx in "${!SOURCES_LIVE[@]}"; do
        local live="${SOURCES_LIVE[$idx]}" rel="${SOURCES_REL[$idx]}"
        local fromdir="$from"
        [[ "$rel" != "." ]] && fromdir="$from/$rel"
        [[ -d "$fromdir" ]] || continue
        info "Running: rsync ${args[*]} ${fromdir}/ ${live}/"
        rsync "${args[@]}" "$fromdir/" "$live/" || die "rsync failed (exit $?) while undeleting"
    done
    if (( dry_run )); then info "DRY RUN: nothing was changed"
    else info "Undeleted files from $snap (existing files untouched)"; fi
}

do_tag() {  # $1 snapshot, $2 tag name
    local snap="$1" tag="$2"
    local from="$TARGETBASE/$snap" to="$TARGETBASE/$tag"
    [[ -d "$from" ]] || die "snapshot not found: $from"
    [[ -e "$to" ]] && die "tag already exists: $to"
    [[ "$tag" == */* ]] && die "tag name must not contain a slash"
    if (( dry_run )); then info "DRY RUN: would create tag '$tag' from '$snap'"
    else cp -al "$from" "$to"; info "Created tag '$tag' from '$snap'"; fi
}

do_list() {
    [[ -d "$TARGETBASE" ]] || die "snapshot directory not found: $TARGETBASE"
    local now entry name age
    now="$(date +%s)"
    info "Snapshots in $TARGETBASE:"
    info ""
    # shellcheck disable=SC2012
    while IFS= read -r entry; do
        name="$(basename "$entry")"
        age="$(_human_age $(( now - $(_mtime "$entry") )))"
        printf '  %-16s (%s)\n' "$name" "$age"
    done < <(ls -1dt "$TARGETBASE"/*/ 2>/dev/null)
    info ""
    info "$(ls -1d "$TARGETBASE"/*/ 2>/dev/null | wc -l | tr -d ' ') snapshots"
}

sampleconfig() {
    cat <<'EOF'
# snapback configuration — sample
#
# project-local:  <project>/.snapshotrc   (snapback.sh init --local)
# global:         ~/.snapshotrc           (snapback.sh sampleconfig > ~/.snapshotrc)

# Project-local mode: snapshot the whole project, keep snapshots inside it.
DIRS='.'
TARGETBASE='./.snapshots'   # any directory inside the project
RSYNC_PARAMS=''

# Retention (optional):
# h_snaps=23
# d_snaps=7
# w_snaps=4
# m_snaps=12

# Global mode instead: absolute paths, snapshots outside the project.
# DIRS='/home/you/Documents /home/you/Projects'
# TARGETBASE='/home/you/.Snapshots'
EOF
}

usage() {
    cat <<EOF
$PROG $VERSION — project-aware snapshot backups

Usage:
  $PROG init [--local] [--snapshots-dir DIR]   set up snapshots in this project
  $PROG hourly|daily|weekly|monthly [--dry-run]
  $PROG tag <snapshot> <description>           keep a snapshot beyond rotation
  $PROG list                                   show snapshots and their age
  $PROG recover <snapshot> [--dry-run] [--keep-existing|--full]
  $PROG undel <snapshot> [--dry-run]           restore deleted files only
  $PROG sampleconfig                           print a sample configuration
  $PROG help

Restoring:
  recover                 restores the snapshot, never deletes anything
  recover --keep-existing restores only missing files; never overwrites
  recover --full          full rollback: also deletes files added since, except
                          .git, gitignored paths, the snapshot directory and the
                          configuration file
  --dry-run               report what would happen, change nothing

Crontab:
  0  * * * *  $PROG hourly  >/dev/null 2>&1
  58 23 * * * $PROG daily   >/dev/null 2>&1
  56 22 * * 1 $PROG weekly  >/dev/null 2>&1
  0  1 1 * *  $PROG monthly >/dev/null 2>&1
EOF
}

# ── init ────────────────────────────────────────────────────────────────────
ensure_gitignore_entries() {  # $1 file, rest: entries; echoes 1 if it added any
    local f="$1"; shift
    [[ -f "$f" ]] || printf '# .gitignore\n' > "$f"
    local -a missing=()
    local e
    for e in "$@"; do
        grep -qxF "$e" "$f" 2>/dev/null || missing+=("$e")
    done
    (( ${#missing[@]} )) || { printf '0\n'; return 0; }
    {
        printf '\n# snapback - local snapshot backups\n'
        for e in "${missing[@]}"; do printf '%s\n' "$e"; done
    } >> "$f"
    printf '1\n'
}

do_init() {  # $1 local|global|auto, $2 snapshots dir (may be empty)
    local mode="$1" dir="${2:-}"

    if [[ "$mode" == "auto" ]]; then
        if [[ -d "./.git" ]]; then mode="local"; else mode="global"; fi
    fi
    # Asking for a snapshot directory only makes sense in a project.
    if [[ -n "$dir" && "$mode" != "local" ]]; then mode="local"; fi

    if [[ "$mode" == "local" ]]; then
        local rc="./.snapshotrc"
        dir="${dir:-.snapshots}"
        [[ "$dir" == /* ]] && die "--snapshots-dir must be relative to the project (got: $dir)"
        [[ "$dir" == *..* ]] && die "--snapshots-dir must not escape the project (got: $dir)"
        [[ "$dir" == "." || -z "$dir" ]] && die "--snapshots-dir must name a directory (got: '$dir')"
        dir="${dir#./}"
        dir="${dir%/}"

        if [[ -f "$rc" ]]; then
            info "Configuration already exists: $rc"
            load_config "$rc"          # honour the settings already in it
        else
            info "Creating project-local configuration..."
            {
                printf '# snapback - project-local configuration\n'
                printf "DIRS='.'\n"
                printf "TARGETBASE='./%s'\n" "$dir"
                printf "RSYNC_PARAMS=''\n"
            } > "$rc"
            info "✓ Created $rc"
        fi

        info "Updating .gitignore..."
        if [[ "$(ensure_gitignore_entries "./.gitignore" "$dir/" ".snapshotrc")" == "1" ]]; then
            info "✓ Added $dir/ and .snapshotrc to .gitignore"
        else
            info "✓ .gitignore already contains snapback entries"
        fi

        mkdir -p "./$dir"
        TARGETBASE="$(cd "$dir" && pwd -P)"
        config_file="$rc"
        is_local=1
    else
        local rc="${config_file:-$HOME/.snapshotrc}"
        [[ -f "$rc" ]] || die "configuration file not found: $rc — run '$PROG sampleconfig > $rc' first"
        load_config "$rc"
        info "Initializing snapshot directory structure in $TARGETBASE"
    fi

    local i
    for (( i = 0; i <= h_snaps; i++ )); do mkdir -p "$TARGETBASE/hour-$i"; done
    for (( i = 0; i <= d_snaps; i++ )); do mkdir -p "$TARGETBASE/day-$i"; done
    for (( i = 0; i <= w_snaps; i++ )); do mkdir -p "$TARGETBASE/week-$i"; done
    for (( i = 0; i <= m_snaps; i++ )); do mkdir -p "$TARGETBASE/month-$i"; done

    info ""
    info "✓ Snapshot directory ready: $TARGETBASE"
    info ""
    info "Next steps:"
    info "  1. Review the configuration"
    info "  2. Create your first snapshot: $PROG hourly"
    info "  3. Tag important states: $PROG tag hour-0 'description'"
}

# ── Argument parsing ────────────────────────────────────────────────────────
[[ "${1:-}" == "" ]] && { usage; exit 0; }

command -v rsync >/dev/null 2>&1 || die "rsync is required but was not found in PATH"

# Accept both the word form (hourly, recover X) and the original flag form
# (--hourly, --recover X) so existing cron entries keep working.
cmd=""
arg1=""
arg2=""
declare -a rest=()

while (( $# )); do
    case "$1" in
        --conf)      config_file="$2"; config_file_set=1; shift 2 ;;
        --config)    config_file="$2"; config_file_set=1; shift 2 ;;
        --dry-run)   dry_run=1; shift ;;
        --local)     cmd="init"; arg1="local"; shift ;;
        --init)      cmd="init"; arg1="global"; shift ;;
        --snapshots-dir) arg2="$2"; shift 2 ;;
        --hourly)    cmd="hourly"; shift ;;
        --daily)     cmd="daily"; shift ;;
        --weekly)    cmd="weekly"; shift ;;
        --monthly)   cmd="monthly"; shift ;;
        --recover)   cmd="recover"; arg1="$2"; shift 2 ;;
        --undel)     cmd="undel"; arg1="$2"; shift 2 ;;
        --tag)       cmd="tag"; arg1="$2"; arg2="$3"; shift 3 ;;
        --sampleconfig|-s) cmd="sampleconfig"; shift ;;
        --help|-h)   cmd="help"; shift ;;
        --keep-existing|--full)
                     rest+=("$1"); shift ;;
        -*)          die "unknown option: $1 (try '$PROG help')" ;;
        *)
            if   [[ -z "$cmd" ]]; then cmd="$1"
            elif [[ -z "$arg1" ]]; then arg1="$1"
            elif [[ -z "$arg2" ]]; then arg2="$1"
            else rest+=("$1"); fi
            shift ;;
    esac
done

case "$cmd" in
    help|"")  usage; exit 0 ;;
    sampleconfig) sampleconfig; exit 0 ;;
esac

# init resolves its own configuration; everything else needs one.
if [[ "$cmd" == "init" ]]; then
    do_init "${arg1:-auto}" "${arg2:-}"
    exit 0
fi

resolve_config
collect_sources

# A restore must know how it is allowed to treat the target.
mode="merge"
for a in ${rest[@]+"${rest[@]}"}; do
    case "$a" in
        --keep-existing) mode="keep" ;;
        --full)          mode="full" ;;
    esac
done

case "$cmd" in
    hourly)  do_backup hour  "$h_snaps" ;;
    daily)   do_backup day   "$d_snaps" "hour-$h_snaps" ;;
    weekly)  do_backup week  "$w_snaps" "day-$d_snaps" ;;
    monthly) do_backup month "$m_snaps" "week-$w_snaps" ;;
    tag)     [[ -n "$arg1" && -n "$arg2" ]] || die "usage: $PROG tag <snapshot> <description>"
             do_tag "$arg1" "$arg2" ;;
    list)    do_list ;;
    recover) [[ -n "$arg1" ]] || die "usage: $PROG recover <snapshot> [--dry-run] [--keep-existing|--full]"
             do_recover "$arg1" "$mode" ;;
    undel)   [[ -n "$arg1" ]] || die "usage: $PROG undel <snapshot> [--dry-run]"
             do_undel "$arg1" ;;
    *)       usage; exit 1 ;;
esac
