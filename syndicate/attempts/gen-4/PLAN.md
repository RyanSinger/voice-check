# Plan: gen-4 criterion 9

## Goal
Add `tests/test_skill_paths.py` to verify every `../../references/*.md` path
inside each `plugins/voice-check/skills/*/SKILL.md` resolves to a real file.

## Steps

1. Baseline-sync from `syndicate/run-1` (done).
2. Read both SKILL.md files, trace regex manually against each.
3. Verify all three reference files exist in `plugins/voice-check/references/`.
4. Write `test_skill_paths.py` with two test functions:
   - `test_skill_file_discovery`: asserts at least 2 SKILL.md files are found.
   - `test_skill_relative_paths_resolve`: for each SKILL.md, extracts relative
     paths via regex and asserts each resolves to an existing file.
5. Add a bonus assertion: each SKILL.md must mention `../../references/rules.md`.
6. Write PLAN.md and REPORT.md to `syndicate/attempts/gen-4/`.
7. Commit all changes.

## Constraints

- stdlib only (pathlib, re).
- No production files touched.
- Plugin root computed from `__file__` for cwd independence.
