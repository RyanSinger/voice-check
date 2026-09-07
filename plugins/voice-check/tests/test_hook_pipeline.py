"""End-to-end tests for the voice-check pre-commit hook pipeline.

Covers criterion 7: install-hook.sh renders the template correctly, is
idempotent, and the installed hook produces findings on dirty staged files
while exiting 0 (advisory).

These tests exercise the real `templates/install-hook.sh` and
`templates/pre-commit.sh` in the repo. They never touch the real `.git/`
directory of the checkout. All work happens in pytest `tmp_path`.

Stdlib only.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
INSTALL_HOOK = TEMPLATES_DIR / "install-hook.sh"
PRE_COMMIT_TEMPLATE = TEMPLATES_DIR / "pre-commit.sh"
HEALER_SCRIPT = PLUGIN_ROOT / "hooks" / "heal-hook.sh"
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
ENGINE_FILE = PLUGIN_ROOT / "engine" / "voice_check.py"

MARKER_START = "# === voice-check section start ==="
MARKER_END = "# === voice-check section end ==="


def _git_env(fake_home: Path = None):
    """Return an env dict with git identity set so commits never fail.

    If fake_home is given, HOME is overridden. This is used when invoking
    install-hook.sh so its plugin-cache and legacy-clone fallbacks (which
    read $HOME) always miss, forcing the installer to use the in-repo
    engine via its walk-up-from-template fallback. That makes the test
    deterministic regardless of what the developer has cached locally.
    """
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    if fake_home is not None:
        env["HOME"] = str(fake_home)
    return env


def _init_repo(path: Path) -> None:
    """Initialize a fresh git repo at path."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", str(path)],
        check=True,
        env=_git_env(),
    )


def _run_installer(repo: Path, fake_home: Path) -> subprocess.CompletedProcess:
    """Run the real install-hook.sh against repo with an isolated HOME."""
    return subprocess.run(
        ["bash", str(INSTALL_HOOK), str(repo)],
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(fake_home=fake_home),
    )


def _hook_path(repo: Path) -> Path:
    return repo / ".git" / "hooks" / "pre-commit"


@pytest.fixture
def fresh_repo(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    return repo


@pytest.fixture
def fake_home(tmp_path):
    """An empty HOME so the installer's HOME-based fallbacks all miss and it
    falls through to the in-repo engine via template walk-up."""
    h = tmp_path / "home"
    h.mkdir()
    return h


# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------

def test_preconditions_installer_and_engine_present():
    """Sanity: real files used by the rest of this module actually exist."""
    assert INSTALL_HOOK.is_file(), f"missing installer: {INSTALL_HOOK}"
    assert PRE_COMMIT_TEMPLATE.is_file(), f"missing template: {PRE_COMMIT_TEMPLATE}"
    assert ENGINE_FILE.is_file(), f"missing engine: {ENGINE_FILE}"


# ---------------------------------------------------------------------------
# Install layer
# ---------------------------------------------------------------------------

def test_install_hook_renders_engine_path(fresh_repo, fake_home):
    """After running install-hook.sh in a fresh tmp repo:
    - .git/hooks/pre-commit exists and is executable
    - contains both marker lines
    - the __VOICE_CHECK_ENGINE__ placeholder is replaced with a real abs path
    """
    _run_installer(fresh_repo, fake_home)

    hook = _hook_path(fresh_repo)
    assert hook.is_file(), "pre-commit hook not installed"

    # Executable bit set
    mode = hook.stat().st_mode
    assert mode & stat.S_IXUSR, "pre-commit hook is not executable"

    content = hook.read_text()
    assert MARKER_START in content
    assert MARKER_END in content

    # Placeholder must be fully substituted
    assert "__VOICE_CHECK_ENGINE__" not in content, (
        "installer did not substitute engine placeholder"
    )

    # With HOME faked out, fallback 3 (walk-up from template dir) must have
    # resolved to the in-repo engine file.
    # Extract the resolved engine path from the rendered BAKED_ENGINE="..." line
    engine_line = next(
        (ln for ln in content.splitlines() if ln.startswith("BAKED_ENGINE=")),
        None,
    )
    assert engine_line is not None, "rendered hook missing BAKED_ENGINE line"
    # Strip BAKED_ENGINE=" ... "
    rendered_engine = engine_line.split("=", 1)[1].strip().strip('"')
    assert rendered_engine, "rendered engine path is empty"
    assert Path(rendered_engine).is_absolute(), (
        f"rendered engine path not absolute: {rendered_engine}"
    )
    assert Path(rendered_engine).is_file(), (
        f"rendered engine path does not exist on disk: {rendered_engine}"
    )
    assert rendered_engine.endswith("voice_check.py")
    assert Path(rendered_engine).resolve() == ENGINE_FILE.resolve(), (
        f"expected in-repo engine, got {rendered_engine}"
    )


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------

def test_install_hook_is_idempotent(fresh_repo, fake_home):
    """Running the installer twice must not duplicate the voice-check section."""
    _run_installer(fresh_repo, fake_home)
    _run_installer(fresh_repo, fake_home)

    content = _hook_path(fresh_repo).read_text()
    assert content.count(MARKER_START) == 1, (
        f"duplicate marker start after second install:\n{content}"
    )
    assert content.count(MARKER_END) == 1, (
        f"duplicate marker end after second install:\n{content}"
    )


# ---------------------------------------------------------------------------
# Runtime layer
# ---------------------------------------------------------------------------

def _stage_file(repo: Path, rel: str, text: str) -> None:
    f = repo / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    subprocess.run(
        ["git", "-C", str(repo), "add", rel],
        check=True,
        env=_git_env(),
    )


def _run_hook(repo: Path) -> subprocess.CompletedProcess:
    hook = _hook_path(repo)
    env = _git_env()
    # Ensure the hook's python3 invocation uses the same interpreter pytest
    # is running under, which we know has stdlib available.
    env["VOICE_CHECK_PYTHON"] = sys.executable
    return subprocess.run(
        ["bash", str(hook)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=env,
    )


def test_hook_runtime_reports_findings_on_dirty_file(fresh_repo, fake_home):
    """With a dirty staged markdown file the hook exits 0 and prints at least
    one engine rule name."""
    _run_installer(fresh_repo, fake_home)

    # "groundbreaking" is a puffery word. " - " is a hyphen separator.
    # Both are deterministic line-scope rules from rules.py.
    dirty = (
        "# Notes\n"
        "\n"
        "This groundbreaking release ships today.\n"
        "Pages 10 - 15 cover the details.\n"
    )
    _stage_file(fresh_repo, "dirty.md", dirty)

    result = _run_hook(fresh_repo)

    assert result.returncode == 0, (
        f"hook exited non-zero: {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    combined = result.stdout + result.stderr
    assert "voice-check: scanning" in combined, (
        f"hook did not announce scan:\n{combined}"
    )
    # Per-file header must appear
    assert "--- dirty.md ---" in combined, (
        f"hook did not print per-file header:\n{combined}"
    )
    # At least one real rule name from rules.py must appear in findings output.
    # format_findings prints lines like "  [no_dashes] line 4: ..."
    assert ("[no_dashes]" in combined) or ("[puffery]" in combined), (
        f"hook did not print any rule name in findings:\n{combined}"
    )
    # Advisory footer
    assert "advisory only" in combined


def test_hook_runtime_silent_on_clean_file(fresh_repo, fake_home):
    """With only a clean staged markdown file the hook exits 0 and prints no
    per-file findings header."""
    _run_installer(fresh_repo, fake_home)

    clean = (
        "# Notes\n"
        "\n"
        "The plan is simple. Ship the MVP. Iterate based on real usage.\n"
    )
    _stage_file(fresh_repo, "clean.md", clean)

    result = _run_hook(fresh_repo)

    assert result.returncode == 0, (
        f"hook exited non-zero on clean file: {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    combined = result.stdout + result.stderr
    # Scan banner is expected (1 file staged)
    assert "voice-check: scanning" in combined
    # No per-file finding header, no advisory footer
    assert "--- clean.md ---" not in combined, (
        f"clean file should not produce findings header:\n{combined}"
    )
    assert "advisory only" not in combined, (
        f"clean file should not trigger advisory footer:\n{combined}"
    )


# ---------------------------------------------------------------------------
# Diff scoping
# ---------------------------------------------------------------------------

def test_hook_reports_only_on_changed_lines(fresh_repo, fake_home):
    """A pre-existing violation elsewhere in the file must stay quiet."""
    _run_installer(fresh_repo, fake_home)

    _stage_file(fresh_repo, "doc.md", "old line with an em dash — here\nsecond line\n")
    subprocess.run(
        ["git", "-C", str(fresh_repo), "commit", "-q", "-m", "seed", "--no-verify"],
        check=True,
        env=_git_env(),
    )

    # Touch only the second line, introducing a fresh violation there.
    _stage_file(
        fresh_repo,
        "doc.md",
        "old line with an em dash — here\nsecond line — changed\n",
    )

    out = _run_hook(fresh_repo)
    assert out.returncode == 0, "hook must never block a commit"
    combined = out.stdout + out.stderr
    assert "line 2" in combined
    assert "line 1" not in combined


def test_hook_still_exits_zero_on_a_clean_staged_file(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "doc.md", "clean prose here\n")
    out = _run_hook(fresh_repo)
    assert out.returncode == 0


# ---------------------------------------------------------------------------
# Working tree vs. index divergence
# ---------------------------------------------------------------------------

def test_hook_falls_back_to_whole_file_scan_when_working_tree_differs_from_index(
    fresh_repo, fake_home
):
    """Diff ranges describe the STAGED (index) blob's line numbers. If the
    working tree copy has since drifted from what is staged, for example
    more edits after `git add -p`, those line numbers no longer point at
    the right lines in the file the engine actually reads from disk. The
    hook must fall back to a whole file scan rather than report findings
    against the wrong lines."""
    _run_installer(fresh_repo, fake_home)

    _stage_file(fresh_repo, "doc.md", "line one\nline two\n")
    subprocess.run(
        ["git", "-C", str(fresh_repo), "commit", "-q", "-m", "seed", "--no-verify"],
        check=True,
        env=_git_env(),
    )

    # Stage a change to line 2 only.
    _stage_file(fresh_repo, "doc.md", "line one\nsecond line changed — here\n")
    # Then edit the working tree further without staging, introducing a
    # violation on line 1 that the staged diff knows nothing about.
    (fresh_repo / "doc.md").write_text(
        "first line groundbreaking\nsecond line changed — here\n"
    )

    out = _run_hook(fresh_repo)
    assert out.returncode == 0
    combined = out.stdout + out.stderr
    assert "puffery" in combined
    assert "no_dashes" in combined


# ---------------------------------------------------------------------------
# git unavailable fallback (spec Testing section)
# ---------------------------------------------------------------------------

def test_hook_falls_back_to_whole_file_scan_when_diff_cached_fails(fresh_repo, fake_home):
    """When `git diff --cached -U0` cannot succeed, the hook must still
    exit 0 and still produce findings, falling back to a whole file scan.
    A `git` wrapper earlier on PATH fails only calls carrying `-U0`, so the
    initial `git diff --cached --name-only` staged file listing still
    succeeds and the file still gets scanned."""
    _run_installer(fresh_repo, fake_home)

    _stage_file(fresh_repo, "dirty.md", "This groundbreaking release ships today.\n")

    real_git = shutil.which("git")
    assert real_git, "git must be on PATH to run this test"

    fake_bin = fresh_repo.parent / "fakebin"
    fake_bin.mkdir(exist_ok=True)
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'for a in "$@"; do\n'
        '  if [ "$a" = "-U0" ]; then\n'
        "    echo 'fatal: simulated git diff failure' >&2\n"
        "    exit 128\n"
        "  fi\n"
        "done\n"
        f'exec "{real_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        ["bash", str(_hook_path(fresh_repo))],
        cwd=str(fresh_repo),
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "--- dirty.md ---" in combined
    assert "puffery" in combined


# ---------------------------------------------------------------------------
# Hook version stamp: the healer reinstalls a stale hook body even when its
# baked engine path is still live
# ---------------------------------------------------------------------------

def _plugin_version():
    return json.loads(PLUGIN_JSON.read_text())["version"]


def _run_healer(cwd, home):
    return subprocess.run(
        ["bash", str(HEALER_SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home), "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)},
    )


def _hook_with_stamp(engine, version):
    return (
        "#!/usr/bin/env bash\n"
        "# === voice-check section start ===\n"
        f"# voice-check hook version: {version}\n"
        f'BAKED_ENGINE="{engine}"\n'
        'if [ ! -f "$BAKED_ENGINE" ]; then\n'
        '  echo "voice-check: engine not found at $BAKED_ENGINE"\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
        "# === voice-check section end ===\n"
    )


def _install_hook_text(repo, text):
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text(text)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return hook


def test_healer_reinstalls_when_version_stamp_is_stale(tmp_path):
    """A hook whose baked engine path is still live but whose version stamp
    is older than the plugin's own version must still be reinstalled, so a
    hook body change (like the diff scoping added in this release) is not
    held hostage to the engine path ever going dead."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())

    live_engine = ENGINE_FILE
    _install_hook_text(repo, _hook_with_stamp(live_engine, "0.0.1"))

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout

    text = (repo / ".git" / "hooks" / "pre-commit").read_text()
    assert f"# voice-check hook version: {_plugin_version()}" in text


def test_healer_noop_when_version_stamp_is_current(tmp_path):
    """A hook whose stamp already matches the plugin's version, and whose
    engine path is live, must be left untouched."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())

    live_engine = ENGINE_FILE
    hook = _install_hook_text(repo, _hook_with_stamp(live_engine, _plugin_version()))
    before = hook.read_bytes()

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert hook.read_bytes() == before


# ---------------------------------------------------------------------------
# The commit-msg hook template
# ---------------------------------------------------------------------------

COMMIT_MSG_TEMPLATE = TEMPLATES_DIR / "commit-msg.sh"


def _run_commit_msg_template(repo: Path, message: str) -> subprocess.CompletedProcess:
    """Run the raw (unrendered) commit-msg template against a message file.

    The template's placeholder is not substituted here. resolve_engine's
    first branch reads $VOICE_CHECK_ENGINE, so pointing that at the in-repo
    engine exercises the real template without an install step.
    """
    msg_file = repo / ".git" / "COMMIT_EDITMSG"
    msg_file.parent.mkdir(parents=True, exist_ok=True)
    msg_file.write_text(message)

    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    env["VOICE_CHECK_ENGINE"] = str(ENGINE_FILE)
    return subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE), str(msg_file)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=env,
    )


def test_commit_msg_template_exists_with_markers_and_placeholder():
    assert COMMIT_MSG_TEMPLATE.is_file(), f"missing template: {COMMIT_MSG_TEMPLATE}"
    text = COMMIT_MSG_TEMPLATE.read_text()
    assert MARKER_START in text
    assert MARKER_END in text
    assert "__VOICE_CHECK_ENGINE__" in text
    assert "# voice-check hook version: " in text


def test_commit_msg_reports_an_em_dash(fresh_repo):
    r = _run_commit_msg_template(fresh_repo, "Fix the parser — nested quotes\n")
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" in combined


def test_commit_msg_stays_silent_on_a_clean_message(fresh_repo):
    r = _run_commit_msg_template(
        fresh_repo,
        "fix(engine): thread surface through the scanner\n"
        "\n"
        "Commit messages now run a restricted rule set.\n",
    )
    assert r.returncode == 0
    assert (r.stdout + r.stderr).strip() == ""


def test_commit_msg_applies_the_allowlist(fresh_repo):
    """Puffery is not on the commit allowlist; a dash is."""
    r = _run_commit_msg_template(
        fresh_repo, "Fix the thing - properly\n\nA groundbreaking change.\n")
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" in combined
    assert "puffery" not in combined


def test_commit_msg_ignores_git_comments_and_the_verbose_diff(fresh_repo):
    """The case most likely to catch a real bug.

    git stripspace --strip-comments removes the scissors line but leaves the
    diff beneath it, so the hook must cut at the scissors marker first.
    Without that cut this message reports an em dash from someone else's code.
    """
    message = (
        "Real message here\n"
        "\n"
        "# Please enter the commit message for your changes.\n"
        "# ------------------------ >8 ------------------------\n"
        "# Do not modify or remove the line above.\n"
        "diff --git a/x.md b/x.md\n"
        "+a line with an em dash — here\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" not in combined, (
        f"verbose diff was scanned:\n{combined}")


def test_commit_msg_keeps_the_body_when_there_is_no_scissors_line(fresh_repo):
    message = (
        "Subject line\n"
        "\n"
        "Body with an em dash — in it.\n"
        "\n"
        "# Please enter the commit message for your changes.\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    assert "no_dashes" in (r.stdout + r.stderr)


def test_commit_msg_is_silent_on_an_aborted_empty_message(fresh_repo):
    message = (
        "\n"
        "# Please enter the commit message for your changes.\n"
        "# Aborting commit due to empty commit message.\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    assert (r.stdout + r.stderr).strip() == ""


def test_commit_msg_leaves_no_scratch_files_behind(fresh_repo):
    _run_commit_msg_template(fresh_repo, "Fix the parser — nested quotes\n")
    root_leftovers = sorted(p.name for p in fresh_repo.glob(".voice-check-*"))
    git_dir_leftovers = sorted(p.name for p in (fresh_repo / ".git").glob("voice-check-*"))
    assert root_leftovers == [], f"scratch files left behind at repo root: {root_leftovers}"
    assert git_dir_leftovers == [], f"scratch files left behind in .git: {git_dir_leftovers}"


def test_commit_msg_uses_the_linked_worktree_own_config_not_the_main_repo(
        fresh_repo, tmp_path):
    """Pins the worktree defect.

    git rev-parse --git-common-dir resolves to the MAIN repository's .git in
    a linked worktree, so a scratch file placed there walks up to the main
    checkout and picks up its .claude/voice-check.md instead of the linked
    worktree's own (absent) supplement. pre-commit.sh scanning a real file in
    the same worktree would never make that mistake, so the commit-msg hook
    must not either. The main repo disables no_dashes here; the worktree has
    no supplement of its own, so an em dash committed from the worktree must
    still be reported.
    """
    (fresh_repo / "README.md").write_text("seed\n")

    env = _git_env()
    subprocess.run(["git", "-C", str(fresh_repo), "add", "."], check=True, env=env)
    subprocess.run(
        ["git", "-C", str(fresh_repo), "commit", "-q", "-m", "seed"],
        check=True, env=env,
    )

    # Written after the commit, and never staged, so a checkout of that
    # commit (the linked worktree below) does not carry a copy of its own.
    claude_dir = fresh_repo / ".claude"
    claude_dir.mkdir()
    (claude_dir / "voice-check.md").write_text(
        "```voice-check-disable\nno_dashes\n```\n"
    )

    worktree = tmp_path / "linked-worktree"
    subprocess.run(
        ["git", "-C", str(fresh_repo), "worktree", "add", str(worktree), "-b", "wt-branch"],
        check=True, env=env, capture_output=True, text=True,
    )

    msg_file = tmp_path / "commit-editmsg"
    msg_file.write_text("Fix the parser — nested quotes\n")

    run_env = _git_env()
    run_env["VOICE_CHECK_PYTHON"] = sys.executable
    run_env["VOICE_CHECK_ENGINE"] = str(ENGINE_FILE)
    r = subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE), str(msg_file)],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        env=run_env,
    )
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" in combined, (
        "the linked worktree picked up the main repo's disable instead of "
        f"its own (absent) supplement:\n{combined}")


def test_commit_msg_exits_zero_when_the_engine_is_missing(fresh_repo):
    msg_file = fresh_repo / ".git" / "COMMIT_EDITMSG"
    msg_file.parent.mkdir(parents=True, exist_ok=True)
    msg_file.write_text("Fix the parser — nested quotes\n")

    env = _git_env()
    env["HOME"] = str(fresh_repo / "empty-home")
    env["VOICE_CHECK_ENGINE"] = str(fresh_repo / "nope" / "voice_check.py")
    r = subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE), str(msg_file)],
        cwd=str(fresh_repo), capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0


def test_commit_msg_exits_zero_when_given_no_argument(fresh_repo):
    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    env["VOICE_CHECK_ENGINE"] = str(ENGINE_FILE)
    r = subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE)],
        cwd=str(fresh_repo), capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# The installer and healer cover both hooks
# ---------------------------------------------------------------------------

def _commit_msg_hook_path(repo: Path) -> Path:
    return repo / ".git" / "hooks" / "commit-msg"


def test_installer_installs_both_hooks(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)

    for hook in (_hook_path(fresh_repo), _commit_msg_hook_path(fresh_repo)):
        assert hook.is_file(), f"not installed: {hook}"
        assert hook.stat().st_mode & stat.S_IXUSR, f"not executable: {hook}"
        text = hook.read_text()
        assert MARKER_START in text
        assert MARKER_END in text
        assert "__VOICE_CHECK_ENGINE__" not in text, f"placeholder left in {hook}"
        engine_line = next(
            (ln for ln in text.splitlines() if ln.startswith("BAKED_ENGINE=")), None)
        assert engine_line is not None, f"no BAKED_ENGINE line in {hook}"
        baked = engine_line.split("=", 1)[1].strip().strip('"')
        assert Path(baked).resolve() == ENGINE_FILE.resolve()


def test_installer_is_idempotent_for_both_hooks(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    _run_installer(fresh_repo, fake_home)

    for hook in (_hook_path(fresh_repo), _commit_msg_hook_path(fresh_repo)):
        text = hook.read_text()
        assert text.count(MARKER_START) == 1, f"duplicate section in {hook}"
        assert text.count(MARKER_END) == 1, f"duplicate section in {hook}"


def test_installer_preserves_a_foreign_commit_msg_hook(fresh_repo, fake_home):
    """A user's own commit-msg hook must survive, with our section appended."""
    hooks_dir = fresh_repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    foreign = hooks_dir / "commit-msg"
    foreign.write_text("#!/usr/bin/env bash\necho 'my own hook'\n")
    foreign.chmod(foreign.stat().st_mode | stat.S_IXUSR)

    _run_installer(fresh_repo, fake_home)

    text = foreign.read_text()
    assert "echo 'my own hook'" in text, "foreign commit-msg hook was clobbered"
    assert MARKER_START in text
    assert text.count(MARKER_START) == 1


def test_installed_commit_msg_hook_runs_end_to_end(fresh_repo, fake_home):
    """A real commit with a dashed message reports and still succeeds."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "notes.md", "All clean here.\n")

    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    r = subprocess.run(
        ["git", "-C", str(fresh_repo), "commit",
         "-m", "Fix the parser — nested quotes"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, f"commit blocked:\n{r.stdout}\n{r.stderr}"
    assert "no_dashes" in (r.stdout + r.stderr)

    log = subprocess.run(
        ["git", "-C", str(fresh_repo), "log", "--oneline"],
        capture_output=True, text=True, env=env)
    assert "Fix the parser" in log.stdout, "commit did not land"


def test_healer_reinstalls_both_hooks_when_pre_commit_is_stale(tmp_path):
    """A repo installed before this release has a stale pre-commit and no
    commit-msg hook at all. One heal must produce both, current."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, "0.0.1"))
    assert not (repo / ".git" / "hooks" / "commit-msg").exists()

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout

    version = _plugin_version()
    for name in ("pre-commit", "commit-msg"):
        text = (repo / ".git" / "hooks" / name).read_text()
        assert f"# voice-check hook version: {version}" in text, f"{name} not current"


def test_healer_reinstalls_when_only_the_commit_msg_hook_is_stale(tmp_path):
    """A half healed install, pre-commit current and commit-msg stale, is
    worse than an unhealed one because nothing surfaces the mismatch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    version = _plugin_version()
    _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, version))

    hooks_dir = repo / ".git" / "hooks"
    stale = hooks_dir / "commit-msg"
    stale.write_text(_hook_with_stamp(ENGINE_FILE, "0.0.1"))
    stale.chmod(stale.stat().st_mode | stat.S_IXUSR)

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    assert f"# voice-check hook version: {version}" in stale.read_text()


def test_healer_noop_when_both_hooks_are_current(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    version = _plugin_version()
    pre = _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, version))
    msg = repo / ".git" / "hooks" / "commit-msg"
    msg.write_text(_hook_with_stamp(ENGINE_FILE, version))
    msg.chmod(msg.stat().st_mode | stat.S_IXUSR)

    before = (pre.read_bytes(), msg.read_bytes())
    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert (pre.read_bytes(), msg.read_bytes()) == before


def test_healer_does_not_install_into_a_repo_that_never_opted_in(tmp_path):
    """No voice-check marker anywhere means this repo never asked for hooks."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n")

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert not (hooks_dir / "commit-msg").exists()


# ---------------------------------------------------------------------------
# The widened file surface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", ["notes.txt", "guide.rst", "readme.markdown"])
def test_pre_commit_scans_the_widened_extensions(fresh_repo, fake_home, rel):
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, rel, "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert f"--- {rel} ---" in combined, f"{rel} was not scanned:\n{combined}"
    assert "no_dashes" in combined


def test_pre_commit_still_scans_markdown(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "notes.md", "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    assert "--- notes.md ---" in (r.stdout + r.stderr)


def test_pre_commit_does_not_scan_source_files(fresh_repo, fake_home):
    """Docstring extraction is a separate phase. A .py file stays out."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "mod.py", '"""The plan is simple — ship it."""\n')

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "mod.py" not in combined, f".py file was scanned:\n{combined}"
    assert "no_dashes" not in combined


def test_pre_commit_does_not_match_an_extension_mid_name(fresh_repo, fake_home):
    """`.txt` in the middle of a name is not a text file."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "archive.txt.gz", "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    assert "archive.txt.gz" not in (r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# Version stamps
# ---------------------------------------------------------------------------

def test_every_hook_template_stamps_the_current_plugin_version():
    """The healer compares each hook's stamp against plugin.json. A template
    left at an older stamp means that hook heals on every session start
    forever; a template ahead of plugin.json means it never heals at all."""
    version = _plugin_version()
    for template in (PRE_COMMIT_TEMPLATE, COMMIT_MSG_TEMPLATE):
        text = template.read_text()
        assert f"# voice-check hook version: {version}" in text, (
            f"{template.name} is not stamped {version}")
