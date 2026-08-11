# Worktree Support and Parked Cleanups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The installer and healer work from linked git worktrees (writing to the shared hooks file), plus three text cleanups and a version bump to 2.2.2.

**Architecture:** Both shell scripts locate the hooks directory via `git rev-parse --git-common-dir` (absolute-resolved) instead of assuming a literal `.git` directory. No other logic changes. Spec: `docs/superpowers/specs/2026-08-11-worktree-and-cleanup-design.md`.

**Tech Stack:** Bash, pytest with subprocess.

## Global Constraints

- No em dashes, en dashes, or spaced hyphens in any written output: shell comments, docs, commit messages, plan prose. Compound-word hyphens fine.
- Installer keeps its exit 1 "not a git repo" error path; the healer ALWAYS exits 0 and still requires the marker section (never installs into repos that have not opted in).
- Marker section format and the installer's idempotent replace logic unchanged.
- Run tests from `plugins/voice-check/`: `.venv/bin/python -m pytest tests/test_engine.py -v`. All 52 existing tests stay green.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 0: Baseline

**Files:** none modified.

- [ ] **Step 1: Run the suite**

```bash
cd plugins/voice-check
.venv/bin/python -m pytest tests/test_engine.py -q
```

Expected: 52 passed. If not, STOP and report.

---

### Task 1: Worktree support in installer and healer

**Files:**
- Modify: `plugins/voice-check/templates/install-hook.sh` (hooks-dir resolution, repo guard, one comment)
- Modify: `plugins/voice-check/hooks/heal-hook.sh` (hooks-path resolution)
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Consumes: existing test helpers in `tests/test_engine.py` from the hook self-healing work: `_make_fake_home(tmp_path, versions)`, `_make_repo(tmp_path, hook_text=None)`, `_run_healer(cwd, home)`, `OLD_STYLE_HOOK` template string, `PLUGIN_ROOT` constant. They exist in the file already.
- Produces: `_add_worktree(repo, tmp_path)` helper returning the worktree path.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`)

```python
# ---------------------------------------------------------------------------
# Worktree support: installer and healer resolve the shared hooks dir
# ---------------------------------------------------------------------------

_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.invalid",
}


def _add_worktree(repo, tmp_path):
    """Commit once (worktree add needs a HEAD), then add a linked worktree."""
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init", "-q"],
        check=True, env={**os.environ, **_GIT_IDENTITY},
    )
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", str(wt)],
        check=True, env={**os.environ, **_GIT_IDENTITY},
    )
    return wt


def test_installer_from_worktree_writes_shared_hook(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path)
    installer = PLUGIN_ROOT / "templates" / "install-hook.sh"
    result = subprocess.run(
        ["bash", str(installer), str(wt)],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(home)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    hook = repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert "voice-check section start" in hook.read_text()
    assert os.access(hook, os.X_OK)


def test_healer_heals_from_worktree(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=dead))
    wt = _add_worktree(repo, tmp_path)
    result = _run_healer(wt, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    text = (repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "resolve_engine" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k worktree -v`
Expected: both FAIL. The installer test fails because the current guard rejects the worktree (`.git` is a file there, stderr says "not a git repo"). The healer test fails because the healer's `.git`-directory guard makes it a silent no-op, so "healed" never prints.

- [ ] **Step 3: Update `templates/install-hook.sh`**

Replace these two lines near the top:

```bash
HOOK_DIR="$REPO_DIR/.git/hooks"
HOOK="$HOOK_DIR/pre-commit"
```

with:

```bash
# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git -C "$REPO_DIR" rev-parse --git-common-dir 2>/dev/null) || {
  echo "error: $REPO_DIR is not a git repo"
  exit 1
}
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$REPO_DIR/$GIT_COMMON" ;;
esac
HOOK_DIR="$GIT_COMMON/hooks"
HOOK="$HOOK_DIR/pre-commit"
```

Delete the now-redundant guard block further down:

```bash
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "error: $REPO_DIR is not a git repo"
  exit 1
fi
```

Also replace the comment containing the em dash (currently reading "Otherwise there's other content" followed by an em dash and "append fresh section after the stripped file") with:

```bash
  # Otherwise there's other content: append fresh section after the stripped file
```

- [ ] **Step 4: Update `hooks/heal-hook.sh`**

Replace this block:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0
# The installer only supports normal checkouts (.git directory).
[ -d "$REPO_ROOT/.git" ] || exit 0

HOOK="$REPO_ROOT/.git/hooks/pre-commit"
```

with:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac
HOOK="$GIT_COMMON/hooks/pre-commit"
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS (54 = 52 prior plus 2 new). The existing healer no-op tests must still pass; normal checkouts resolve `--git-common-dir` to `.git` and behave identically.

- [ ] **Step 6: Commit**

```bash
git add templates/install-hook.sh hooks/heal-hook.sh tests/test_engine.py
git commit -m "feat(hooks): install and heal from linked worktrees via the shared hooks dir

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: README fixes and version bump

**Files:**
- Modify: `README.md` (install command block, repo layout test line)
- Modify: `plugins/voice-check/.claude-plugin/plugin.json` (version)

**Interfaces:**
- Consumes: behavior shipped by Task 1.

- [ ] **Step 1: Fix the install command**

In `README.md`, under the heading "### Install the git pre-commit hook in a repo", replace the code block:

```bash
cd /path/to/your/repo
~/.claude/plugins/cache/voice-check/voice-check/*/templates/install-hook.sh
```

with:

```bash
cd /path/to/your/repo
bash "$(ls ~/.claude/plugins/cache/voice-check/voice-check/*/templates/install-hook.sh | sort -V | tail -1)"
```

- [ ] **Step 2: Drop the stale test count**

In `README.md`'s repo layout listing, change the line:

```
      test_engine.py            pytest suite (15 tests)
```

to:

```
      test_engine.py            pytest suite
```

- [ ] **Step 3: Bump the version**

In `plugins/voice-check/.claude-plugin/plugin.json` change `"version": "2.2.1"` to `"version": "2.2.2"`.

- [ ] **Step 4: Verify**

```bash
cd plugins/voice-check
.venv/bin/python -m pytest tests/test_engine.py -q
python3 engine/voice_check.py --report-only ../../README.md
```

Expected: 54 passed. The engine scan must show no dash findings and no findings on the lines edited here (pre-existing findings on the rule-example list around lines 14 through 22 are expected and fine).

- [ ] **Step 5: Commit**

```bash
git add ../../README.md .claude-plugin/plugin.json
git commit -m "docs: deterministic installer command, drop stale test count, bump to 2.2.2

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Post-implementation (manual, not a task)

From this repo root (which has no voice-check hook section), run `CLAUDE_PLUGIN_ROOT=plugins/voice-check bash plugins/voice-check/hooks/heal-hook.sh`; expect silent exit 0 and no hook created, confirming the guard relaxation did not loosen the opt-in boundary.
