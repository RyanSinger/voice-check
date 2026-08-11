---
name: voice-check
description: Scans a document for AI writing tells, including em dashes, hedging, puffery, AI vocabulary clusters, promotional tone, bridge phrases, and leaked markup artifacts. Use when reviewing or editing prose, before committing any document, when invoked via /voice-check, or when the user mentions AI-sounding writing, voice, or tone. Layers global rules with per-repo supplements found at .claude/voice-check.md walking up from the target file.
---

# Voice Check (reactive scan)

Scans a file for AI writing patterns and tone violations, fixes every issue found, then reports what changed. The deterministic rules are verified by the bundled Python engine; context-sensitive rules get a manual pass.

## Process

Copy this checklist and check off items as you complete them:

```
Voice Check Progress:
- [ ] Step 1: Read the rules, locate the target file and any supplement
- [ ] Step 2: Run the engine (report-only)
- [ ] Step 3: Fix every engine finding
- [ ] Step 4: Re-run the engine until it reports zero findings
- [ ] Step 5: Manual pass for skill-only rules
- [ ] Step 6: Report changes by category
```

**Step 1: Read the rules, locate the target and supplement.**
Read `../../references/rules.md` (the file lives at the plugin root, two levels up from this skill directory, NOT inside the skill dir). Determine the target file path. Walk up from the target file to the git root, looking for `.claude/voice-check.md` at each level. Stop at the first one found; do not aggregate across levels. Load the supplement if found.

**Step 2: Run the engine.**
Run this script (execute it, do not read it as reference):

```bash
python3 ../../engine/voice_check.py --report-only <target-file>
```

The path is relative to this skill directory; resolve it against the installed plugin location. The engine covers every rule tagged `[engine + skill]` plus supplement rules, and always exits 0. If `python3` is unavailable, skip to Step 5 and cover the engine-tagged rules manually as well.

**Step 3: Fix every engine finding.**
Rewrite the target file to resolve each finding. Preserve meaning; change only the flagged constructions and their immediate context.

**Step 4: Re-run the engine.**
Repeat Steps 2 and 3 until the engine reports zero findings. Do not proceed to Step 5 with open engine findings.

**Step 5: Manual pass for skill-only rules.**
The engine cannot see these; scan for them yourself using `../../references/rules.md`:

- Structural tells: rule of three, negative parallelisms and contrast reframes, false ranges, challenges-and-future-prospects, balanced-debate framing, uniform sentence rhythm, mechanical bold headers, elegant variation
- 2026 bare-word cluster in context (quietly, shift, matters, signal, compound, and the rest; two or more in a document is a pattern)
- Nuanced copula avoidance ("represents," "marks")

**Step 6: Report a summary of changes by category.**

## Modes

- **Auto-fix (default for /voice-check):** the full process above; rewrite the file in place.
- **Report-only (pre-commit hook path):** print findings, do not modify the file. The hook calls the engine directly; if this skill is invoked in a report-only context, run Steps 1, 2, and 5 and print findings without editing.

## References

All reference files live at the plugin root, two levels up from this skill directory:

- `../../references/rules.md`: the rule list (single source of truth). Read it in Step 1.
- `../../references/examples.md`: before/after examples per rule category. Read when unsure how to rewrite a finding.
- `../../references/wikipedia-signs.md`: condensed Wikipedia signs of AI writing. Read only for deep dives on unfamiliar patterns.
