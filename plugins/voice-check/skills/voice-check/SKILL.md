---
name: voice-check
description: Scan a document for AI writing tells, em dashes, hedging, puffery, and tone violations. Use when reviewing or editing prose, when invoked via /voice-check, or before committing any document. Layers global rules with per-repo supplements found at .claude/voice-check.md walking up from the target file.
---

# Voice Check (reactive scan)

Scan a file for AI writing patterns and tone violations. Fix every issue found, then report what you changed.

## Process

1. Read `../../references/rules.md` for the full rule list (the file lives at the plugin root, not inside the skill dir)
2. Determine the target file path
3. Walk up from the target file to the git root, looking for `.claude/voice-check.md` at each level. Stop at the first one found. Do not aggregate across levels.
4. Load the supplement if found
5. Read the target file
6. Scan against the rules + supplement
7. **Auto-fix mode (default for /voice-check):** rewrite the file in place
8. **Report-only mode (when called from the pre-commit hook):** print findings, do not modify the file
9. Report a summary of changes by category

## References

All reference files live at the plugin root, two levels up from this skill directory:

- `../../references/rules.md` — the rule list (single source of truth)
- `../../references/wikipedia-signs.md` — full Wikipedia article on signs of AI writing
- `../../references/examples.md` — before/after examples for each rule category
