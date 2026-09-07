# Structural Detection (Phase 2)

Date: 2026-09-07
Status: approved, ready for implementation planning

## Context

Phase 1 made the pre-commit hook quiet enough to trust. It masked mentions, added suppression, scoped reporting to changed lines, and gave every rule an id and a severity. It did nothing for recall.

Running the shipped 2.3.0 engine over this paragraph reports zero findings:

> Our platform is not just a tool, it is a partner in your workflow. The results speak for themselves. Teams move faster. Reviews get shorter. While there are tradeoffs to this approach, the benefits outweigh them for most teams. In short: we shipped speed, clarity, and confidence.

That text carries negative parallelism, balanced-debate framing, a rule of three, and flat rhythm. Every structural rule in `references/rules.md` is tagged `[skill only]`, and the hook runs the engine alone, so the always-on surface catches vocabulary and misses structure. Structure is the part that most makes prose read as machine written.

## Scope

In scope:

- Five syntactic frames as line-scope rule rows
- One computed analyzer for mechanical bold headers
- A new `analyzers.py` module and the analyzer contract in `scanner.py`

Out of scope, with reasons:

- **Uniform sentence rhythm.** Measured and rejected. See "Rhythm, measured and dropped" below.
- **Rule of three.** Separating a rhetorical triad from "eggs, milk, and bread" needs semantics.
- **Elegant variation.** Requires knowing that "the engineer" and "Nick" refer to the same person.
- Sentence segmentation of any kind, which only rhythm needed.
- Surfaces beyond markdown, which is Phase 3.
- Any change to the advisory contract.

## Constraints

- The engine stays Python standard library only.
- The pre-commit hook stays advisory and always exits 0.
- The `# === voice-check section start/end ===` hook contract is preserved.
- No dashes in any prose output, including commit messages and documentation.
- Python 3.11 or later.
- Structural rules default to `low` severity and are enabled by default. Phase 1's collapse behavior means they summarize to one counted line unless the reader asks for detail with `--min-severity low`.

## Rhythm, measured and dropped

Uniform sentence rhythm looked like the most promising analyzer, because variance is arithmetic rather than judgment. Calibration killed it, and the result is recorded here so nobody re-derives it.

Coefficient of variation over sentence word counts, excluding headings, tables, fenced code, and bullets. Measured across every markdown file in this repository that carries at least six sentences, which was sixteen of them at the time of writing:

| Document | CV |
| --- | --- |
| `skills/voice-check/SKILL.md` | 0.40 |
| `references/wikipedia-signs.md` | 0.41 |
| **A deliberately AI sounding sample** | **0.48** |
| `specs/2026-08-11-hook-self-healing-design.md` | 0.48 |
| `specs/2026-09-07-signal-quality-design.md` | 0.53 |
| `README.md` | 0.64 |
| `references/rules.md` | 0.83 |

The AI sample lands mid range, with two hand written files scoring lower. No threshold separates them. Technical reference prose is legitimately uniform, because "vary your rhythm" is advice about narrative writing and this corpus is entirely specs, plans, and reference material.

An earlier probe appeared to show separation (0.48 against 1.34) but its control was a single six sentence paragraph written to be deliberately varied. That was not a fair test.

Rhythm may be viable against a corpus of genuine AI output paired with genuine human narrative prose. This repository is not that corpus. Revisiting it is a research spike, not an implementation task.

## Architecture

One new module. The dependency graph gains one edge and stays acyclic: `scanner` depends on `analyzers`, `analyzers` depends on `document`, nothing depends on `scanner`.

### The analyzer contract

An analyzer is a function `(doc, cfg) -> list[dict]` returning entries shaped:

```
{"message": str, "lines": [int, ...]}
```

`lines` holds the source line numbers that evidence the finding. An analyzer does not build a complete finding and does not know about suppression, severity, or line ranges.

Analyzers are registered in an `ANALYZERS` list whose entries carry the same keys a rule row carries, with `fn` in place of `pattern` and `kind`:

```
{"name": "structure", "id": "structure.bold_headers",
 "category": "structure", "severity": "low", "fn": mechanical_bold_headers}
```

Sharing `name` and `id` is the design. `config.is_disabled(row, path)`, `config.severity_for(row)`, and `Suppression.covers(line, name, id)` read those two fields and nothing else, so every Phase 1 control applies to analyzers with no change to those modules. Because the five frames also carry `name: "structure"`, a repo can disable structural detection wholesale with `structure` or one member with `structure.bold_headers`, matching how `puffery` and `puffery.crucial` already behave.

### The scanner's third pass

`scanner.scan` gains a pass after line scope and document scope. For each registered analyzer not disabled by config, it calls `fn(doc, cfg)` and converts each returned entry into a finding, applying the same semantics document scope rules already use:

1. Drop any evidence line covered by a suppression for this rule name or id.
2. Drop the entry entirely when no evidence line survives.
3. Under `--lines`, keep the entry only when at least one evidence line falls inside a changed range.
4. Tag with `cfg.severity_for(row)`.
5. Emit with `line` set to the first surviving evidence line, so the finding points somewhere real.

Analyzers therefore inherit diff scoping and suppression without containing any code for either.

The two existing passes are untouched.

### Reading sources

The bold header analyzer reads `doc.lines`, the raw lines, because `mask_line` replaces the bullet marker it needs to see. This is the first consumer of raw lines for matching rather than for snippets, and the reason belongs in a code comment so nobody switches it to `scan_lines` for consistency.

## The five frames

Six line-scope regex rows, each with an explicit `id` and a `term` for display, since Phase 1 established that a raw pattern must never reach a developer's terminal. All carry `name: "structure"` and `severity: "low"`.

<!-- voice-check: disable structure -->

### Negative parallelism, `structure.not_just_but`

```
\bnot (?:just|only|merely|simply)\b[^.!?\n]{1,80}?(?:,\s*)?\b(?:but|it['’]?s|it is)\b
```

Covers "not just X, but Y" and the variant "not just X, it is Y".

### Contrast reframe, `structure.not_about_but_about`

```
\b(?:it|this|that)['’]?s not about\b[^.!?\n]{1,80}?\b(?:it|this|that)['’]?s about\b
```

### Balanced debate, two rows

The tell appears two ways, so it gets two rows.

`structure.while_also` catches the concessive frame:

```
\bwhile\b[^.!?\n]{1,80}?,\s*(?:it|they|there)\s+also\b
```

`structure.advantages_disadvantages` catches the paired nouns form:

```
\b(?:advantages?|benefits?|strengths?)\b[^.!?\n]{0,60}?\b(?:disadvantages?|drawbacks?|weaknesses?|downsides?)\b
```

### Challenges and prospects, `structure.despite_faces_challenges`

```
\bdespite\s+(?:its|their|these|the)\b[^.!?\n]{1,80}?\bfaces?\b[^.!?\n]{0,40}?\bchallenges?\b
```

Requiring all three beats keeps ordinary concessive sentences out. "Despite budget challenges, we shipped" does not fire, because there is no "faces".

### False ranges, `structure.false_range`

```
\bfrom\s+[a-z]+s\b[^.!?\n]{0,30}?\bto\s+[a-z]+s\b
```

This is the highest risk frame in the set, because "from X to Y" is ordinary English. A bare pattern would fire on "from 9 to 5" and "from the store to home" constantly.

The tell is a false enumeration of scope, and it has a syntactic signature: lowercase plural to lowercase plural. Restricting to that shape excludes numbers, proper nouns, and singular objects, which is most of the false positive surface. Verified silent on "from 9 to 5", "from the store to home", "from src to dist", "from 3 to 7", and "from London to Paris"; verified firing on "from startups to enterprises" and "from teams to organizations".

**Known miss, accepted deliberately.** Gerund ranges such as "from onboarding to offboarding" do not fire, because a gerund is not a plural. Broadening to `[a-z]+(?:s|ing)` would catch them but would also fire on "from testing to shipping", which describes a genuine sequence rather than a false spectrum. Gerund pairs are more often real orderings than plural noun pairs are, so the conservative form is preferred and the miss is documented.

<!-- voice-check: enable -->

### Calibration

<!-- voice-check: disable structure -->

Running all six patterns over this repository's markdown, twenty two files at the time of writing, produces fifteen hits and zero false positives on genuine prose:

| Rule | Hits |
| --- | --- |
| `structure.not_just_but` | 5 |
| `structure.not_about_but_about` | 3 |
| `structure.while_also` | 3 |
| `structure.advantages_disadvantages` | 1 |
| `structure.despite_faces_challenges` | 3 |
| `structure.false_range` | 0 |

Every hit lands in a file that quotes these patterns as examples: `references/examples.md` (four hits, its deliberate "before" samples), `references/rules.md` (four hits), `specs/2026-08-11-voice-check-upgrade-design.md` (three hits), `references/wikipedia-signs.md` (three hits), and this file (one hit, its own worked note two sections up confirming that "not only X but Y" fires). Each is a document about the rules rather than a document exhibiting them, which is what suppression exists for.

A single line can carry more than one match of the same rule. `references/wikipedia-signs.md` line 90 opens with a short "not just" construction and, later in the same sentence, an independent "not only" one, so the engine's `finditer` scan finds two non overlapping `not_just_but` matches on that one line, not one. Counting matched lines instead of matched occurrences undercounts a table like this one; count occurrences.

<!-- voice-check: enable -->

## The bold header analyzer

`mechanical_bold_headers(doc, cfg)` counts bullet lines in `doc.lines` and, among them, those opening with a bold run:

```
bullet:  ^\s*[-*+]\s+
bolded:  ^\s*[-*+]\s+\*\*[^*\n]+\*\*
```

It returns one entry when both hold: at least `MIN_BULLETS` bullets exist, and the bolded fraction is at least `RATIO_THRESHOLD`. Evidence lines are the bolded bullet lines.

`MIN_BULLETS` is 4 and `RATIO_THRESHOLD` is 0.6, chosen from measurement rather than taste. Bolded fraction across this repository:

| Document | Bullets | Bolded |
| --- | --- | --- |
| `README.md` | 14 | 86% |
| `references/rules.md` | 10 | 80% |
| `plans/2026-08-11-voice-check-upgrade.md` | 112 | 8% |
| every other file | | 0% to 20% |

The gap between 80% and 20% is wide, so the threshold is not finely balanced.

A ratio is why this cannot be a rule row. `doc_min` is an absolute count, so a document with 100 bullets and 5 bolded would satisfy `doc_min: 4` while being 5% bolded. Expressing "most bullets" requires computing over the document, which is the entire reason `analyzers.py` exists.

### The glossary exception

The threshold flags this project's own `README.md` and `references/rules.md`. Both are definition lists whose bullets read like `- **Hard rules [engine]:** em dashes, en dashes, ...`, where a bolded term per entry is conventional.

The rule as `references/rules.md` states it ("Use sparingly, not mechanically") does describe both files. Rather than weaken the rule with a heuristic for what counts as a glossary, both files receive a targeted suppression naming `structure.bold_headers` specifically, with a comment saying they are definition lists. Other repositories still get the detection.

This is recorded as a known tension rather than settled: if the rule proves noisy in practice, narrowing it to fire only when the bold run is a full sentence, or only when no colon follows, is the first thing to try.

## Error handling

Phase 1 built the safety net; this phase adds two things.

Each analyzer call is wrapped individually, so one raising analyzer cannot take out the others, the rule passes, or the scan. A failure prints a warning to stderr naming the analyzer and continues.

This is the one place the project's "degrade toward reporting more" principle cannot hold, since a failed analyzer necessarily reports less. Crashing would be worse, and `voice_check.py`'s existing handler already guarantees exit 0 under `--report-only`.

Analyzer guards return an empty list rather than dividing by zero: no bullets at all, fewer than `MIN_BULLETS`, or an empty document.

## Testing

### Negative tests carry the weight

For frames, false positives are the risk, so every frame gets a negative test built from ordinary English that must stay silent. These matter more than the positives:

- "I could not just sit there and watch" against `not_just_but`
- "Despite budget challenges, we shipped" against `despite_faces_challenges`
- "We work from 9 to 5", "She walked from the store to home", "Copy the file from src to dist" against `false_range`
- "While the tests ran, we reviewed the diff" against `while_also`
- "It's not about money" against `not_about_but_about`
- "The benefits are clear and worth the effort" against `advantages_disadvantages`

<!-- voice-check: disable structure -->
Note that "He was not only tired but hungry" **does** fire `not_just_but`, and should. "Not only X but Y" is the same negative parallelism construction that `references/rules.md` names, so firing there is correct behavior rather than a false positive.
<!-- voice-check: enable -->

### Calibration as a regression test

A test asserts the six frames produce exactly the recorded counts across this repository's own markdown. If a later change broadens a pattern, that test fails and names the rule. Phase 1 shipped two constants that nothing pinned, and both returned as review findings; this is the mechanism that prevents a repeat.

### Analyzer boundaries

Both dimensions get boundary tests: 3 bullets does not fire and 4 does, 59% does not and 60% does. Plus the case `doc_min` cannot express, many bullets with few bolded, which must stay silent.

### Analyzer machinery inherits Phase 1

Coverage proving the contract genuinely works rather than appearing to: disable by name removes it, disable by id removes it, a severity override reaches it, a suppression over an evidence line drops it, and under `--lines` it survives only when an evidence line falls inside a changed range.

### Self scan

`README.md` and `references/rules.md` carry a suppression naming `structure.bold_headers` alone, not a blanket ignore. `references/rules.md` also adds `structure` to its existing suppression range, since it quotes the frames. Every other self scan target must stay clean with no suppression, which doubles as the check that the frames are not over firing on real prose.

Two reference files fire on the frames without being pinned by any test today: `references/examples.md`, whose "before" samples deliberately exhibit these patterns, and `references/wikipedia-signs.md`, which describes them. Both receive a suppression range for `structure` as part of this phase. Shipping a tool that reports findings on its own reference material is poor hygiene even where no test catches it.

## Documentation changes

`references/rules.md` moves five Structural Tells bullets from `[skill only]` to `[engine + skill]`: negative parallelisms and contrast reframes, false ranges, challenges and future prospects, balanced debate framing, and bolded inline headers.

Three remain `[skill only]`, each with its reason recorded: rule of three and elegant variation need semantics, and uniform rhythm was measured and found not to discriminate. The rhythm table above is summarized there so the decision is not re-litigated from scratch.

`README.md` gains the new rule ids in its "What it catches" list. `CLAUDE.md` gains `analyzers.py` in the module description and an updated test count. `plugin.json` goes to 2.4.0, a feature release with no breaking change.

## Alternatives considered

**A `computed` rule kind inside the existing table.** Add `kind: "computed"` with an `fn` key and dispatch on it in the scanner. One registry, and machinery reuse is automatic rather than by convention. Rejected because it turns `RULES` from pure data into part data and part code, and `rules.py` is the file a contributor opens to add a banned word. The compile cache keyed on pattern would also need a carve out.

**Synthetic markers.** Compute the metric, inject a sentinel token into the text, let an ordinary regex row match it. The smallest possible diff and no new machinery. Rejected because findings would then report positions that do not exist in the source, and debugging a rule that fires on text nobody wrote is miserable. Recorded so it is not reinvented.

## Success criteria

1. The paragraph quoted in Context reports at least three structural findings.
2. The six frames produce exactly the recorded counts across this repository's markdown, pinned by a test.
3. Every frame has a negative test drawn from ordinary English that stays silent.
4. `mechanical_bold_headers` fires on a document with 4 or more bullets that is 60% or more bolded, and stays silent below either threshold.
5. A document with many bullets and few bolded stays silent, demonstrating the case `doc_min` cannot express.
6. An analyzer is disabled by rule name and independently by rule id.
7. A suppression directive over an evidence line drops an analyzer finding.
8. Under `--lines`, an analyzer finding survives only when an evidence line falls inside a changed range.
9. A raising analyzer warns on stderr and leaves every other finding intact.
10. The self scan reports zero on `README.md`, `references/rules.md`, and both Phase specs. The only new suppressions are the two targeted `structure.bold_headers` comments, plus `structure` added to the existing suppression ranges in files that quote the frames as examples, which are `references/rules.md` and this specification.
11. The hook still exits 0 in every case.
12. The full suite passes.
