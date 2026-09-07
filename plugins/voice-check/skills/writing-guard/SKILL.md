---
name: writing-guard
description: Loads the writing rules before drafting prose and self-censors AI tells, em dashes, hedging, puffery, and promotional tone in real time while drafting. Use before writing any prose for the user, including emails, log entries, documents, summaries, messages, status updates, and reports. Proactive complement to voice-check.
---

# Writing Guard (proactive)

Internalize the rules first and self-edit while drafting, not after.

## Why this skill exists

The `voice-check` skill cleans up AI writing tells AFTER they appear in a file. `writing-guard` prevents them from appearing in the first place. Both skills use the same rule list. The difference is timing: guard fires before and during writing, voice-check fires after.

## Process

1. Read `../../references/rules.md` in full before writing anything (the file lives at the plugin root, two levels up from this skill directory, NOT inside the skill dir).
2. If the target context has a per-repo supplement at `.claude/voice-check.md` (walking up to the git root, first match wins), load those rules too.
3. As you draft, self-check each sentence against the rules. If a sentence triggers any rule, rewrite it before continuing. Do not finish the draft and clean up later.
4. After completing the draft, do one final pass against the rules.
5. If the draft was written to a file and `python3` is available, verify it: run `python3 ../../engine/voice_check.py --report-only --min-severity low <file>` (execute the script, do not read it), fix any findings, and re-run until it reports zero. `--min-severity low` is required. Without it the engine collapses lower severity findings into a summary line, and this step could not tell a clean file from a quiet one. The path is relative to this skill directory; resolve it against the installed plugin location.
6. If you cannot express something without violating a rule, prefer the rule over the original phrasing.

## When NOT to use this skill

- When transcribing the user's exact words (the rules are about generated prose, not user quotes)
- When writing code, code comments, or commit messages where dashes and technical jargon are appropriate
- When explicitly asked to mimic a specific style that conflicts with the rules

## References

- `../../references/rules.md`: the rule list (shared with voice-check, lives at the plugin root). Read it in step 1.
