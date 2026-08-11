# Hook Self-Healing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Installed pre-commit hooks survive plugin upgrades with zero user action: the hook re-resolves the engine at commit time, and a plugin SessionStart healer repairs already-stale hooks automatically.

**Architecture:** Two shell changes in `plugins/voice-check/`: the git hook template gains a `resolve_engine` fallback chain, and a new `hooks/` directory registers a Claude Code SessionStart hook that re-runs the installer when it finds a marked hook whose baked engine path is dead. Spec: `docs/superpowers/specs/2026-08-11-hook-self-healing-design.md`.

**Tech Stack:** Bash (templates, healer), JSON (plugin hook registration), pytest with subprocess for tests.

## Global Constraints

- No em dashes, en dashes, or spaced hyphens in ANY written output: shell comments, docs, commit messages, plan prose. Compound-word hyphens ("self-healing") are fine.
- The git hook stays advisory: ALWAYS exits 0, never blocks a commit. The healer also always exits 0; a session must never break because of it.
- The marker section format (`# === voice-check section start ===` / `# === voice-check section end ===`) is unchanged; `install-hook.sh` install/replace logic is unchanged (comments only).
- The healer only repairs repos that already contain the marker; it never installs into new repos.
- Run tests from `plugins/voice-check/`: `.venv/bin/python -m pytest tests/test_engine.py -v`. All 46 existing tests stay green after every task.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 0: Baseline

**Files:** none modified.

- [ ] **Step 1: Run the suite**

```bash
cd plugins/voice-check
.venv/bin/python -m pytest tests/test_engine.py -q
```

Expected: 46 passed. If not, STOP and report.

---

### Task 1: Self-healing hook template

**Files:**
- Modify: `plugins/voice-check/templates/pre-commit.sh` (full replacement)
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Produces: template variable line `BAKED_ENGINE="__VOICE_CHECK_ENGINE__"` and shell function `resolve_engine` (Task 2's healer greps for `BAKED_ENGINE=`; tests grep for `resolve_engine`). Env overrides honored: `VOICE_CHECK_ENGINE` (engine path), `VOICE_CHECK_PYTHON` (interpreter, unchanged).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`; `subprocess`, `sys`, and `Path` are already imported at the top of the file)

```python
# ---------------------------------------------------------------------------
# Hook self-healing: template runtime resolution + SessionStart healer
# ---------------------------------------------------------------------------

import os
import stat

PLUGIN_ROOT = Path(__file__).parent.parent
HOOK_TEMPLATE = PLUGIN_ROOT / "templates" / "pre-commit.sh"
HEALER_SCRIPT = PLUGIN_ROOT / "hooks" / "heal-hook.sh"
ENGINE_SRC_DIR = PLUGIN_ROOT / "engine"


def _make_fake_home(tmp_path, versions):
    """Build a fake HOME containing a plugin cache with the given versions."""
    home = tmp_path / "home"
    for v in versions:
        dst = (home / ".claude" / "plugins" / "cache" / "voice-check"
               / "voice-check" / v / "engine")
        dst.mkdir(parents=True)
        for f in ENGINE_SRC_DIR.glob("*.py"):
            (dst / f.name).write_text(f.read_text())
    home.mkdir(exist_ok=True)
    return home


def _make_repo(tmp_path, hook_text=None):
    """Init a git repo; optionally install pre-commit hook content."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if hook_text is not None:
        hooks_dir = repo / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook = hooks_dir / "pre-commit"
        hook.write_text(hook_text)
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return repo


def _render_hook(engine_path):
    return HOOK_TEMPLATE.read_text().replace(
        "__VOICE_CHECK_ENGINE__", str(engine_path))


def _run_hook(repo, home):
    return subprocess.run(
        ["bash", str(repo / ".git" / "hooks" / "pre-commit")],
        cwd=str(repo), capture_output=True, text=True,
        env={**os.environ, "HOME": str(home)},
    )


def _stage_dirty_md(repo):
    doc = repo / "dirty.md"
    doc.write_text("The plan is simple \u2014 ship it.\n")
    subprocess.run(["git", "-C", str(repo), "add", "dirty.md"], check=True)


def test_hook_resolves_newest_cache_when_baked_path_dead(tmp_path):
    home = _make_fake_home(tmp_path, ["2.1.0", "2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, _render_hook(dead))
    _stage_dirty_md(repo)
    result = _run_hook(repo, home)
    assert result.returncode == 0
    assert "no_dashes" in result.stdout
    assert "engine not found" not in result.stdout


def test_hook_advisory_when_no_engine_anywhere(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, _render_hook(dead))
    _stage_dirty_md(repo)
    result = _run_hook(repo, home)
    assert result.returncode == 0
    assert "engine not found" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k "hook_resolves or hook_advisory" -v`
Expected: `test_hook_resolves_newest_cache_when_baked_path_dead` FAILS (the current template prints "engine not found at" and never scans). `test_hook_advisory_when_no_engine_anywhere` may already pass (the old message contains "engine not found"); that is acceptable, it pins the contract.

- [ ] **Step 3: Replace the template** (`templates/pre-commit.sh`, entire file)

```bash
#!/usr/bin/env bash
# voice-check pre-commit hook (advisory, report-only)
# Installed by: voice-check plugin install-hook.sh
# === voice-check section start ===

set -e

# Baked at install time; fast path while it remains valid. If a plugin
# upgrade moves the cache directory, resolve_engine falls back to the
# newest installed version at commit time, so the hook self-heals.
BAKED_ENGINE="__VOICE_CHECK_ENGINE__"

resolve_engine() {
  if [ -n "${VOICE_CHECK_ENGINE:-}" ] && [ -f "${VOICE_CHECK_ENGINE:-}" ]; then
    echo "$VOICE_CHECK_ENGINE"
    return
  fi
  if [ -f "$BAKED_ENGINE" ]; then
    echo "$BAKED_ENGINE"
    return
  fi
  newest=$(find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
  if [ -n "$newest" ]; then
    echo "$newest"
    return
  fi
  if [ -f "$HOME/.claude/skills/voice-check/engine/voice_check.py" ]; then
    echo "$HOME/.claude/skills/voice-check/engine/voice_check.py"
    return
  fi
  true
}

ENGINE="$(resolve_engine)"

if [ -z "$ENGINE" ]; then
  echo "voice-check: engine not found (is the voice-check plugin installed?), skipping scan"
  exit 0
fi

PYTHON="${VOICE_CHECK_PYTHON:-python3}"

staged_md=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$' || true)

if [ -z "$staged_md" ]; then
  exit 0
fi

count=$(echo "$staged_md" | wc -l | tr -d ' ')
echo "voice-check: scanning $count staged markdown file(s)"

findings_total=0
while IFS= read -r f; do
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    continue
  fi
  out=$("$PYTHON" "$ENGINE" --report-only "$f" 2>&1 || true)
  if [ -n "$out" ]; then
    echo "--- $f ---"
    echo "$out"
    findings_total=$((findings_total + 1))
  fi
done <<< "$staged_md"

if [ "$findings_total" -gt 0 ]; then
  echo ""
  echo "voice-check: $findings_total file(s) with findings (advisory only, commit will proceed)"
  echo "  to fix:    /voice-check <file>"
  echo "  to bypass: git commit --no-verify"
fi

exit 0
# === voice-check section end ===
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS (48 = 46 prior plus 2 new).

- [ ] **Step 5: Commit**

```bash
git add templates/pre-commit.sh tests/test_engine.py
git commit -m "feat(hook): resolve engine at commit time so hooks survive upgrades

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: SessionStart healer

**Files:**
- Create: `plugins/voice-check/hooks/hooks.json`
- Create: `plugins/voice-check/hooks/heal-hook.sh` (mode 755)
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Consumes: `BAKED_ENGINE=` / `VOICE_CHECK_ENGINE=` variable lines in installed hooks (old installs use `VOICE_CHECK_ENGINE=`, Task 1 template uses `BAKED_ENGINE=`); `templates/install-hook.sh` invoked as `bash "$CLAUDE_PLUGIN_ROOT/templates/install-hook.sh" <repo-root>`.
- Produces: `hooks/heal-hook.sh` runnable with env `CLAUDE_PLUGIN_ROOT` set; registered via `hooks/hooks.json`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`; helpers from Task 1's test block are in the same file)

```python
OLD_STYLE_HOOK = """#!/usr/bin/env bash
# === voice-check section start ===
VOICE_CHECK_ENGINE="{engine}"
if [ ! -f "$VOICE_CHECK_ENGINE" ]; then
  echo "voice-check: engine not found at $VOICE_CHECK_ENGINE"
  exit 0
fi
exit 0
# === voice-check section end ===
"""


def _run_healer(cwd, home):
    return subprocess.run(
        ["bash", str(HEALER_SCRIPT)],
        cwd=str(cwd), capture_output=True, text=True,
        env={**os.environ, "HOME": str(home),
             "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)},
    )


def test_healer_replaces_stale_section(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=dead))
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    hook = repo / ".git" / "hooks" / "pre-commit"
    text = hook.read_text()
    assert "resolve_engine" in text
    assert os.access(hook, os.X_OK)


def test_healer_noop_when_baked_path_healthy(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    live = (home / ".claude" / "plugins" / "cache" / "voice-check"
            / "voice-check" / "2.2.0" / "engine" / "voice_check.py")
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=live))
    before = (repo / ".git" / "hooks" / "pre-commit").read_bytes()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert (repo / ".git" / "hooks" / "pre-commit").read_bytes() == before


def test_healer_noop_without_marker(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    repo = _make_repo(tmp_path, "#!/bin/sh\nexit 0\n")
    before = (repo / ".git" / "hooks" / "pre-commit").read_bytes()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert (repo / ".git" / "hooks" / "pre-commit").read_bytes() == before


def test_healer_noop_outside_git_repo(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    plain = tmp_path / "plain"
    plain.mkdir()
    result = _run_healer(plain, home)
    assert result.returncode == 0
```

Note: `test_healer_noop_outside_git_repo` runs with cwd `tmp_path/plain`, which sits under pytest's tmp root, not under this repository, so `git rev-parse` fails there... unless the system tmp dir is itself inside a repo, which it is not. No special handling needed.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k healer -v`
Expected: all 4 FAIL (HEALER_SCRIPT does not exist yet; subprocess fails or bash errors on a missing file, either way the asserts do not hold for the heal case, and the noop cases fail on the missing script's nonzero exit).

- [ ] **Step 3: Create `hooks/heal-hook.sh`** (chmod 755)

```bash
#!/usr/bin/env bash
# voice-check SessionStart healer.
# Repairs this repo's installed pre-commit hook when the engine path baked
# into it stopped resolving (a plugin upgrade moved the cache directory).
# Exits 0 in every case; a session must never break because of this hook.

set -u

MARKER="# === voice-check section start ==="

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0
# The installer only supports normal checkouts (.git directory).
[ -d "$REPO_ROOT/.git" ] || exit 0

HOOK="$REPO_ROOT/.git/hooks/pre-commit"
[ -f "$HOOK" ] || exit 0
grep -qF "$MARKER" "$HOOK" || exit 0

# Old installs bake VOICE_CHECK_ENGINE=; the self-healing template bakes
# BAKED_ENGINE=. Either way, a live path means nothing to heal.
BAKED=$(sed -n 's/^BAKED_ENGINE="\(.*\)"$/\1/p; s/^VOICE_CHECK_ENGINE="\(.*\)"$/\1/p' "$HOOK" | head -1)
[ -n "$BAKED" ] || exit 0
[ -f "$BAKED" ] && exit 0

INSTALLER="${CLAUDE_PLUGIN_ROOT:-}/templates/install-hook.sh"
[ -f "$INSTALLER" ] || exit 0

if bash "$INSTALLER" "$REPO_ROOT" >/dev/null 2>&1; then
  echo "voice-check: healed stale pre-commit hook in $REPO_ROOT"
fi
exit 0
```

- [ ] **Step 4: Create `hooks/hooks.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/heal-hook.sh\"",
            "shell": "bash",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS (52 = 48 plus 4 new).

- [ ] **Step 6: Commit**

```bash
git add hooks/hooks.json hooks/heal-hook.sh tests/test_engine.py
git commit -m "feat(hooks): SessionStart healer repairs stale pre-commit hooks automatically

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Installer comment, docs, version bump

**Files:**
- Modify: `plugins/voice-check/templates/install-hook.sh` (header comment only, lines 2 through 5)
- Modify: `CLAUDE.md` (hook installation flow paragraph, around line 23)
- Modify: `README.md` (around lines 75 and 153, locate by content)
- Modify: `plugins/voice-check/.claude-plugin/plugin.json` (version)

**Interfaces:**
- Consumes: behavior shipped by Tasks 1 and 2.

- [ ] **Step 1: Update the installer header comment**

Replace lines 2 through 5 of `templates/install-hook.sh`:

```bash
# Install the voice-check pre-commit hook into a git repo.
# Resolves the absolute path to the voice-check engine in the plugin cache
# at install time and embeds it into the per-repo hook. Re-run after
# upgrading the voice-check plugin so the hook picks up the new version path.
```

with:

```bash
# Install the voice-check pre-commit hook into a git repo.
# Resolves the absolute path to the voice-check engine in the plugin cache
# at install time and embeds it as the hook's fast path. Installed hooks
# self-heal: they re-resolve the engine at commit time after upgrades, and
# the plugin's SessionStart healer rewrites stale pre-2.2.1 hook sections.
# Re-running this installer is always safe (idempotent) but no longer
# required after upgrades.
```

- [ ] **Step 2: Update CLAUDE.md**

In the "Hook installation flow" section, replace the sentence:

```
After upgrading the plugin, users must re-run `install-hook.sh` in each repo because the cached engine path changes.
```

with:

```
Installed hooks self-heal across upgrades: the hook re-resolves the engine from the newest plugin cache version at commit time, and the plugin's SessionStart hook (`hooks/heal-hook.sh`, registered in `hooks/hooks.json`) rewrites stale pre-2.2.1 hook sections the first time a Claude Code session starts in that repo. Re-running `install-hook.sh` stays harmless but is no longer needed.
```

- [ ] **Step 3: Update README.md**

Replace the sentence at the line reading:

```
If you have the pre-commit hook installed in any repo, re-run `install-hook.sh` after each upgrade so the hook picks up the new engine path:
```

(and delete the code block immediately following it, if that block only shows the re-run command) with:

```
Installed hooks self-heal after upgrades: the hook re-resolves the engine from the plugin cache at commit time, and a SessionStart healer repairs hooks installed by versions before 2.2.1 the first time you start a Claude Code session in that repo. Repos where you never open Claude Code keep the old advisory nag until you run `install-hook.sh` there once.
```

Replace the other sentence:

```
If you have the pre-commit hook installed in any repos, re-run `install-hook.sh` from the new plugin location to update the embedded engine path.
```

with:

```
Hooks installed by 2.2.1 or later need nothing after upgrades; older hooks are repaired automatically the first time a Claude Code session starts in that repo.
```

- [ ] **Step 4: Bump the version**

In `plugins/voice-check/.claude-plugin/plugin.json` change `"version": "2.2.0"` to `"version": "2.2.1"`.

- [ ] **Step 5: Run the full suite and the engine on changed docs**

```bash
.venv/bin/python -m pytest tests/test_engine.py -q
python3 engine/voice_check.py --report-only ../../README.md
python3 engine/voice_check.py --report-only ../../CLAUDE.md
```

Expected: 52 passed; no dash findings on either doc (other advisory findings on pre-existing text are acceptable, but the sentences added here must be clean).

- [ ] **Step 6: Commit**

```bash
git add templates/install-hook.sh ../../CLAUDE.md ../../README.md .claude-plugin/plugin.json
git commit -m "docs: describe hook self-healing, bump version to 2.2.1

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Post-implementation (manual, not a task)

Real-world smoke test in this checkout: run `bash plugins/voice-check/hooks/heal-hook.sh` with `CLAUDE_PLUGIN_ROOT=plugins/voice-check` from the repo root. This repo has no voice-check pre-commit section, so it must exit 0 silently without touching `.git/hooks/`.
