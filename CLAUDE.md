# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code marketplace plugin (`voice-check`) that ships two writing-rule skills plus a deterministic Python engine for a git pre-commit hook. The repo is both the source of truth for the rules and the installable marketplace entry.

## Architecture

The plugin has three layers that must stay in sync:

1. **Rule source of truth**: `plugins/voice-check/references/rules.md`. Both skills read this at runtime. Editing it updates skill behavior immediately (no code change needed).
2. **Skills** (`plugins/voice-check/skills/`): thin Markdown shells that reference `../../references/rules.md` (two levels up, at the plugin root, NOT inside the skill dir). Two skills with deliberate timing split:
   - `writing-guard/SKILL.md`: proactive, loads *before* Claude drafts prose, self-censors during writing.
   - `voice-check/SKILL.md`: reactive, scans/fixes existing files; also used in report-only mode by the pre-commit hook.
3. **Python engine** (`plugins/voice-check/engine/`): deterministic subset of the rules for hook-speed scanning. `voice_check.py` is the CLI entry (`--report-only` for hook mode, always exits 0, advisory). `rules.py` holds regex/word lists. `supplement.py` walks up from a target file to the git root to find `.claude/voice-check.md` (per-repo supplement, first match wins, no aggregation).

Important: the engine duplicates a subset of the markdown rules as code. When adding a rule, decide whether it needs to run in the hook (add to both `rules.py` and `references/rules.md`) or only at skill-invocation time (markdown only). The markdown file is authoritative for the skill path; `rules.py` is authoritative for the hook path.

### Hook installation flow

`templates/pre-commit.sh` contains a `__VOICE_CHECK_ENGINE__` placeholder. `templates/install-hook.sh` substitutes the absolute path to `engine/voice_check.py` inside the installed plugin cache and writes a marked section (`# === voice-check section start/end ===`) into the target repo's `.git/hooks/pre-commit`. The installer is idempotent and appends rather than overwriting. After upgrading the plugin, users must re-run `install-hook.sh` in each repo because the cached engine path changes.

### Marketplace structure

`.claude-plugin/marketplace.json` at the repo root is the marketplace catalog; `plugins/voice-check/.claude-plugin/plugin.json` is the plugin manifest. The marketplace points at `./plugins/voice-check` as the plugin source.

## Commands

Run the engine tests (46 pytest cases in `plugins/voice-check/tests/test_engine.py`):

```bash
cd plugins/voice-check
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/test_engine.py -v
```

Runtime engine is stdlib-only; pytest is only needed for the test suite. Requires Python 3.11+.

Run the engine directly against a file:

```bash
python3 plugins/voice-check/engine/voice_check.py --report-only path/to/file.md
```

CI runs the same pytest suite via `.github/workflows/test.yml`.

## Conventions specific to this repo

- **No dashes in any written output, anywhere.** This repo's entire purpose is enforcing that rule. Commit messages, docs, comments, and Markdown prose must use commas, colons, periods, or parentheses instead of em/en dashes or spaced hyphens. Compound-word hyphens (no surrounding spaces) are allowed.
- Skill files reference rules via `../../references/rules.md`. If you move skill files, update these relative paths; the skills explicitly document that references live at the plugin root, not inside the skill dir.
- The pre-commit hook is **advisory only** by design. It prints findings to stderr and exits 0. Do not change this without a deliberate decision; users rely on commits never being blocked.
