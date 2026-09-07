"""End-to-end tests for the voice-check pre-commit hook pipeline.

Covers criterion 7: install-hook.sh renders the template correctly, is
idempotent, and the installed hook produces findings on dirty staged files
while exiting 0 (advisory).

These tests exercise the real `templates/install-hook.sh` and
`templates/pre-commit.sh` in the repo. They never touch the real `.git/`
directory of the checkout. All work happens in pytest `tmp_path`.

Stdlib only.
"""
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
INSTALL_HOOK = TEMPLATES_DIR / "install-hook.sh"
PRE_COMMIT_TEMPLATE = TEMPLATES_DIR / "pre-commit.sh"
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
