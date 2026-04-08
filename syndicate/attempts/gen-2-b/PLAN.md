# Plan (gen-2-b, borrow variant)

1. Sync baseline from syndicate/run-1 (done).
2. Read install-hook.sh and pre-commit.sh to learn the real interface.
3. Add `tests/test_hook_pipeline.py` (stdlib only) that:
   a. Copies nothing. Invokes the repo's real `templates/install-hook.sh` with a fresh `tmp_path` git repo (git init, user.name/email set).
   b. Asserts `.git/hooks/pre-commit` exists, is executable, contains the marker pair, and the `__VOICE_CHECK_ENGINE__` placeholder is gone and replaced with an existing absolute path.
   c. Runs `install-hook.sh` a second time. Asserts exactly one marker-start and one marker-end (idempotence).
   d. Stages a dirty markdown file, runs `.git/hooks/pre-commit` directly, asserts exit 0 and that stdout contains at least one known rule name (e.g. `no_dashes`) plus the `voice-check: scanning` banner.
   e. Stages only a clean markdown file, runs the hook, asserts exit 0 and no `--- ` finding banner.
4. Use `GIT_AUTHOR_*` / `GIT_COMMITTER_*` env for any git work; no global config writes.
5. Commit on worktree branch. Static-trace each assertion in REPORT.md since python3 is sandboxed.
