---
name: snapback-project-snapshots
description: "Use when taking or restoring project snapshots with snapback."
version: 1.0.0
author: snapback
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [snapshots, rollback, backups, agentic-workflows]
    related_skills: [project-snapshot-backups]
---

# Taking and restoring project snapshots with snapback

## When to Use

Before a risky edit, a refactor, or an experiment you may need to undo; when an agent session
needs a checkpoint it can roll back to; or when you must restore a project to an earlier state.

## Setup (once per project)

```bash
cd /path/to/project
snapback init --local                          # snapshots in ./.snapshots
snapback init --local --snapshots-dir .snapback # or any directory inside the project
```

This writes `./.snapshotrc`, creates the snapshot directory, and adds both it and `.snapshotrc`
to `.gitignore`. The snapshot directory is excluded from its own snapshots, and so are `.git`,
gitignored paths and the config file.

Configuration reference: `snapshotrc.example` in this repo. Run `snapback list` to see snapshots.

## The working loop

```bash
snapback hourly                 # checkpoint (also: daily, weekly, monthly)
snapback tag hour-0 "before-refactor"   # keep an important state beyond rotation
snapback list                   # what exists, and how old each snapshot is
snapback recover --dry-run hour-1       # preview a rollback first
```

Tag anything you may need later: rotation eventually reuses `hour-*`, `day-*`, `week-*` and
`month-*` names, but tags are kept indefinitely.

## Restoring — choose deliberately

| Goal | Command | Effect |
|---|---|---|
| Roll the project back | `snapback recover hour-1` | Restores the snapshot, deletes files added since (protected paths untouched) |
| Preview a rollback | `snapback recover --dry-run hour-1` | Reports what would change; changes nothing |
| Restore only what is missing | `snapback recover --keep-existing hour-1` | Never deletes or overwrites — safe when unsure |
| Undelete files only | `snapback undel hour-1` | Restores missing files; never deletes |

**Prefer `--keep-existing` or `undel` unless you specifically want the whole tree rolled back.**

Protected from deletion by any restore: `.git`, gitignored files and directories, the snapshot
directory, and `.snapshotrc`. Everything else the snapshot does not contain is removed by a full
`recover`.

## Verify a restore

After any restore, confirm the project is intact before continuing:

```bash
test -d .git && echo "repository intact"
test -f .snapshotrc && echo "config intact"
snapback list
```

Then check that the files you expected came back, and read one of them — a restore that reports
success is not proof that the content is what you wanted.

## Rules

- **Never run the first restore of a project you care about.** Rehearse in a copy: snapshots are
  cheap, a destroyed working tree is not.
- **Snapshot before risky edits, not after.** A checkpoint taken after the damage is worthless.
- **Tag before rotating.** A tag survives retention; `hour-*` names do not.
- **The snapshot directory must stay inside the project.** `init` refuses absolute or escaping
  paths; `TARGETBASE` in `.snapshotrc` is validated against the project root.
- **Space is shared, not copied:** unchanged files are hard-linked between snapshots, so a
  project with many snapshots costs roughly its own size plus the changes.
- **Check what was excluded.** Ignored files are not in snapshots, which is why they are protected
  during a restore — do not expect a rollback to bring back something that was never captured.
