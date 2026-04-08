# Dissolution Report

## Outcome

Closed the gap between what the voice-check plugin advertised and what its Python engine actually implemented, wired supplement support into the CLI, added full pre-commit hook pipeline coverage, fixed a real false-positive bug on markdown structural syntax, and added skill file path integrity testing. 38 tests pass. Job complete.

## Stopping Reason

Judgment call under the "ship a good deliverable, don't run forever" principle. Four generations saturated the functional criteria at 5.00 avg across nine criteria. The formal convergence stopping condition (two consecutive convergence generations at 4.8+) was not yet triggered because only one convergence generation ran, but the deliverable is genuinely at ceiling for the original goal and further generations would target new concerns rather than refine the current one.

## Rounds Summary

Single round, four generations:

- **gen-1** (exploration, borrow beat decompose): data-driven RULES table in rules.py, four new rule categories (hedging, copula avoidance, dangling participles, vague attributions), supplement wiring with three kinds (words, phrases, regex). 26 tests.
- **gen-2** (exploration, borrow beat constrain): full pre-commit hook pipeline test covering install, idempotence, and runtime. 31 tests. Surfaced a false-positive bug on indented bullet lists during scoring.
- **gen-3** (exploration, constrain beat invert): surgical fix for the bullet-list bug plus fence-block and inline-code handling. Broke the borrow-wins streak on pairwise simplicity. 35 tests. Transitioned to convergence after this gen.
- **gen-4** (convergence, single variant, sonnet): skill file path integrity test targeting the class of bug fixed in v2.0.1. 38 tests.

Scores trajectory: 5.00, 5.00, 5.00, 5.00. Complexity grew 13 → 18 files across the run, proportional to functional gains.

## What Was Learned

- **Borrow-wins-when-the-pattern-fits, constrain-wins-when-the-fit-is-gone.** Borrow won gens 1 and 2 because the target work had obvious prior patterns to import (data-driven rules from the single-source-of-truth idea, full-pipeline tests from real-world hook installers). Constrain won gen-3 because no pattern was needed, just a surgical fix. Letting the operator choice follow the task rather than forcing diversity produced better work.
- **Task-agent sandboxes block python3 execution.** Every task agent reported the same constraint. The meta-agent runs the test suite itself after each task. Design task-agent prompts around static-trace verification with the meta-agent doing the final run.
- **Exploration surfaces real bugs through scoring, not planning.** The bullet-list false-positive was found because gen-2 scoring ran the engine against an ad-hoc file, not because anyone planned to test it. Exploration phase is as much about probing as proposing.
- **Merge conflicts on the worktree --squash path are a known workaround cost.** Switch to patch-apply (`git diff baseline-sync HEAD | git apply`) when --squash conflicts. Loop.md documents this pattern; it worked cleanly in gen-3 and gen-4.
- **Pairwise tie-breaking on architectural simplicity is a legitimate convergence signal.** When functional criteria saturate, smaller surface area and fewer files win.

## Deliverable

Path: `plugins/voice-check/` on `syndicate/run-1`. Key changes vs `main`:

- `engine/rules.py`: data-driven RULES table with hedging, copula avoidance, dangling participles, and vague attributions categories added to the existing four. Markdown structural guards (bullet marker strip, fence toggle, inline code strip). Back-compat shims preserved for prior callers.
- `engine/voice_check.py`: supplement discovery wired via `supplement.find_for`. Extras merged into the scan table per invocation.
- `engine/supplement.py`: `load_rows` parses fenced code blocks with info strings `voice-check-words`, `voice-check-phrases`, `voice-check-regex`.
- `tests/test_engine.py`: 26 tests including negatives for each new rule category and supplement integration.
- `tests/test_hook_pipeline.py` (new): five tests covering install, idempotence, and runtime.
- `tests/test_skill_paths.py` (new): three tests verifying SKILL.md relative reference paths resolve.
- `tests/fixtures/clean.md`: expanded with heading, nested bullets, fenced code block, inline code, and table. All stays clean.
- `references/rules.md` and `README.md`: updated to honestly tag each rule as engine-enforced or skill-only.

Total: 38 passing tests, stdlib-only engine, no new runtime dependencies.
