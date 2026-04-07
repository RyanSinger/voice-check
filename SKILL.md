---
name: voice-check
description: Scan a document for AI writing tells, em dashes, hedging, puffery, and tone violations. Use when reviewing or editing prose, when invoked via /voice-check, or before committing any document. Layers global rules with per-repo supplements found at .claude/voice-check.md walking up from the target file.
---

# Voice Check

Scan the specified document (or the most recently written/edited file) for AI writing patterns and tone violations. Fix every issue found, then report what you changed.

## Process

1. Determine the target file path
2. Walk up from the target file to the git root, looking for `.claude/voice-check.md` at each level. Stop at the first one found. Do not aggregate.
3. Load the supplement if found
4. Read the target file
5. Scan for every category below, plus any rules from the supplement
6. **Auto-fix mode (default for /voice-check):** rewrite file in place
7. **Report-only mode (when called from pre-commit hook):** print findings, do not modify the file
8. Report a summary of changes by category

## Hard Rules (fix all violations, no exceptions)

### No dashes
Em dashes and en dashes are banned. Hyphens used as separators or punctuation are also banned. Replace with commas, periods, colons, or parentheses. Hyphens inside compound words ("voice-check," "first-person") are fine.

### No hedging
Cut "I can take on," "I could potentially help with," "I'm pushing for this direction," "would like to." Replace with ownership: "I own X," "Ready to do Y," "This is the plan."

### No copula avoidance
Don't replace "is" with "serves as," "stands as," "represents," "marks." Just say "is."

## AI Vocabulary Cluster (flag when 2+ appear in the same document)

Additionally (starting sentences), align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as verb), interplay, intricate/intricacies, key (as adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (as verb), valuable, vibrant.

One might be fine. Two or more in the same document is a pattern. Replace with plain language.

## Puffery and Significance Language

Flag and rewrite: "pivotal," "crucial," "testament," "underscores," "highlights its importance," "represents a shift," "setting the stage for," "indelible mark," "deeply rooted," "groundbreaking," "renowned."

Show importance through specifics, not inflating adjectives.

## Superficial Analysis via Dangling Participles

Flag and rewrite: "...highlighting the importance of," "...ensuring that," "...reflecting broader trends," "...contributing to," "...fostering," "...encompassing."

These are filler. Cut them or say something concrete.

## Promotional Tone

Flag and rewrite: "boasts," "vibrant," "rich" (figurative), "nestled," "in the heart of," "groundbreaking," "showcasing," "commitment to," "natural beauty."

Write neutral, not like ad copy.

## Structural Tells

- **Rule of three**: Don't default to "X, Y, and Z" triads. Break the pattern.
- **Negative parallelisms**: "Not just X, but Y" and "It's not about X, it's about Y." Overused. Rewrite.
- **False ranges**: "From X to Y" where no real spectrum exists. Cut.
- **Challenges-and-future-prospects**: "Despite its [good thing], [subject] faces challenges..." followed by vague optimism. Never.
- **Bolded inline headers on every bullet**: Use sparingly, not mechanically.
- **Elegant variation**: Don't swap synonyms to avoid repeating a word. Say "Nick" three times rather than "the engineer," "the technical lead," "the key contributor."

## Vague Attributions

"Experts say," "industry reports suggest," "observers note." Name the source or cut the claim.

## Output

After fixing, report:
- Number of violations found and fixed, by category
- Any judgment calls where you left something as-is and why

## References

- `references/wikipedia-signs.md` — full Wikipedia article on signs of AI writing
- `references/examples.md` — before/after examples for each rule category
