# Phase Transition Rationale

Transitioning from exploration to convergence after gen-3.

## Eligibility

- 3 exploration generations complete (gen-1, gen-2, gen-3).
- 4 mutation operators tried across generations (borrow, decompose, constrain, invert).
- Each generation produced 2 genuinely different variants with clearly distinct architectural stances.

## What exploration surfaced

- **Gen 1** (rule parity + supplement wiring): borrow beat decompose. The data-driven rule table is a better fit for a plugin whose core abstraction is "rules as data"; decomposing into per-category files added boilerplate without earning it.
- **Gen 2** (hook e2e integration): borrow beat constrain. The runtime-only test was too narrow to satisfy criterion 7; the full-pipeline test caught the actual class of bug that criterion 7 exists to prevent. Gen-2 also surfaced a real false-positive bug (indented bullet lists) during scoring, which became the gen-3 ratchet.
- **Gen 3** (markdown structural safety): constrain beat invert. Both were functionally correct and both fixed the bullet-list bug. The surgical fix won on pairwise simplicity; the dedicated preprocessor module would only earn its weight in a larger system with multiple consumers.

## Why the current best won

The final state on `syndicate/run-1` is 35 passing tests covering: 8 rule categories (4 new this round), data-driven rule table, per-repo supplement support with three kinds (words, phrases, regex), full pre-commit hook pipeline (install, idempotence, runtime), markdown structural safety (bullets, fences, inline code). The engine is stdlib-only and runs the suite in under 0.4 seconds.

The README and `references/rules.md` have been updated to tag each rule category as engine-enforced or skill-only, fixing the docs-honesty gap that opened this round.

## What exploration revealed that wouldn't have been obvious upfront

- **The bullet-list false-positive bug** only surfaced because the gen-2 scoring process ran the engine against an ad-hoc file. The original clean fixture was too narrow to catch it. Without exploration-style scoring (run variants, compare, probe), this would have shipped unnoticed.
- **The pairwise tie-breaker in gen-3** showed that architectural diversity (A's colocated guards vs B's dedicated module) matters more than score-based ranking when functional criteria are saturated. Convergence phase will lean on this more.
- **Task agent sandboxes cannot run python3.** The meta-agent must run verification commands after each task completes. This is a persistent constraint that shaped the loop.

## Rationale for the coherence agent

One-sentence summary: three generations of exploration across four mutation operators saturated the functional criteria at 5.00 and surfaced one real bug (markdown false positives) that became a criterion, so transitioning to convergence is genuine saturation, not evaluation gaming.

## Phase: convergence

Starting gen-4 in convergence phase. Ratchet becomes optional; criteria cannot be softened. Stopping conditions now apply: avg 4.8+ for 2+ consecutive gens, or 4.5+ with improvement delta under 0.1 for 3+ consecutive gens.
