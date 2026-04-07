# Voice Check Rules

This is the single source of truth for the writing rules used by both the `voice-check` (reactive scan) and `writing-guard` (proactive guard) skills. When changing rules, edit this file and both skills get the update automatically.

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
