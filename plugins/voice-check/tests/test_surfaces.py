"""Tests for the surface concept: which rules run on which kind of text.

A commit message cannot carry a `<!-- voice-check: ignore -->` comment, and
once written it is in history. The commit surface therefore runs an
allowlist rather than everything, and these tests pin that allowlist.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import analyzers  # noqa: E402
import config  # noqa: E402
import document  # noqa: E402
import rules  # noqa: E402
import scanner  # noqa: E402
import voice_check  # noqa: E402

ENGINE = Path(__file__).parent.parent / "engine" / "voice_check.py"


def _scan(text, surface="file", rel_path="a.md"):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, config.Config.empty(), rel_path, None, surface)


# ---------------------------------------------------------------------------
# The allowlist pin
# ---------------------------------------------------------------------------

def test_commit_surface_is_pinned_exactly():
    """Adding a rule family without deciding about commit messages must fail
    here rather than start nagging on every commit in the field."""
    assert rules.COMMIT_SURFACE == frozenset({"no_dashes", "markup_artifacts"})


def test_every_commit_surface_name_is_a_real_rule_name():
    known = ({r["name"] for r in rules.RULES}
             | {a["name"] for a in analyzers.ANALYZERS})
    assert rules.COMMIT_SURFACE <= known


# ---------------------------------------------------------------------------
# The allowlist actually restricts
# ---------------------------------------------------------------------------

def test_commit_surface_keeps_dashes_and_drops_everything_else():
    """This single test pins the whole feature. Without it the surface filter
    could be a no op and nothing else would notice."""
    text = "Fix the thing - properly\n\nThis is a groundbreaking change.\n"

    on_files = {f["rule"] for f in _scan(text, surface="file")}
    assert on_files == {"no_dashes", "puffery", "promotional_tone"}

    on_commits = {f["rule"] for f in _scan(text, surface="commit")}
    assert on_commits == {"no_dashes"}


def test_commit_surface_reports_leaked_tokens():
    text = "Add the docs\n\nSee contentReference for details.\n"
    assert {f["rule"] for f in _scan(text, surface="commit")} == {"markup_artifacts"}


def test_file_surface_is_the_default_and_unchanged():
    text = "This is a groundbreaking change.\n"
    doc = document.Document.from_markdown(text)
    without = scanner.scan(doc, config.Config.empty(), "a.md")
    with_default = _scan(text, surface="file")
    assert {f["rule"] for f in without} == {f["rule"] for f in with_default}
    assert "puffery" in {f["rule"] for f in without}


def test_supplement_rules_never_reach_commit_messages():
    """A repo's custom word cannot be suppressed in a commit message any more
    than a built in can, so it does not run there."""
    cfg = config.Config.empty()
    cfg.extra_rows.append({
        "name": "supplement:word", "id": "supplement.word.synergy",
        "category": "supplement", "kind": "word", "pattern": "synergy",
        "message": "Supplement rule (word): 'synergy'.",
        "scope": "line", "severity": "medium",
    })
    doc = document.Document.from_markdown("We need more synergy here.\n")

    on_files = scanner.scan(doc, cfg, "a.md", None, "file")
    assert {f["rule"] for f in on_files} == {"supplement:word"}

    on_commits = scanner.scan(doc, cfg, "a.md", None, "commit")
    assert on_commits == []


# ---------------------------------------------------------------------------
# Analyzers obey the surface too
# ---------------------------------------------------------------------------

def test_embedded_token_analyzer_runs_on_commit_messages():
    text = "Add link\n\nSee https://example.com/a?utm_source=chatgpt.com now.\n"
    hits = {f["rule_id"] for f in _scan(text, surface="commit")}
    assert "markup_artifacts.embedded_tokens" in hits


def test_bold_header_analyzer_never_runs_on_commit_messages():
    """structure ships off by default, so enable it and confirm the surface
    filter still keeps it away from commit messages."""
    cfg = config.Config.empty()
    cfg.enabled.append(("structure.bold_headers", None))
    text = (
        "Summary\n\n"
        "- **One**: first thing\n"
        "- **Two**: second thing\n"
        "- **Three**: third thing\n"
        "- **Four**: fourth thing\n"
    )
    doc = document.Document.from_markdown(text)

    on_files = scanner.scan(doc, cfg, "a.md", None, "file")
    assert "structure.bold_headers" in {f["rule_id"] for f in on_files}

    on_commits = scanner.scan(doc, cfg, "a.md", None, "commit")
    assert "structure.bold_headers" not in {f["rule_id"] for f in on_commits}


# ---------------------------------------------------------------------------
# The CLI flag
# ---------------------------------------------------------------------------

def test_voice_check_scan_takes_a_surface(tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Fix the thing - properly\n\nA groundbreaking change.\n")
    assert {x["rule"] for x in voice_check.scan(f, surface="commit")} == {"no_dashes"}


def test_cli_surface_commit_reports_only_allowlisted_rules(tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Fix the thing - properly\n\nA groundbreaking change.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--min-severity", "low",
         "--surface", "commit", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "no_dashes" in r.stdout
    assert "puffery" not in r.stdout


def test_cli_defaults_to_the_file_surface(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("A groundbreaking change.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--min-severity", "low", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "puffery" in r.stdout


def test_cli_rejects_an_unknown_surface(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("Anything.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--surface", "email", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 2
