---
name: writing-guard
description: Use BEFORE drafting any prose for the user — emails, log entries, documents, summaries, messages, status updates, reports. Loads the writing rules and self-censors AI tells, em dashes, hedging, puffery, and promotional tone in real time as you draft. Proactive complement to voice-check.
---

# Writing Guard (proactive)

You are about to write prose for the user. Internalize the rules first and self-edit as you draft, not after.

## Why this skill exists

The `voice-check` skill cleans up AI writing tells AFTER they appear in a file. `writing-guard` prevents them from appearing in the first place. Both skills use the same rule list. The difference is timing: guard fires before/during writing, voice-check fires after.

## Process

1. Read `../../references/rules.md` in full before writing anything (the file lives at the plugin root, not inside the skill dir)
2. As you draft, self-check each sentence against the rules. If a sentence triggers any rule, rewrite it before continuing. Do not finish the draft and clean up later.
3. After completing the draft, do one final pass against the rules.
4. If you cannot express something without violating a rule, prefer the rule over the original phrasing.
5. If the user is in a context with a per-repo supplement at `.claude/voice-check.md` (walking up to git root), apply those rules too.

## When NOT to use this skill

- When transcribing the user's exact words (the rules are about generated prose, not user quotes)
- When writing code, code comments, or commit messages where dashes and technical jargon are appropriate
- When explicitly asked to mimic a specific style that conflicts with the rules

## References

- `../../references/rules.md` — the rule list (shared with voice-check, lives at the plugin root)
