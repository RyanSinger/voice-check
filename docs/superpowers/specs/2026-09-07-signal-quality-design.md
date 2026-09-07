# Signal Quality (Phase 1)

Date: 2026-09-07
Status: approved, ready for implementation planning

## Context

`voice-check` ships a deterministic Python engine behind an advisory git pre-commit hook. The hook is the only always-on surface, so its output quality decides whether the tool gets trusted or muted.

Probing the current engine against real files surfaced four defects:

1. **No mention versus use distinction.** Running the engine on this repo's own `README.md` produces dozens of findings, every one of them from a quoted rule name. Blockquotes match. URLs match: a link containing `state-of-the-art-review` was reported as puffery.
2. **No suppression of any kind.** No inline directive, no per-file exclude, no baseline. A document already judged fine reports the same findings on every commit forever.
3. **Whole-file scanning.** The hook pipes the entire staged file to the engine, so touching one line of an old document inherits that document's full violation history.
4. **Word lists misfire on technical prose.** A four line file containing `API key`, `the key is read`, `Align the config`, and a sentence opening with `Additionally` trips the vocabulary cluster rule.

Two further defects surfaced while designing:

5. **Supplement loading swallows its own errors.** `voice_check.py` wraps supplement loading in a bare `except Exception`, so a single bad line silently discards every custom rule in a repo's supplement.
6. **Document-scope rules skip inline code masking.** `scan_text` builds its document-scope input with `_strip_code_blocks`, which handles fenced blocks only. Line-scope rules get inline code masking from `_prepare_line_for_rules`, but document-scope rules bypass it and match against raw text. Running the engine on this specification reports a vocabulary cluster of 12 occurrences, every one of them inside backticks.

## Scope

Phase 1 covers the Precision and Control directions from the parent decomposition. Phase 2 (structural detection) and Phase 3 (additional surfaces) get their own specs.

In scope:

- Mention versus use masking
- In-document suppression directives
- Stable per-row rule identity
- Per-repo rule disabling, severity overrides, and path exclusion
- Severity as a display and filtering mechanism
- Staged-diff scoping in the hook

Out of scope:

- Structural tell detection (Phase 2)
- Surfaces beyond markdown (Phase 3)
- Deterministic auto-fix
- Any change to the advisory contract

## Constraints

- The engine stays Python standard library only.
- The pre-commit hook stays advisory and always exits 0. Severity never blocks a commit.
- The `# === voice-check section start/end ===` hook contract is preserved.
- No dashes in any prose output, including commit messages and documentation.
- Python 3.11 or later.

## Architecture

Five modules, each answering one question. The dependency graph is acyclic and shallow: `voice_check` depends on `scanner`; `scanner` depends on `document`, `rules`, and `config`; those three depend on nothing beyond the standard library.

### `document.py`: what text is prose?

`Document.from_markdown(text)` returns an object holding:

- `lines`: the raw lines, used for finding snippets
- `scan_lines`: a parallel list of masked lines, used for line-scope matching
- `prose_text`: the masked full text, used for document-scope rules

Masking replaces hidden characters with spaces rather than deleting them, so column numbers stay aligned with the raw line and findings can still quote the original.

`prose_text` is built by joining `scan_lines`, not by a separate pass over the raw text. That construction is load bearing: it guarantees line-scope and document-scope rules see identical masking, which closes defect 6. The current engine derives its document-scope input independently and therefore misses inline code.

`prose_text` is also what allows document-scope rules to count occurrences on masked text. Counting has to happen after masking, which is why a post-filter approach was rejected (see Alternatives).

Block level masking runs first, in this order:

1. YAML frontmatter, recognized only when line 1 is exactly three hyphens, masked through the closing delimiter
2. Fenced code blocks, toggled on the existing fence pattern, fence lines included
3. HTML comments, including those spanning multiple lines

Line level masking then runs on the remainder:

4. Inline code spans
5. URLs matching an `http` or `https` scheme, and bare `www.` prefixes
6. Markdown link targets, masking inside `](...)` while leaving `[text]` scanned, plus reference definitions
7. Autolinks in angle brackets
8. Short quoted spans (see below)
9. Blockquote lines, recognized by a leading `>`, masked entirely
10. Leading bullet list markers

### Quoted span policy

A quoted span is masked when its content holds fewer than seven words. Longer quotations stay scanned, on the reasoning that a quoted paragraph is usually the author's own pull quote rather than a mention. Seven is one more than the word count of the longest expression the engine can match, "at the end of the day," so that expression can still be quoted as a mention rather than firing the rule that bans it.

Only double quotes participate, both straight and curly. Single quotes are deliberately excluded because apostrophes make them ambiguous: in the text `it's a 'test' case`, a naive single quote pattern matches the span `s a `, masking real prose.

Verified against the observed failures. These mask:

```
"would like to," "could potentially," "it is worth noting"
"groundbreaking," "renowned," "pivotal," "crucial," "testament"
https://example.com/state-of-the-art-review
> Our product is groundbreaking.
```

This does not mask, by design, and falls to suppression instead:

```
Additionally (starting sentences), align with, crucial, delve, emphasizing
```

No masking heuristic should catch an unquoted list of banned words. Suppression is the correct tool for a document that lists them.

### `config.py`: what rules apply here, and how loudly?

Absorbs and replaces `supplement.py`. Retains `find_for`, walking up from the target file to the git root and stopping at the first `.claude/voice-check.md`, with no aggregation across levels.

Parses the three existing fenced block kinds (`voice-check-words`, `voice-check-phrases`, `voice-check-regex`) and three new ones:

```voice-check-disable
puffery.crucial
ai_vocab_cluster
vocab_2026 in docs/reference/**
```

```voice-check-severity
puffery = low
no_dashes = high
```

```voice-check-exclude
CHANGELOG.md
docs/vendor/**
```

A disable line accepts either a rule name, covering every row under that name, or a single rule id. An optional `in <glob>` suffix scopes the disable to matching paths.

Returns a `Config` carrying extra rule rows, disabled identifiers, severity overrides, and excluded path globs.

### `rules.py`: what are the rules?

Shrinks to the rule table plus compilation. Three changes:

**Stable rule ids.** Today `puffery` names thirteen rows, so no individual row can be disabled or suppressed. Word and phrase rows generate `<name>.<slug>` deterministically from their pattern, yielding `puffery.groundbreaking` and `hedging.would_like_to` without hand authoring. The small number of hand written regex rows carry an explicit `id` field.

**Default severity per row.** Assignments:

- `high`: `no_dashes`, `markup_artifacts`. Both are mechanical and unambiguous.
- `low`: `ai_vocab_cluster`. This is the rule that fired on a technical document containing `API key` and `Align the config`.
- `medium`: everything else.

**Dead code removal.** The back-compat exports (`AI_VOCAB_CLUSTER`, `PUFFERY_WORDS`, `PROMOTIONAL_PHRASES`) and shim functions (`check_dashes`, `check_puffery`, `check_promotional`, `check_ai_vocab_cluster`) have no call sites anywhere in the repository. Verified by grep across `engine/`, `tests/`, `skills/`, and `templates/`. Roughly 100 lines are deleted.

### `scanner.py`: what is wrong with this document?

Takes a `Document` and a `Config`, runs the applicable rows, applies suppression directives, and returns findings tagged with severity. This is the only module aware of both rules and documents.

### `voice_check.py`: the CLI

Gains `--min-severity {high,medium,low}` and `--lines <ranges>`. Retains `--report-only`. Always exits 0 in report-only mode.

## Suppression directives

Directives are HTML comments, so they travel with the file and stay invisible in rendered markdown. Three forms:

- `<!-- voice-check: ignore -->` on a line suppresses findings on that line
- `<!-- voice-check: disable -->` paired with a later `<!-- voice-check: enable -->` suppresses the block between them
- `<!-- voice-check: disable -->` with no matching `enable` suppresses from that point to end of file

The block and file forms share a token, resolved by whether a matching `enable` appears later in the file.

Every form accepts optional arguments: a rule name, a rule id, or a comma separated list of either. With no arguments, all rules are suppressed.

Two ordering constraints govern the implementation:

1. `document.py` masks HTML comments, so directives must be parsed from the raw text **before** masking runs, or the directives erase themselves.
2. Directive parsing must **skip fenced code regions**. `references/rules.md` will document this syntax inside a fenced block, and a documented example must not take effect.

## Diff scoping

The hook computes changed line ranges per staged file using `git diff --cached -U0` and passes them to the engine as `--lines 12-18,40-41`.

Line-scope findings outside the supplied ranges are dropped.

Document-scope rules need an explicit answer, because a vocabulary cluster is a property of the whole file rather than of a line. The rule: **report a document-scope finding only when at least one of its occurrences falls inside a changed range.** An author is told about a cluster they introduced and is not nagged about one they never touched.

Diff scoping is hook only. Manual `/voice-check <file>` and any CLI invocation without `--lines` scans the whole file.

## Severity display

`--min-severity` defaults to `medium`.

Findings at or above the threshold print in full with their snippet, matching today's format plus a severity label. Findings below the threshold collapse into a single summary line:

```
1 finding below medium severity (ai_vocab_cluster). Re-run with --min-severity low for detail.
```

One knob controls verbosity, and nothing is hidden without a trace.

## Data flow

```
raw text
  parse suppression directives (skipping fenced regions)
  build Document (block masking, then line masking)
  select rule rows (built in, plus supplement, minus disabled, minus path excluded)
  scan line scope against scan_lines
  scan doc scope against prose_text
  tag findings with severity (defaults, then config overrides)
  drop findings suppressed by directive
  drop findings outside --lines ranges
  collapse findings below --min-severity
  format and print
  exit 0
```

## Error handling

The governing principle: **every degradation path falls toward reporting more, never toward silently reporting less.** The one exception is an outright crash, where printing nothing beats blocking a commit.

| Failure | Behavior |
| --- | --- |
| Bad line in a supplement block | Skip that line, warn on stderr with file and line number, load the rest. Replaces the current bare `except Exception` that discards the whole supplement. |
| Invalid regex in a supplement | Catch `re.error` at compile time, drop that row, warn. |
| Unknown rule id in a disable block | Warn, continue. Rule ids shift between versions and a stale disable must not be fatal. |
| Non UTF-8 target file | Read with `encoding="utf-8", errors="replace"`. A binary file yields junk findings at worst instead of a traceback. |
| Malformed `--lines` | Ignore the flag, warn, scan the whole file. |
| `git diff --cached -U0` fails in the hook | Fall back to whole file scanning. |
| Unexpected exception under `--report-only` | Print a one line notice to stderr, exit 0. |
| Unexpected exception without `--report-only` | Raise, so debugging stays possible. |

Warnings print once per run rather than once per scanned file.

## Testing

### Prerequisite: the suite is red and CI does not see it

Two defects block the testing plan and must be fixed first.

`test_install_hook_renders_engine_path` fails on a clean checkout of `main`. Commit `6e7b700` renamed the hook variable from `VOICE_CHECK_ENGINE=` to `BAKED_ENGINE=`, and the test still searches for the old name. The assertion is checking the right property, that placeholder substitution produced an absolute path to an existing file, and only reads the wrong variable.

The failure went unnoticed because `.github/workflows/test.yml` runs `pytest tests/test_engine.py` rather than `pytest tests/`. The eight tests in `test_hook_pipeline.py` and `test_skill_paths.py` have never run in CI.

Phase 1 adds substantially to the hook pipeline tests, so both are prerequisites:

1. Update the assertion to read `BAKED_ENGINE=`.
2. Change the workflow to run `pytest tests/ -v`.

### Current state

The suite holds 63 tests (55 engine, 5 hook pipeline, 3 skill paths), of which 62 pass. Phase 1 should land near 110, all passing, all running in CI.

### Regression fixtures from observed failures

The highest value additions are drawn from real defects rather than synthetic cases. Each asserts zero findings after Phase 1:

- The rule listing lines from this repo's `README.md`
- A line containing a URL with `state-of-the-art-review` in its path
- The four line technical document containing `API key`, `the key is read`, `Align the config`, and a sentence opening with `Additionally`

### Self-scan test

Run the engine over this repository's own `README.md` and `references/rules.md` and assert zero findings, with `rules.md` carrying whatever suppression directive it needs. This puts the question of whether the tool trusts its own documentation into CI.

### Document-scope masking tests

A document quoting six vocabulary words must report zero findings, proving masking runs before counting. This converts the reason for rejecting the post-filter approach into a permanent guard.

A document mentioning vocabulary words only inside inline code backticks must report zero findings, covering defect 6. A companion test asserts that line-scope and document-scope rules receive byte identical masked input, so the two scopes cannot drift apart again.

This specification file itself is a usable fixture for both: before Phase 1 it reports a cluster of 12 occurrences across `additionally`, `align`, and `key`, every one of them inside backticks.

### Unit coverage

- `document.py`: one positive and one negative per mask kind; the seven word boundary (six words masks, seven does not); single quotes deliberately unmasked, using `it's a 'test' case`; link text scanned while link target is masked; a column alignment assertion proving `col` still points at the correct character after masking
- `config.py`: each new block kind; path scoped disable; unknown rule id warns without failing; one bad line does not discard the rest of the config; invalid regex dropped with a warning
- Suppression: line form, block form, unterminated block running to end of file, rule name versus rule id arguments, and a directive inside a fenced code block having no effect
- Severity: default assignment per rule, config override, threshold filtering, collapse line format
- Diff scoping: line-scope findings inside and outside ranges; document-scope reported when an occurrence is inside a range; document-scope dropped when all occurrences fall outside; malformed `--lines` degrading to a whole file scan
- Hook pipeline: extend the existing test to cover the `git diff --cached -U0` path and the git unavailable fallback

## Documentation and integration changes

`skills/voice-check/SKILL.md` step 4 instructs the model to re-run until the engine reports zero findings. Severity collapsing makes "zero findings" ambiguous, so the skill must invoke the engine with `--min-severity low` to see everything. The same applies to the verification step in `skills/writing-guard/SKILL.md`.

Also updated in Phase 1:

- `references/rules.md`: document the suppression directive syntax and the new supplement block kinds
- `README.md`: document severity, suppression, diff scoping, and the new configuration blocks
- `CLAUDE.md`: refresh the module description and the test count
- `plugin.json`: version bump

## Alternatives considered

**Grow the existing scanner in place.** Expand `_prepare_line_for_rules` into a fuller masker, derive rule ids inline, parse suppression in the same loop. Smallest diff, and consistent with the constrain-beats-invert outcome recorded in gen-3 of the prior run. Rejected because `rules.py` already holds 533 lines spanning rule data, compilation, scanning, and shims. Adding masking, identity, suppression, and severity produces a file that must be read in full before any change to it.

The gen-3 notes rejected a separate `markdown_view.py` module as premature, correctly at the time: one consumer and one concern meant the split did not pay for itself. Phase 1 changes that arithmetic by adding four concerns at once, and Phase 3 adds a second consumer in commit messages and plain text.

**Post-filter the findings.** Leave the scanner untouched and filter its output: drop findings whose column lands inside a masked span, drop suppressed rules, drop findings outside the diff range, sort by severity. Attractive because it risks nothing against the existing suite.

Rejected on a structural defect. Document-scope rules count occurrences during the scan, so filtering afterward cannot correct the count. This repository's `README.md` would still report a cluster of six occurrences across five words and then have no findings left to display. Masking has to precede counting.

## Success criteria

1. The engine reports zero findings on this repository's `README.md`, `references/rules.md`, and this specification file.
2. The technical document fixture containing `API key` and `Align the config` reports zero findings.
3. A URL containing a flagged term in its path produces no finding.
4. A supplement with one malformed line still loads its remaining rules.
5. Editing one line of a document with pre-existing violations elsewhere reports only findings on the edited line.
6. A repo can disable a single rule row by id and a whole rule by name.
7. The hook still exits 0 in every case, including on malformed configuration and unreadable files.
8. Line-scope and document-scope rules operate on identical masked input.
9. The full suite passes, including every test listed above.
