#!/usr/bin/env bash
#
# Integration tests for snapback.sh.
#
# These run the real tool against real directories. Mocked or stubbed rsync calls
# cannot see the defects that matter here — a restore that deletes .git, a
# snapshot directory that snapshots itself, a failure reported as success — so
# every check below asserts on files on disk after a real run.
#
# Usage: bash tests/bash/test_snapback.sh
#
set -uo pipefail

# Override SNAP to run the suite against the tool under another interpreter, e.g.
# SNAP=/tmp/wrapper bash tests/bash/test_snapback.sh, where the wrapper execs an older bash.
SNAP="${SNAP:-$(cd "$(dirname "$0")/../.." && pwd)/snapback.sh}"
WORK="$(mktemp -d)"
trap 'chmod -R u+rwX "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT

pass=0
fail=0

check() {  # description, expected, actual
    if [[ "$2" == "$3" ]]; then
        pass=$(( pass + 1 )); printf '  ok   %s\n' "$1"
    else
        fail=$(( fail + 1 ))
        printf '  FAIL %s\n         expected: %s\n         actual:   %s\n' "$1" "$2" "$3"
    fi
}

section() { printf '\n%s\n' "$1"; }

# A throwaway project: a repository marker, gitignored content, a config file.
new_project() {  # $1 name -> echoes the directory
    local d="$WORK/$1"
    mkdir -p "$d/src" "$d/ignored" "$d/.git"
    printf 'ref: refs/heads/main\n' > "$d/.git/HEAD"
    printf 'ignored/\n' > "$d/.gitignore"
    printf 'v1\n'    > "$d/src/app.txt"
    printf 'keep\n'  > "$d/notes.txt"
    printf 'secret\n'> "$d/ignored/secret.txt"
    printf '%s\n' "$d"
}

[[ -x "$SNAP" ]] || { printf 'not executable: %s\n' "$SNAP" >&2; exit 1; }

# ── 1. init in a project ────────────────────────────────────────────────────
section "init --local"
P="$(new_project init)"; cd "$P" || exit 1
"$SNAP" init --local >/dev/null
check "writes .snapshotrc"          "TARGETBASE='./.snapshots'" "$(grep TARGETBASE .snapshotrc)"
check "creates the snapshot dir"    "yes" "$([ -d .snapshots ] && echo yes)"
check "ignores the snapshot dir"    "yes" "$(grep -qxF '.snapshots/' .gitignore && echo yes)"
check "ignores the config"          "yes" "$(grep -qxF '.snapshotrc' .gitignore && echo yes)"

# ── 2. taking snapshots ─────────────────────────────────────────────────────
section "hourly"
"$SNAP" hourly >/dev/null
check "hour-0 holds the file"       "v1" "$(cat .snapshots/hour-0/src/app.txt)"
printf 'v2\n' > src/app.txt
"$SNAP" hourly >/dev/null
check "hour-0 is current"           "v2" "$(cat .snapshots/hour-0/src/app.txt)"
check "hour-1 kept the older state" "v1" "$(cat .snapshots/hour-1/src/app.txt)"

# ── 3. default restore: restores, never deletes ─────────────────────────────
section "recover (default)"
rm src/app.txt
printf 'added\n' > added.txt
"$SNAP" recover hour-1 >/dev/null
check "restores the deleted file"   "v1"    "$(cat src/app.txt)"
check "leaves files added since"    "added" "$(cat added.txt)"

# ── 4. protected paths ──────────────────────────────────────────────────────
section "protected paths"
check ".git survives"               "yes" "$([ -f .git/HEAD ] && echo yes)"
check "gitignored content survives" "yes" "$([ -f ignored/secret.txt ] && echo yes)"
check "the config survives"         "yes" "$([ -f .snapshotrc ] && echo yes)"
check "the snapshot dir survives"   "yes" "$([ -d .snapshots/hour-1 ] && echo yes)"

# ── 5. --full is the only destructive mode, and still protects ──────────────
section "recover --full"
"$SNAP" recover hour-1 --full >/dev/null
check "removes files added since"   "no"  "$([ -f added.txt ] && echo yes || echo no)"
check "still keeps .git"            "yes" "$([ -f .git/HEAD ] && echo yes)"
check "still keeps ignored content" "yes" "$([ -f ignored/secret.txt ] && echo yes)"
check "still keeps the config"      "yes" "$([ -f .snapshotrc ] && echo yes)"
check "still keeps the snapshots"   "yes" "$([ -d .snapshots/hour-1 ] && echo yes)"

# ── 6. --keep-existing ──────────────────────────────────────────────────────
section "recover --keep-existing"
printf 'v3-broken\n' > src/app.txt
rm notes.txt
"$SNAP" recover hour-1 --keep-existing >/dev/null
check "does not overwrite"          "v3-broken" "$(cat src/app.txt)"
check "restores what is missing"    "keep"      "$(cat notes.txt)"

# ── 7. --dry-run ────────────────────────────────────────────────────────────
section "--dry-run"
printf 'v4\n' > src/app.txt
rm notes.txt
"$SNAP" recover hour-1 --dry-run >/dev/null
check "recover --dry-run changes nothing"     "v4" "$(cat src/app.txt)"
check "recover --dry-run restores nothing"    "no" "$([ -f notes.txt ] && echo yes || echo no)"
"$SNAP" hourly --dry-run >/dev/null
check "hourly --dry-run did not update hour-0" "v2" "$(cat .snapshots/hour-0/src/app.txt)"
check "hourly --dry-run does not rotate"      "v1" "$(cat .snapshots/hour-1/src/app.txt)"

# ── 8. a configured snapshot directory ──────────────────────────────────────
section "custom --snapshots-dir"
P2="$(new_project custom)"; cd "$P2" || exit 1
"$SNAP" init --local --snapshots-dir .snapback >/dev/null
check "config points at it"         "TARGETBASE='./.snapback'" "$(grep TARGETBASE .snapshotrc)"
check "it is gitignored"            "yes" "$(grep -qxF '.snapback/' .gitignore && echo yes)"
"$SNAP" hourly >/dev/null
check "snapshots land there"        "v1" "$(cat .snapback/hour-0/src/app.txt)"
check "no snapshot of the snapshots" "0" "$(find .snapback/hour-0 -maxdepth 1 -name '.snapback' | wc -l | tr -d ' ')"
check "no stray .snapshots dir"     "no" "$([ -d .snapshots ] && echo yes || echo no)"

# ── 9. the snapshot directory must stay in the project ──────────────────────
section "init refuses to escape the project"
P3="$(new_project badinit)"; cd "$P3" || exit 1
"$SNAP" init --local --snapshots-dir /tmp/elsewhere >/dev/null 2>&1
check "refuses an absolute path"    "1" "$?"
"$SNAP" init --local --snapshots-dir ../outside >/dev/null 2>&1
check "refuses a path outside"      "1" "$?"
check "wrote no config"             "no" "$([ -f .snapshotrc ] && echo yes || echo no)"

# ── 10. tags survive rotation ───────────────────────────────────────────────
section "tag"
P4="$(new_project tag)"; cd "$P4" || exit 1
"$SNAP" init --local >/dev/null
"$SNAP" hourly >/dev/null
"$SNAP" tag hour-0 baseline >/dev/null
printf 'v9\n' > src/app.txt
"$SNAP" hourly >/dev/null
check "the tag kept the old state"  "v1" "$(cat .snapshots/baseline/src/app.txt)"
check "the tag is listed"           "1" "$("$SNAP" list | grep -c baseline)"

# list is the command that computes ages from file metadata, which is where the
# BSD/GNU stat difference bites. Assert it runs clean and reports the summary.
check "list exits 0"                "0" "$("$SNAP" list >/dev/null 2>&1; echo $?)"
check "list prints the age summary" "1" "$("$SNAP" list | grep -c 'snapshots with data')"
check "list prints no raw errors"   "0" "$("$SNAP" list 2>&1 | grep -cE 'unbound variable|No such file')"

# ── 11. undel ───────────────────────────────────────────────────────────────
section "undel"
P5="$(new_project undel)"; cd "$P5" || exit 1
"$SNAP" init --local >/dev/null
"$SNAP" hourly >/dev/null
printf 'edited\n' > src/app.txt
rm notes.txt
"$SNAP" undel hour-0 >/dev/null
check "restores the deleted file"   "keep"   "$(cat notes.txt)"
check "leaves edited files alone"   "edited" "$(cat src/app.txt)"

# ── 12. a failing rsync is not reported as success ──────────────────────────
section "failure is loud"
P6="$(new_project ro)"; cd "$P6" || exit 1
"$SNAP" init --local >/dev/null
"$SNAP" hourly >/dev/null
rm src/app.txt
chmod 000 "$P6/.snapshots/hour-0"          # an unreadable snapshot must fail loudly
"$SNAP" recover hour-0 >/dev/null 2>&1
rc=$?
chmod 755 "$P6/.snapshots/hour-0"
check "exits non-zero"              "1" "$([ "$rc" -ne 0 ] && echo 1 || echo 0)"

# ── 13. global mode still works ─────────────────────────────────────────────
section "global mode (absolute DIRS, config outside the project)"
G="$WORK/global"; mkdir -p "$G/data"; cd "$G" || exit 1
printf 'g1\n' > "$G/data/f.txt"
printf "DIRS='%s/data'\nTARGETBASE='%s/snaps'\n" "$G" "$G" > "$G/rc"
"$SNAP" --config "$G/rc" init >/dev/null
"$SNAP" --config "$G/rc" hourly >/dev/null
check "snapshots the absolute source" "g1" "$(cat "$G/snaps/hour-0/data/f.txt")"
rm "$G/data/f.txt"
"$SNAP" --config "$G/rc" recover hour-0 >/dev/null
check "restores it"                   "g1" "$(cat "$G/data/f.txt")"

# ── 14. the original flag form still parses ─────────────────────────────────
section "backwards compatibility"
P7="$(new_project flags)"; cd "$P7" || exit 1
"$SNAP" --local --snapshots-dir .snapshots >/dev/null 2>&1 || true
"$SNAP" init --local >/dev/null
"$SNAP" --hourly >/dev/null
check "--hourly works"              "v1" "$(cat .snapshots/hour-0/src/app.txt)"
rm src/app.txt
"$SNAP" --undel hour-0 >/dev/null
check "--undel works"               "v1" "$(cat src/app.txt)"
"$SNAP" --tag hour-0 keepme >/dev/null
check "--tag works"                 "yes" "$([ -d .snapshots/keepme ] && echo yes)"
check "--help exits 0"              "0" "$("$SNAP" --help >/dev/null 2>&1; echo $?)"
check "unknown option fails"        "1" "$("$SNAP" --nonsense >/dev/null 2>&1; echo $?)"

# ── summary ─────────────────────────────────────────────────────────────────
printf '\n%s\n' "────────────────────────────────────────"
printf '%s passed, %s failed\n' "$pass" "$fail"
(( fail == 0 )) || exit 1
