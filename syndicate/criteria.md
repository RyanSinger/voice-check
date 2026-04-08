# Criteria

Score each 1 to 5 (1 = not met, 5 = fully met).

## 1. Rule parity with README

Engine implements all rule categories the README advertises that are deterministic enough for a hook: hedging, copula avoidance, dangling participles, vague attributions. Plus the existing categories (dashes, AI vocab cluster, puffery, promotional tone) remain functional.

- 5: all four new categories implemented with reasonable regex/word lists, no obvious misses in the README's example phrases.
- 3: two or three of the four implemented cleanly.
- 1: none implemented, or implementations are placeholders.

## 2. Supplement wiring

`engine/voice_check.py` CLI finds per-repo `.claude/voice-check.md` via `supplement.find_for()`, parses it for additional banned words or phrases, and reports findings that use those extensions. A supplement with one new banned word produces a finding the base engine would not.

- 5: supplement is parsed, applied, findings are labeled as originating from the supplement, and a test proves it.
- 3: supplement is loaded and applied but not tested or not labeled.
- 1: unchanged, supplement module still unused.

## 3. Zero regressions, zero false positives on clean fixture

All 15 existing tests pass. `tests/fixtures/clean.md` still reports zero findings with the new rules enabled.

- 5: full green, clean fixture is clean.
- 3: clean fixture has a small number of false positives (1 to 2) that are defensible.
- 1: existing tests break, or clean fixture is noisy.

## 4. Test coverage for new rules

Each new rule category has at least one positive test (catches the violation) and one negative test (does not fire on safe phrasing). New test count is roughly proportional to new rule count.

- 5: >=2 tests per new category, covering positive and negative cases.
- 3: positive tests only, no negative coverage.
- 1: new rules added without tests.

## 5. Stdlib-only, acceptable speed

Engine imports nothing outside the Python standard library. Scanning a 500-line markdown file completes in well under a second. No perceptible slowdown on the hook path.

- 5: stdlib only, fast.
- 1: adds a dependency or has a perf cliff.

## 6. Docs honesty

`plugins/voice-check/references/rules.md` and `README.md` accurately describe what the engine catches vs. what only the Claude-loaded skill catches. No rule advertised in the README is silently absent from the engine unless explicitly marked as skill-only.

- 5: docs match reality, explicit engine-vs-skill split where relevant.
- 3: mostly accurate, a minor gap or two.
- 1: still advertises behaviors the engine does not ship.
