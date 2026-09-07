# Voice Check Rules

This is the single source of truth for the writing rules used by both the `voice-check` (reactive scan) and `writing-guard` (proactive guard) skills. When changing rules, edit this file and both skills get the update automatically.

Each rule is marked with a tag:

- `[engine + skill]`: enforced by the Python rules engine at pre-commit hook speed AND by the Claude-loaded skills.
- `[skill only]`: only enforced by the Claude-loaded skills. The Python engine does not attempt this because it depends on context the regex engine cannot reliably see.

## Hard Rules (fix all violations, no exceptions)

### No dashes `[engine + skill]`
Em dashes and en dashes are banned. Hyphens used as separators or punctuation are also banned. Replace with commas, periods, colons, or parentheses. Hyphens inside compound words ("voice-check," "first-person") are fine.

### No hedging `[engine + skill]`
Cut "I can take on," "I could potentially help with," "I'm pushing for this direction," "would like to." Replace with ownership: "I own X," "Ready to do Y," "This is the plan."

### No copula avoidance `[engine + skill]`
Don't replace "is" with "serves as," "stands as," "acts as," "functions as," "represents," "marks." Just say "is." The engine catches the "as" variants ("serves as", "stands as", "acts as", "functions as") with a word-boundary regex. Nuanced replacements like "represents" are left to the skill.

<!-- voice-check: disable ai_vocab_cluster, puffery, promotional_tone, vocab_2026, bridge_phrases, hedging, vague_attribution, dangling_participle, structure, markup_artifacts -->

## AI Vocabulary Cluster (flag when 2+ appear in the same document) `[engine + skill]`

Additionally (starting sentences), align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as verb), interplay, intricate/intricacies, key (as adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (as verb), valuable, vibrant.

One might be fine. Two or more in the same document is a pattern. Replace with plain language.

`key (as adjective)` is skill only. Telling the adjective "a key decision" apart from the plain noun "an API key" needs part of speech judgment that a regex cannot make, so the engine omits `key` from its cluster list entirely and leaves it to the skill.

Five other members carry qualifiers the engine also cannot enforce: `highlight (as verb)`, `showcase (as verb)`, `underscore (as verb)`, `landscape (abstract noun)`, and `tapestry (abstract noun)`. Unlike `key`, the engine still matches these as bare words, because dropping them would lose more than it saves. The qualifiers describe the sense to flag, and the skill applies them; the engine approximates.

That approximation is deliberate and measured. Scanning 206 markdown files, 19 fired the cluster and only 4 fired solely because of these five words, so tightening them would change roughly two percent of verdicts while adding five hand written patterns whose qualifiers a regex cannot express anyway. "Highlight your advantages" is a verb and not the tell; "competitive landscape" is the abstract noun and arguably is. Two safeguards make the looseness tolerable: a single occurrence never fires, since the cluster needs two, and the whole rule is low severity, so it collapses to a counted line unless the reader asks for detail.

## Puffery and Significance Language `[engine + skill]`

Flag and rewrite: "pivotal," "crucial," "testament," "underscores," "highlights its importance," "represents a shift," "setting the stage for," "indelible mark," "deeply rooted," "groundbreaking," "renowned."

Show importance through specifics, not inflating adjectives.

## Superficial Analysis via Dangling Participles `[engine + skill]`

Flag and rewrite: "...highlighting the importance of," "...ensuring that," "...reflecting broader trends," "...contributing to," "...fostering," "...encompassing," "...emphasizing," "...underscoring," "...showcasing."

These are filler. Cut them or say something concrete. The engine catches comma + gerund constructions using a conservative regex anchored on a seed list of gerunds.

## Promotional Tone `[engine + skill]`

Flag and rewrite: "boasts," "vibrant," "rich" (figurative), "nestled," "in the heart of," "groundbreaking," "showcasing," "commitment to," "natural beauty."

Write neutral, not like ad copy.

## Structural Tells

- **Rule of three** `[skill only]`: Don't default to "X, Y, and Z" triads. Break the pattern.
- **Negative parallelisms and contrast reframes** `[engine + skill]`: "Not just X, but Y" and "It's not about X, it's about Y." The reframe manufactures insight by setting up a false opposition and resolving it in one move. Also flag overuse of "X rather than Y." Rewrite as a direct claim.
- **False ranges** `[engine + skill]`: "From X to Y" where no real spectrum exists. Cut.

  The engine matches lowercase plural to lowercase plural, which is what
  separates a false enumeration ("from startups to enterprises") from an
  ordinary range ("from 9 to 5"). Gerund pairs such as "from onboarding to
  offboarding" are missed on purpose: catching them would also fire on "from
  testing to shipping", which describes a real sequence.

- **Challenges-and-future-prospects** `[engine + skill]`: "Despite its [good thing], [subject] faces challenges..." followed by vague optimism. Never.
- **Bolded inline headers on every bullet** `[engine, opt in]`: Use sparingly, not mechanically. The engine ships this one OFF. Measured across 206 markdown files it fired on 6.8 percent of them with no identifiable true positive: every hit was a definition list. The examples this rule was drawn from are definition lists too, so no syntactic test separates the tell from the legitimate pattern, and what distinguishes them is whether the surrounding prose was machine written, which the engine cannot see. Turn it on for a repo whose prose is article shaped with a `voice-check-enable` block naming `structure.bold_headers`.
- **Elegant variation** `[skill only]`: Don't swap synonyms to avoid repeating a word. Say "Nick" three times rather than "the engineer," "the technical lead," "the key contributor."
- **Balanced-debate framing** `[engine + skill]`: presenting every topic as a two-sided debate is a tell. Take a position or report the facts.

  Bare word co-occurrence fires on an ordinary pros and cons discussion,
  which is not the tell, so the engine requires a balancing connective
  ("but," "yet," "though," "however," "also") sitting between an advantage
  term and a disadvantage term before it flags the sentence.

- **Uniform sentence rhythm** `[skill only]`: every sentence landing in the
  same length range. Vary it. Some thoughts need three words. Some need a
  full paragraph. The engine does not attempt this. Measuring the coefficient
  of variation of sentence lengths across this repository put a deliberately
  AI sounding sample at 0.48, between two hand written files at 0.40 and
  0.41, so no threshold separates them. Technical reference prose is
  legitimately uniform, and this advice is about narrative writing.

Rule of three and elegant variation stay skill only because telling a
deliberate pattern from an incidental one needs judgment a regex cannot
reach. The other five bullets above are now attempted by the Python engine
too, marked `[engine + skill]`.

Matching a sentence shape instead of a word list carries a cost: some
ordinary prose has the same shape as the tell. Three of the five engine rows
have a confirmed false positive shape. `not_just_but` fires on ordinary
enumeration such as "This library supports not only Python but also Java."
`false_range` fires on a genuine range built from plural nouns, such as "events from decades to centuries," and it also fires on ordinary migration prose in the same shape, such as "from callbacks to promises." That is the same plural noun to plural noun shape a genuine sequence uses, so an ordinary changelog line describing a migration reads as a false range too.
`while_also` fires on an ordinary concessive sentence such as "While Sarah wrote the tests, they also fixed the linter." All five rows default to low
severity, so a hit collapses into one counted summary line instead of
surfacing on its own; a repo whose prose keeps tripping one of these can
disable it, reassign its severity, or suppress the line in a supplement.

## Vague Attributions `[engine + skill]`

"Experts say," "experts agree," "industry reports suggest," "industry observers note," "observers note," "sources say," "critics argue," "many believe," "it is widely believed." Name the source or cut the claim.

## Faux-conversational Bridges `[engine + skill]`

Flag and cut: "here's the thing," "but here's the truth," "at the end of the day," "don't get me wrong," "let's dive in," "let's delve into," "let's examine," "we will explore," "in this section we will."

These bridges simulate spoken candor or announce structure instead of delivering content. State the point directly.

## 2026 Vocabulary Cluster

The vocabulary generation turned over in 2025/2026. Current model output leaks abstract fillers and unearned intensifiers with a LinkedIn flavor.

Bare words `[skill only]` (flag when 2+ appear in the same document, same clustering logic as the AI Vocabulary Cluster above): quietly, shift (as default word for any change), matters, shape (as vague influence verb), land (for message reception), actually, real (as intensifier), earn (attached to abstractions), hold (metaphorical), pull (unnamed forces), compound (as growth default), signal (abstract substitute), the work (vague reverence).

These are common English words; judge them in context. "She spoke quietly" is fine. "Quietly building an empire" is the tell.

Phrase forms `[engine + skill]`: "quietly [verb]ing," "this matters because," "the pull of," "built different," "do the work," "send a signal," "decisions compound."

## Markup Artifacts `[engine + skill]`

Leaked model citation tokens are proof of unedited AI output. Flag and delete: `contentReference`, `oaicite`, `oai_citation`, `turn0search` and `turn0image` and `turn0news` and `turn0file` style tokens, `[cite:` fragments, `[span_0]` fragments, `[web:1]` fragments, `grok_card` and its hyphenated `grok-card` form, `grok_render`, `ppl-ai-file-upload`, `attached_file`, DeepSeek lenticular bracket citations, and the `:::writing` document marker.

Emoji used as bullet markers (an emoji starting a line as if it were a list marker) is also flagged. Use standard list markers. Artifacts quoted inside fenced code blocks are not flagged.

Two token families cannot be rule rows, because they live where the masking layer correctly refuses to look. A chatbot tracking parameter sits inside a URL, and URLs are masked whole; a JSON attribution key sits inside double quotes, and short quoted spans are masked as mentions. Both are handled by an analyzer instead, which reads raw lines: `utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=copilot.com`, `referrer=grok.com`, and `attributableIndex`.

Because that analyzer bypasses masking by design, naming those tokens anywhere makes the document containing them fire, backticks included. That is why this section sits inside a suppression range rather than relying on inline code the way the rule row tokens above do.

<!-- voice-check: enable -->

## Per-repo supplements

In addition to the rules above, the engine loads extra rows from a per-repo `.claude/voice-check.md` supplement file. Authors add banned words, phrases, or regex patterns by embedding fenced code blocks with one of these info strings:

```
voice-check-words      one word per line, matched with word boundaries
voice-check-phrases    one literal phrase per line, matched case-insensitive
voice-check-regex      one raw regex per line, matched case-insensitive
voice-check-disable    rule name or id, optionally "<rule> in <path glob>"
voice-check-enable     same shape, switches on a rule that ships off
voice-check-severity   "<rule name or id> = high|medium|low"
voice-check-exclude    one path glob per line, skipped entirely
```

Each non-blank, non-comment line inside a `voice-check-words`, `voice-check-phrases`, or `voice-check-regex` block becomes a supplement rule row appended to the scanner table at scan time. Findings from supplement rules carry the rule name `supplement:<kind>` so they are attributable.

`voice-check-disable`, `voice-check-severity`, and `voice-check-exclude` change how existing rows are treated instead of adding new ones. A disable entry can name a rule by its plain name (every row under that name) or by a single stable id, and can optionally scope itself to one path glob with `in`. A severity entry reassigns a rule's default severity the same way. An exclude entry is a path glob, matched with `fnmatch` semantics where `*` also matches a path separator, so `docs/vendor/**` covers `docs/vendor/a/b.md`. A bad line is skipped and recorded as a warning; the rest of the supplement still loads.

Rule ids can change between releases. If a supplement disables or reassigns severity for an id that no longer exists (for example, `ai_vocab_cluster.key` was removed and `ai_vocab_cluster.align` became `ai_vocab_cluster.align_with`), the engine warns that the identifier is unknown and the entry has no effect, rather than failing. Check `rules.py` for current ids after an upgrade if a supplement directive stops doing anything.

## Suppression directives

Any file can suppress rules inline with an HTML comment, which stays
invisible in rendered markdown:

```
<!-- voice-check: ignore -->                 suppress this line
<!-- voice-check: ignore puffery -->         suppress one rule on this line
<!-- voice-check: disable -->                suppress from here on
<!-- voice-check: enable -->                 resume after a disable
```

Arguments accept a rule name, which covers every row under that name, or a
single rule id such as `puffery.crucial`. A comma separated list works too.
A `disable` with no matching `enable` runs to the end of the file.

Only one `disable` can be open at a time. A second `disable` opened while
the first is still open is ignored entirely, rule arguments included; the
scope and rule list that apply until the next `enable` are the first
`disable`'s. Close the open one before opening another.

Directives inside fenced code blocks have no effect, so the examples above
are inert.
