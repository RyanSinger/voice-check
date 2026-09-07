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
3. **Python engine** (`plugins/voice-check/engine/`): six modules with an
   acyclic dependency graph. `voice_check.py` is the CLI entry
   (`--report-only` for hook mode, `--min-severity` for verbosity, `--lines`
   for diff scoping, always exits 0, advisory). `document.py` decides what
   text is prose, producing length preserving masked lines plus suppression
   directives parsed from the raw text. `config.py` finds `.claude/voice-check.md`
   by walking up to the git root (first match wins, no aggregation) and parses
   six fenced block kinds. `rules.py` holds the rule table, where every row has
   a stable id and a severity. `analyzers.py` holds rules that compute over a
   document rather than matching against it, for properties like the fraction
   of bullets opening with a bold run that no rule row can express. Its
   registry entries share the rule row contract, so per repo disable,
   severity, and suppression apply to analyzers unchanged. `scanner.py` runs
   rows against a document and applies suppression, severity, and line
   ranges, then runs the analyzer pass: it validates each analyzer's returned
   evidence lines and isolates a raising or malformed analyzer so one bad
   analyzer cannot cost the rule passes or the other analyzers.

Rule ids can shift between releases. A supplement that disables or reassigns severity for a stale id (for example, the removed `ai_vocab_cluster.key` or the renamed `ai_vocab_cluster.align`, now `ai_vocab_cluster.align_with`) prints a warning and otherwise has no effect; see `references/rules.md` for current ids.

Important: the engine duplicates a subset of the markdown rules as code. When adding a rule, decide whether it needs to run in the hook (add to both `rules.py` and `references/rules.md`) or only at skill-invocation time (markdown only). The markdown file is authoritative for the skill path; `rules.py` is authoritative for the hook path.

### Hook installation flow

`templates/pre-commit.sh` contains a `__VOICE_CHECK_ENGINE__` placeholder. `templates/install-hook.sh` substitutes the absolute path to `engine/voice_check.py` inside the installed plugin cache and writes a marked section (`# === voice-check section start/end ===`) into the target repo's `.git/hooks/pre-commit`. The installer is idempotent and appends rather than overwriting. Installed hooks self-heal across upgrades: the hook re-resolves the engine from the newest plugin cache version at commit time, and the plugin's SessionStart hook (`hooks/heal-hook.sh`, registered in `hooks/hooks.json`) rewrites stale pre-2.2.1 hook sections the first time a Claude Code session starts in that repo. Re-running `install-hook.sh` stays harmless but is no longer needed.

### Marketplace structure

`.claude-plugin/marketplace.json` at the repo root is the marketplace catalog; `plugins/voice-check/.claude-plugin/plugin.json` is the plugin manifest. The marketplace points at `./plugins/voice-check` as the plugin source.

## Commands

Run the engine tests (207 pytest cases across `plugins/voice-check/tests/`):

```bash
cd plugins/voice-check
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -v
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
