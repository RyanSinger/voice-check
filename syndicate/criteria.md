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

## 7. Pre-commit hook end-to-end integration (added gen-1 ratchet)

The installed pre-commit hook actually works on a real repo. Covered by a test or verified procedure that: installs the hook via `install-hook.sh` into a temp repo, stages a dirty markdown file, runs the hook script (or `git commit`), confirms the engine findings appear on stderr, and confirms the hook exits 0 (advisory).

- 5: integration test exists in the pytest suite, passes, and covers both the install flow (templates substitution) and the runtime execution path.
- 3: a manual verification procedure is documented and proven to work, but not automated as a test.
- 1: no coverage; install-hook.sh and the template remain untested end-to-end.

Reason for adding: neither gen-1 variant touched the hook install or runtime path. A silently broken hook template would not be caught by any existing test. This is the next real gap.

## 8. Markdown structural safety (added gen-2 ratchet)

The engine does not fire false positives on common markdown structural elements: indented bullet list items, fenced code blocks, inline code, headings, tables. Verified by expanded clean fixtures and targeted tests.

- 5: dedicated clean fixture includes indented bullets (`  - nested`), fenced code blocks with hyphens inside, inline code with hyphens, and at least one table. A test or the existing clean-fixture test proves the engine reports zero findings on all of it. The fix is landed in the engine, not just documented.
- 3: fix landed but test coverage is thin; or fixture covers only two of the four categories.
- 1: unchanged; indented bullets still produce `no_dashes` false positives.

Reason for adding: running the engine against `- first\n- second\n  - nested` in an ad-hoc fixture produces `no_dashes` findings on the nested bullets because the hyphen-separator regex `\s-\s` matches indented list markers. The clean fixture is too narrow to have caught this. Real documents have bullet lists; this is a blocker for honest use.

## 9. Skill file path integrity (added gen-3 ratchet)

All relative reference paths inside skill files (`plugins/voice-check/skills/*/SKILL.md`) resolve to files that actually exist. Specifically, references to `../../references/rules.md`, `../../references/wikipedia-signs.md`, and `../../references/examples.md` from inside each skill directory resolve to existing files in `plugins/voice-check/references/`.

- 5: a test exists in the pytest suite that programmatically reads each SKILL.md, extracts relative paths it mentions, and asserts each resolves to an existing file from the skill directory.
- 3: a manual verification procedure is documented and passed.
- 1: no coverage; broken reference paths can slip into a release (as they did in v2.0.1).

Reason for adding: v2.0.1 shipped with a broken relative path in SKILL.md that made the skill unusable at runtime. The fix is in git history, but no test catches the class of bug. Three generations of work on the engine and hook leave the skill file discovery path untested. This is the next real gap.



