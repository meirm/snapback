# Agentic Development with snapback

**Complete guide to using snapback for AI-assisted development workflows**

---

## Table of Contents

- [Overview](#overview)
- [Why Project-Local Snapshots for AI Agents](#why-project-local-snapshots-for-ai-agents)
- [Setup](#setup)
- [Basic Workflows](#basic-workflows)
- [Advanced Patterns](#advanced-patterns)
- [AI Agent Integration](#ai-agent-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

---

## Overview

**Agentic development** refers to software development workflows where AI agents (like GitHub Copilot, ChatGPT, Claude, or autonomous coding agents) assist in code generation, refactoring, and problem-solving. These workflows require:

- **Frequent checkpoints**: Save state before letting AI make changes
- **Quick rollbacks**: Revert experiments that don't work
- **Session isolation**: Separate development sessions don't interfere
- **Git integration**: Work alongside version control without conflicts

snapback's **project-local mode** is designed specifically for these workflows, providing lightweight, fast snapshots that complement (rather than replace) git version control.

## Why Project-Local Snapshots for AI Agents

### The Problem

Traditional version control (git) is excellent for finalized changes but can be cumbersome during rapid AI-assisted experimentation:

- **Commit overhead**: Creating git commits for every experiment creates noise
- **Branch proliferation**: Testing multiple AI suggestions requires many throwaway branches
- **Messy history**: Reverting experimental changes clutters git history
- **Build artifacts**: Git isn't designed for tracking large generated files

### The Solution

Project-local snapshots provide a **complementary safety net**:

1. **Instant checkpoints**: Snapshot before AI makes changes (seconds, not minutes)
2. **No git pollution**: Snapshots don't affect git history or require commits
3. **Fast rollbacks**: Revert experiments without git reset complexity
4. **Session state**: Capture entire working directory including build artifacts
5. **Gitignore-aware**: Respects `.gitignore` automatically

### Relationship with Git

```
┌─────────────────────────────────────────┐
│                                         │
│  Git Commits (finalized changes)        │
│  ├── feature-x                          │
│  ├── bug-fix-y                          │
│  └── refactor-z                         │
│                                         │
└─────────────────────────────────────────┘
            ▲
            │ git commit (after validation)
            │
┌───────────┴─────────────────────────────┐
│                                         │
│  snapback Snapshots (experiments)       │
│  ├── hour-0: "ai-suggestion-3-tested"   │
│  ├── hour-1: "ai-suggestion-2-failed"   │
│  ├── hour-2: "ai-suggestion-1-partial"  │
│  └── hour-3: "clean-baseline"           │
│                                         │
└─────────────────────────────────────────┘
```

**Workflow**:
1. Create snapback checkpoint (hour-0: "clean-baseline")
2. AI makes changes
3. Create checkpoint (hour-0: "ai-suggestion-1")
4. Test changes
5. If good: `git commit` and move forward
6. If bad: `snapback recover hour-1` (rollback)

## Setup

### Initial Project Setup

```bash
# Navigate to your project
cd ~/projects/my-ai-project

# Initialize project-local snapback (auto-detects git repos)
snapback init

# Verify setup
ls -la .snapshotrc .snapshots/
cat .gitignore  # Should include .snapshots/ and .snapshotrc
```

### Configuration Verification

```bash
# Check your local config
cat .snapshotrc
```

Should contain:
```bash
# snapback project-local configuration
DIRS='.'
TARGETBASE='./.snapshots'
RSYNC_PARAMS=''
```

### Gitignore Verification

Your `.gitignore` should now include (automatically added by `snapback init`):

```
# snapback - local snapshot backups
.snapshots/
.snapshotrc
```

## Basic Workflows

### Workflow 1: Simple AI-Assisted Feature

**Scenario**: AI generates a new function. Test it, then decide to keep or revert.

```bash
# 1. Create baseline snapshot
snapback hourly
snapback tag hour-0 "before-ai-feature"

# 2. AI generates feature
# (use your AI coding assistant to generate code)

# 3. Create checkpoint after AI changes
snapback hourly
snapback tag hour-0 "ai-generated-feature"

# 4. Test the feature
npm test
# or: python -m pytest
# or: cargo test

# 5. Decision point:
#    Option A - Tests pass, keep changes
git add .
git commit -m "Add AI-generated feature"

#    Option B - Tests fail, revert
snapback recover before-ai-feature
```

### Workflow 2: Multiple AI Iterations

**Scenario**: Try several AI suggestions until one works.

```bash
# 1. Start clean
snapback hourly
snapback tag hour-0 "baseline-v1"

# 2. First AI suggestion
# ... AI makes changes ...
snapback hourly
snapback tag hour-0 "attempt-1"
npm test
# Fails! ❌

# 3. Second AI suggestion (revert first)
snapback recover baseline-v1
# ... AI makes different changes ...
snapback hourly
snapback tag hour-0 "attempt-2"
npm test
# Fails again! ❌

# 4. Third AI suggestion (revert second)
snapback recover baseline-v1
# ... AI makes third approach ...
snapback hourly
snapback tag hour-0 "attempt-3-success"
npm test
# Success! ✅

# 5. Commit winning approach
git add .
git commit -m "Implement feature using approach #3"
```

### Workflow 3: Refactoring Safety

**Scenario**: AI refactors code. Want to compare before/after.

```bash
# 1. Snapshot before refactoring
snapback hourly
snapback tag hour-0 "pre-refactor"

# 2. AI refactors code
# ... large refactoring ...

# 3. Snapshot after refactoring
snapback hourly
snapback tag hour-0 "post-refactor"

# 4. Compare specific file
snapdiff 1 src/important-module.js
# Opens vimdiff showing before/after

# 5. Check all tests still pass
npm test

# 6. If tests pass, commit refactoring
git add .
git commit -m "Refactor module structure"

# 7. If tests fail, investigate or revert
snapback recover pre-refactor
```

### Workflow 4: Bug Fix Experimentation

**Scenario**: AI suggests multiple bug fixes. Try each one.

```bash
# 1. Snapshot current (buggy) state
snapback hourly
snapback tag hour-0 "bug-present"

# 2. AI suggests fix #1
# ... apply fix ...
snapback hourly
# Test manually or automated
npm test
# Bug still present ❌

# 3. Try AI fix #2 (revert first)
snapback recover bug-present
# ... apply different fix ...
snapback hourly
# Test again
npm test
# Bug fixed! ✅

# 4. Document and commit
git add .
git commit -m "Fix bug XYZ (approach #2)"
```

## Advanced Patterns

### Pattern 1: Parallel Experimentation

**Scenario**: Test multiple AI approaches simultaneously using snapback tags.

```bash
# Create baseline
snapback hourly
snapback tag hour-0 "baseline"

# Approach A: Performance optimization
# ... AI optimizes ...
snapback hourly
snapback tag hour-0 "approach-a-perf"

# Switch to baseline, try approach B
snapback recover baseline

# Approach B: Memory optimization
# ... AI optimizes differently ...
snapback hourly
snapback tag hour-0 "approach-b-memory"

# Switch to baseline, try approach C
snapback recover baseline

# Approach C: Hybrid
# ... AI combines approaches ...
snapback hourly
snapback tag hour-0 "approach-c-hybrid"

# Compare performance
snapback recover approach-a-perf
npm run benchmark > results-a.txt

snapback recover approach-b-memory
npm run benchmark > results-b.txt

snapback recover approach-c-hybrid
npm run benchmark > results-c.txt

# Pick winner, commit
snapback recover approach-c-hybrid
git commit -am "Optimize using hybrid approach"
```

### Pattern 2: Session State Preservation

**Scenario**: End work session, resume next day with exact state.

```bash
# End of Day 1
snapback hourly
snapback tag hour-0 "end-of-day-2024-01-15"
git add .
git commit -m "WIP: Feature implementation"
git push

# Start of Day 2
git pull
snapback recover end-of-day-2024-01-15
# Now in exact same state as yesterday

# Continue work...
```

### Pattern 3: AI Code Review Integration

**Scenario**: Let AI review code, create checkpoint before accepting AI suggestions.

```bash
# Current state
snapback hourly
snapback tag hour-0 "before-ai-review"

# AI reviews code and suggests improvements
# Output: "Found 5 issues, here are fixes..."

# Apply AI's suggested fixes
# ... make changes ...

# Create checkpoint after AI review
snapback hourly
snapback tag hour-0 "after-ai-review"

# Test thoroughly
npm test
npm run lint
npm run type-check

# If all good, commit
git add .
git commit -m "Apply AI code review suggestions"

# If problems, compare changes
snapdiff 1 src/module.js
# Or revert entirely
snapback recover before-ai-review
```

### Pattern 4: Automated Checkpoint Integration

**Scenario**: Auto-create snapshots at key points in development workflow.

```bash
# Add to your package.json scripts
{
  "scripts": {
    "checkpoint": "snapback hourly",
    "tag": "snapback tag hour-0",
    "rollback": "snapback recover hour-1",
    "test-safe": "snapback hourly && npm test || snapback recover hour-1"
  }
}

# Usage
npm run checkpoint  # Create checkpoint
npm run tag "before-merge"  # Tag current state
npm run test-safe  # Test with automatic rollback on failure
```

## AI Agent Integration

### Integration with GitHub Copilot

GitHub Copilot generates code suggestions inline. Use snapback as a safety net:

```bash
# Before accepting large Copilot suggestions
snapback hourly && snapback tag hour-0 "pre-copilot-$(date +%Y%m%d-%H%M)"

# Accept Copilot suggestion(s)
# ... write code with Copilot ...

# Test immediately
npm test

# If tests fail, rollback
snapback recover pre-copilot-*
```

### Integration with ChatGPT/Claude

When getting code suggestions from chat interfaces:

```bash
# 1. Snapshot before applying suggestion
snapback hourly
snapback tag hour-0 "pre-chatgpt"

# 2. Copy-paste AI-generated code

# 3. Snapshot after applying
snapback hourly
snapback tag hour-0 "post-chatgpt-attempt-1"

# 4. Test
pytest tests/

# 5. If successful, commit
git add .
git commit -m "Implement feature using ChatGPT suggestion"

# 6. If unsuccessful, analyze diff and revert if needed
snapdiff 1 src/module.py
snapback recover pre-chatgpt
```

### Integration with Autonomous Agents

For autonomous coding agents (AutoGPT, BabyAGI, etc.) that make multiple sequential changes:

```bash
# Before starting agent
snapback hourly
snapback tag hour-0 "pre-agent-session"

# Agent makes multiple changes over time
# You can create intermediate checkpoints via agent's action system

# After agent completes
snapback hourly
snapback tag hour-0 "post-agent-session"

# Review all changes
snapdiff 1 .

# Selectively recover if needed
snapback list  # See all snapshots
snapback recover pre-agent-session  # Full rollback if necessary
```

### Scripting snapback Operations

Create wrapper scripts for common AI workflows:

```bash
# ~/scripts/ai-checkpoint.sh
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
snapback hourly
snapback tag hour-0 "ai-checkpoint-$TIMESTAMP"
echo "✓ Created checkpoint: ai-checkpoint-$TIMESTAMP"

# ~/scripts/ai-rollback.sh
#!/bin/bash
snapback list --tags | grep "ai-checkpoint"
read -p "Enter checkpoint name to rollback to: " CHECKPOINT
snapback recover "$CHECKPOINT"
echo "✓ Rolled back to: $CHECKPOINT"

# ~/scripts/ai-safe-test.sh
#!/bin/bash
snapback hourly
if "$@"; then
    echo "✓ Tests passed, checkpoint preserved"
else
    echo "✗ Tests failed, rolling back..."
    snapback recover hour-1
    exit 1
fi
```

## Best Practices

### General Best Practices

1. **Checkpoint Before AI Changes**
   - Always create snapshot before accepting AI suggestions
   - Tag important checkpoints with descriptive names

2. **Test Immediately**
   - Run tests immediately after AI changes
   - Don't accumulate untested AI-generated code

3. **Small Iterations**
   - Let AI make small, testable changes
   - Don't accept massive refactorings without checkpoints

4. **Document Tags**
   - Use descriptive tag names: `before-refactor`, `working-state`, `ai-suggestion-3`
   - Include timestamps for long sessions: `pre-ai-2024-01-15-14:30`

5. **Clean Up Regularly**
   - Delete old tagged snapshots you no longer need
   - Keep snapshot directory size manageable

### Workflow-Specific Practices

**For Feature Development**:
- Checkpoint at: start, after each AI iteration, before testing, before commit
- Tag pattern: `feature-x-baseline`, `feature-x-attempt-1`, `feature-x-working`

**For Refactoring**:
- Checkpoint at: before refactoring, after each major change, before finalizing
- Tag pattern: `pre-refactor-module-x`, `refactor-step-1`, `refactor-complete`

**For Bug Fixes**:
- Checkpoint at: with bug present, after each fix attempt
- Tag pattern: `bug-123-present`, `bug-123-fix-attempt-1`, `bug-123-fixed`

**For Experiments**:
- Checkpoint at: before each experiment, after each significant change
- Tag pattern: `experiment-baseline`, `exp-approach-a`, `exp-approach-b`

### Performance Practices

1. **Use .gitignore Patterns**
   - Ensure `.snapshots/` is in `.gitignore`
   - snapback automatically respects your `.gitignore` in local mode

2. **Exclude Build Artifacts** (if desired)
   - Add to `.gitignore`: `build/`, `dist/`, `node_modules/`
   - snapback will exclude these automatically

3. **Monitor Disk Usage**
   ```bash
   du -sh .snapshots/
   ```

4. **Clean Up Old Snapshots**
   ```bash
   # List all tagged snapshots
   snapback list --tags

   # Manually remove old tags (they're just directories)
   rm -rf .snapshots/old-tag-name
   ```

### Safety Practices

1. **Never Commit .snapshots/ to Git**
   - Verify it's in `.gitignore`
   - Check before pushing: `git status`

2. **Backup .snapshotrc Separately**
   - Not necessary if you use default settings
   - If customized, commit to git (it's small)

3. **Test Rollbacks Before Relying on Them**
   ```bash
   # Practice rollback
   snapback hourly
   echo "test" > test-file.txt
   snapback hourly
   snapback recover hour-1
   # test-file.txt should be gone
   ```

4. **Use Both snapback and Git**
   - snapback for experiments (temporary)
   - git for finalized changes (permanent)

## Troubleshooting

### Snapback Not Respecting .gitignore

**Problem**: Files that should be ignored are being backed up.

**Solution**:
```bash
# Verify you're in local mode
cat .snapshotrc
# Should have: DIRS='.' and TARGETBASE='./.snapshots'

# Verify .gitignore exists and contains patterns
cat .gitignore

# Test with dry-run
snapback --dry-run hourly
```

### Snapshots Taking Too Much Space

**Problem**: `.snapshots/` directory is very large.

**Solutions**:
```bash
# Check what's taking space
du -sh .snapshots/*

# List tagged snapshots (won't be auto-deleted)
snapback list --tags

# Remove old tags manually
rm -rf .snapshots/old-tag-name

# Exclude more files in .gitignore
echo "*.log" >> .gitignore
echo "tmp/" >> .gitignore
```

### Can't Recover to Previous State

**Problem**: `snapback recover` doesn't work as expected.

**Solutions**:
```bash
# List available snapshots
snapback list

# Verify snapshot exists
ls -la .snapshots/hour-1/

# Check if you have the right tag
snapback list --tags

# Try recovering with tag name instead
snapback recover my-tag-name

# If desperate, manually copy files
cp -r .snapshots/hour-1/* .
```

### Git and snapback Conflicts

**Problem**: Git sees .snapshots/ or .snapshotrc as untracked files.

**Solutions**:
```bash
# Ensure they're in .gitignore
cat .gitignore | grep snapshots
cat .gitignore | grep snapshotrc

# If missing, add them
echo ".snapshots/" >> .gitignore
echo ".snapshotrc" >> .gitignore

# Tell git to ignore
git add .gitignore
git commit -m "Ignore snapback files"
```

### Multiple Developers Using Same Project

**Problem**: Each developer has their own `.snapshotrc`.

**Solutions**:
```bash
# Option 1: Each dev has local .snapshotrc (in .gitignore)
# This is the default - each dev manages their own snapshots

# Option 2: Commit .snapshotrc but not .snapshots/
# Remove .snapshotrc from .gitignore
# Keep .snapshots/ in .gitignore
git add .snapshotrc
git commit -m "Share snapback config"

# Option 3: Use global config instead
# Each dev uses ~/.snapshotrc
# Don't use project-local mode
```

## Examples

### Example 1: AI Pair Programming Session

Complete session with Claude Code or GitHub Copilot:

```bash
cd ~/projects/web-app

# Start session
snapback init
snapback hourly
snapback tag hour-0 "session-start-$(date +%Y-%m-%d)"

# AI implements login feature
# ... AI generates code ...
snapback hourly
snapback tag hour-0 "login-feature-v1"
npm test
# Tests fail ❌

# AI fixes tests
# ... AI modifies code ...
snapback hourly
snapback tag hour-0 "login-feature-v2"
npm test
# Tests pass ✅

# AI adds validation
# ... AI adds validation logic ...
snapback hourly
snapback tag hour-0 "login-with-validation"
npm test
# Tests pass ✅

# Commit final version
git add src/auth/
git commit -m "Implement login with validation"

# Clean up snapshots
snapback list --tags
# Keep: login-with-validation
# Delete others: they're in hourly snapshots anyway
```

### Example 2: Debugging with AI Assistant

Systematic debugging with AI help:

```bash
# Bug exists in production
snapback hourly
snapback tag hour-0 "bug-reproduction"

# AI suggests cause #1
# ... AI generates diagnostic code ...
snapback hourly
snapback tag hour-0 "debug-attempt-1"
npm test
# Still buggy ❌

# AI suggests cause #2
snapback recover bug-reproduction
# ... AI generates different fix ...
snapback hourly
snapback tag hour-0 "debug-attempt-2"
npm test
# Fixed! ✅

# Verify fix thoroughly
npm run integration-tests
npm run e2e-tests
# All pass ✅

# Commit fix
git add .
git commit -m "Fix production bug in payment processing"

# Document approach in ticket
echo "Used AI-assisted debugging, attempt #2 successful" >> docs/bugs/BUG-123.md
```

### Example 3: Refactoring Large Codebase

Safe refactoring with AI:

```bash
# Snapshot before refactoring
snapback hourly
snapback tag hour-0 "pre-refactor"

# Phase 1: Rename variables
# ... AI refactors variable names ...
snapback hourly
snapback tag hour-0 "refactor-phase-1-names"
npm test
# Pass ✅

# Phase 2: Extract functions
# ... AI extracts helper functions ...
snapback hourly
snapback tag hour-0 "refactor-phase-2-functions"
npm test
# Pass ✅

# Phase 3: Reorganize files
# ... AI moves code between files ...
snapback hourly
snapback tag hour-0 "refactor-phase-3-structure"
npm test
# Fail ❌ - import paths broken

# Revert phase 3, fix manually
snapback recover refactor-phase-2-functions
# ... manually fix imports ...
npm test
# Pass ✅

# Commit working refactoring
git add .
git commit -m "Refactor module structure (phases 1-2)"
```

---

## Summary

Project-local snapshots with snapback provide a **safety net** for AI-assisted development:

- **Fast checkpoints** before AI makes changes
- **Quick rollbacks** when experiments fail
- **No git pollution** - snapshots are separate from version control
- **Automatic .gitignore integration** - respects your existing patterns

**Remember**:
1. Always checkpoint before AI changes: `snapback hourly`
2. Tag important states: `snapback tag hour-0 "description"`
3. Test immediately after AI changes
4. Commit good changes to git, rollback bad ones with snapback
5. Use both tools: snapback for experiments, git for finalized work

---

**For more information**:
- Main README: [README.md](../README.md)
- Container testing: [DOCKER_TESTING.md](../DOCKER_TESTING.md)
- Project repository: https://github.com/meirm/snapback
