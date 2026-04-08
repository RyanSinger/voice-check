# Meta-Agent Notes

Record observations here after each generation. When a pattern recurs enough to be reusable, promote it to a learned agent (procedure) or domain skill (knowledge). Distill this file at round boundaries or when it gets too long. Git preserves the full history.

---

## Gen 1 (exploration)

**Tried:** two approaches to rule-parity + supplement wiring.
- A (decompose): per-category files under `engine/rules/` package, conservative narrow regex, markdown-list supplement format (H2 + bullets), words+phrases only.
- B (borrow): unified data-driven `RULES` table in single `rules.py`, generic scanner, fenced-code-block supplement format, words+phrases+regex kinds.

**Verified:** both passed all tests (A: 25/25, B: 26/26) and kept `clean.md` silent. Ran pytest in each worktree after the task agents reported their sandboxes denied python3 execution. Must run tests myself going forward when delegating to task agents.

**Winner:** B (5.00 avg vs A 4.83). B's edge: third supplement kind (regex), data-driven table aligns with plugin's "rules.md as source of truth" pattern, single-file scanner is cleaner than per-category dispatch.

**Ratchet:** added criterion 7, hook integration end-to-end test. Neither variant exercised `install-hook.sh` or the runtime hook path. Silently broken hook template would slip past the current suite. This is the obvious next gap.

**Coherence:** continue. Clean trajectory, complexity proportional to functional gains.

**Learnings worth carrying:**
- Task agents in isolated worktrees cannot execute python3 under the current sandbox policy. When dispatching a task that needs verification, plan to run the verification commands from the meta-agent's shell after the task completes, not inside the worktree.
- `isolation: "worktree"` forks from main, not from `syndicate/run-1`. The baseline-sync workaround from loop.md worked cleanly in both variants.
- Conservative regex (A) and broader matching (B) both produced zero false positives on clean.md, so the conservative/broad tradeoff was not a tie-breaker. Future rules can lean broader when the negative test is strong.

## Gen 2 (exploration)

**Tried:** two approaches to criterion 7 (hook e2e).
- A (constrain): runtime-only test in test_hook.py, 3 tests, no production file touched. 29 passing.
- B (borrow): full pipeline test in test_hook_pipeline.py, 5 tests (preconditions, install substitution, idempotence, runtime dirty, runtime clean). 31 passing. Fake $HOME trick forces install-hook.sh to use its fallback-3 path, which is the most robust resolver, making the test deterministic regardless of developer cache.

**Winner:** B (5.00 vs A 4.57). Criterion 7 explicitly required both install and runtime, so A's narrow stance cost it 2 points on that one criterion.

**Bug surfaced during scoring:** running the engine on an indented bullet list (`  - nested`) produces `no_dashes` findings because the hyphen-separator regex matches the indented list marker. Clean fixture is too narrow to have caught this. Became the gen-2 ratchet (criterion 8).

**Ratchet:** added criterion 8, markdown structural safety. Clean fixture must include indented bullets, fenced code blocks, inline code, tables, and the engine must not fire on any of them.

**Coherence:** continue. Scores stable at 5.00, complexity proportional.

**Pattern to note:** B won both gen-1 and gen-2 with the borrow operator. Borrow keeps working when the task is "apply a known pattern to a new area" (data-driven rules, full-pipeline tests). Expect it to lose value once the syndicate runs out of known patterns to borrow from. Gen 3 (fixing the bullet-list bug) is a constrain/invert candidate, not borrow.

**Learning to promote?** Not yet. Two generations of borrow-wins isn't enough recurrence. Watch for a third.
