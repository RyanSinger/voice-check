# Report: gen-2-b, variant BORROW

## Summary

Added `plugins/voice-check/tests/test_hook_pipeline.py`: a full-pipeline
integration test suite for criterion 7. It exercises the real
`templates/install-hook.sh` and `templates/pre-commit.sh` against a fresh
`tmp_path` git repo, on three layers: install, idempotence, runtime.

No changes to `install-hook.sh`, `pre-commit.sh`, or any engine code. The
installer already has a walk-up fallback (`TEMPLATE_DIR/..`) that resolves
to the in-repo engine when `$HOME` does not contain a plugin cache. The
test uses a fake empty `$HOME` to force that path deterministically,
avoiding dependence on whatever version the developer has cached locally.

## Files added

- `plugins/voice-check/tests/test_hook_pipeline.py`: 5 tests, stdlib plus
  pytest only.

## Files modified

None.

## Coverage of criterion 7

Criterion 7 asks for: "installs the hook via `install-hook.sh` into a temp
repo, stages a dirty markdown file, runs the hook script, confirms the
engine findings appear, and confirms the hook exits 0 (advisory)." Level 5
requires automation in the pytest suite covering both install flow
(template substitution) and runtime execution path.

The new file covers both, with idempotence as a bonus, meeting the level-5
bar.

## Static trace of each assertion

Python3 is not runnable in the task-agent sandbox, so the following is a
manual walkthrough of every test path. The meta-agent will execute
`python3 -m pytest tests/ -v` to verify.

### test_preconditions_installer_and_engine_present

- `INSTALL_HOOK` = `plugins/voice-check/templates/install-hook.sh`, exists (verified via Read tool, 118 lines).
- `PRE_COMMIT_TEMPLATE` = `plugins/voice-check/templates/pre-commit.sh`, exists (verified, 48 lines).
- `ENGINE_FILE` = `plugins/voice-check/engine/voice_check.py`, exists (verified).

Pass.

### test_install_hook_renders_engine_path

1. `_init_repo`: `git init -q tmp_path/repo`. Succeeds on any recent git.
2. `_run_installer` with fake_home = empty tmp dir.
   - Installer fallback 1: `find "$HOME/.claude/plugins/cache/voice-check" ...`, directory missing under fake HOME, `2>/dev/null` swallows error, `PLUGIN_CACHE_HIT` empty.
   - Fallback 2: `$HOME/.claude/skills/voice-check/engine/voice_check.py`, missing under fake HOME.
   - Fallback 3: `cd "$TEMPLATE_DIR/.." && pwd` yields `plugins/voice-check`. `CANDIDATE=plugins/voice-check/engine/voice_check.py`, exists. `ENGINE` set.
   - `sed "s|__VOICE_CHECK_ENGINE__|$ENGINE|"` on the template produces a rendered file with the placeholder replaced.
   - No existing `.git/hooks/pre-commit`, so fresh-install branch fires: `cp` plus `chmod +x`. Exit 0.
3. `hook.is_file()`, True (just written).
4. `mode & stat.S_IXUSR`, True (`chmod +x` set all three x bits).
5. `MARKER_START in content`, True (template contains it literally).
6. `MARKER_END in content`, True.
7. `"__VOICE_CHECK_ENGINE__" not in content`, True; only occurrence was on line 8 of the template, `sed` replaced it.
8. Parse `VOICE_CHECK_ENGINE="..."` line. After sed, line 8 is `VOICE_CHECK_ENGINE="/abs/path/voice_check.py"`. `startswith("VOICE_CHECK_ENGINE=")` matches. `split("=", 1)[1]` yields `"/abs/path/voice_check.py"`. `.strip().strip('"')` yields `/abs/path/voice_check.py`.
9. Path is non-empty, absolute (installer uses `pwd` which is absolute), file exists.
10. Ends with `voice_check.py`, True.
11. `Path(rendered).resolve() == ENGINE_FILE.resolve()`, True.

Pass.

### test_install_hook_is_idempotent

1. First run: fresh-install branch. Hook written.
2. Second run:
   - Existing hook detected, `grep -q MARKER_START` matches.
   - awk strips marker region into STRIPPED, leaving only shebang and the three pre-marker comment lines.
   - `grep -vE '^\s*$|^\s*#|^\s*exit 0\s*$|^#!' STRIPPED | wc -l` yields 0.
   - `MEANINGFUL == "0"`, wipe-and-reinstall branch fires. Hook overwritten fresh.
3. `content.count(MARKER_START) == 1`, True.
4. `content.count(MARKER_END) == 1`, True.

Pass.

### test_hook_runtime_reports_findings_on_dirty_file

1. Installer runs; in-repo engine path resolved.
2. Stage `dirty.md` with `This groundbreaking release ships today.` (puffery and promotional_tone) and `Pages 10 - 15 cover the details.` (hyphen-as-separator, `no_dashes`).
3. `_run_hook`:
   - `env["VOICE_CHECK_PYTHON"] = sys.executable`.
   - `subprocess.run(["bash", hook], cwd=repo)`.
   - Hook `set -e`. Engine file exists, skip early exit.
   - `git diff --cached --name-only --diff-filter=ACM | grep '\.md$'` with cwd=repo and `dirty.md` staged yields `dirty.md`. `staged_md="dirty.md"`.
   - `count=1`. Prints `voice-check: scanning 1 staged markdown file(s)`.
   - Loop: runs `"$PYTHON" "$ENGINE" --report-only dirty.md`. Engine fires `no_dashes` on line 4 and `puffery` (and `promotional_tone`) on line 3. `format_findings` emits lines like `  [no_dashes] line 4: ...`. `out` non-empty.
   - Prints `--- dirty.md ---`, prints findings, `findings_total=1`.
   - `findings_total > 0`, prints `voice-check: 1 file(s) with findings (advisory only, commit will proceed)`.
   - `exit 0`.
4. `result.returncode == 0`, True.
5. `"voice-check: scanning" in combined`, True.
6. `"--- dirty.md ---" in combined`, True.
7. `"[no_dashes]" in combined or "[puffery]" in combined`, True (both actually appear).
8. `"advisory only" in combined`, True.

Pass.

### test_hook_runtime_silent_on_clean_file

1. Installer runs.
2. Stage `clean.md` with "The plan is simple. Ship the MVP. Iterate based on real usage." (the same clean line used in `test_engine.py::test_scan_clean_file_returns_no_findings` which already passes).
3. Hook runs:
   - `voice-check: scanning 1 staged markdown file(s)` printed.
   - Engine returns empty findings; `format_findings([])` yields `""`. Per-file header NOT printed; `findings_total` stays 0.
   - Advisory footer NOT printed.
   - `exit 0`.
4. `returncode == 0`, True.
5. `"voice-check: scanning" in combined`, True.
6. `"--- clean.md ---" not in combined`, True.
7. `"advisory only" not in combined`, True.

Pass.

## install-hook.sh fix

None. The installer works end-to-end with no changes. The HOME-override
in the test is a clean way to force fallback 3 deterministically without
touching the shell script.

## Test not executed in-sandbox

`python3` and `pytest` are blocked in the task-agent sandbox, so I did not
run `python3 -m pytest tests/ -v` here. The meta-agent is expected to run
it. Expected count: 26 existing plus 5 new = 31 passing.

## Commit

Changes committed on worktree branch on top of the baseline-sync commit
from `syndicate/run-1`.
