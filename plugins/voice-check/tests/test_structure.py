"""Tests for the structural frame rules.

Frames match sentence shapes rather than words, so they fire on legitimate
prose more readily than a vocabulary rule does. The negative cases matter
more than the positives here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402
import document  # noqa: E402
import scanner  # noqa: E402


def _ids(text):
    doc = document.Document.from_markdown(text)
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    return {f["rule_id"] for f in findings}


def test_negative_parallelism_fires():
    assert "structure.not_just_but" in _ids(
        "Our platform is not just a tool, it is a partner.\n"
    )


def test_not_only_but_also_fires():
    """"Not only X but Y" is the same construction and should fire."""
    assert "structure.not_just_but" in _ids("He was not only tired but hungry.\n")


def test_plain_not_just_stays_silent():
    assert "structure.not_just_but" not in _ids(
        "I could not just sit there and watch.\n"
    )


def test_contrast_reframe_fires():
    assert "structure.not_about_but_about" in _ids(
        "It's not about the tooling, it's about the culture.\n"
    )


def test_single_negation_stays_silent():
    assert "structure.not_about_but_about" not in _ids("It's not about money.\n")


def test_balanced_debate_concessive_fires():
    assert "structure.while_also" in _ids(
        "While the approach has merit, it also carries risk.\n"
    )


def test_ordinary_while_clause_stays_silent():
    assert "structure.while_also" not in _ids(
        "While the tests ran, we reviewed the diff.\n"
    )


def test_advantages_disadvantages_fires():
    assert "structure.advantages_disadvantages" in _ids(
        "The framework has clear advantages and some disadvantages.\n"
    )


def test_benefits_alone_stays_silent():
    assert "structure.advantages_disadvantages" not in _ids(
        "The benefits are clear and worth the effort.\n"
    )


def test_challenges_and_prospects_fires():
    assert "structure.despite_faces_challenges" in _ids(
        "Despite its strong adoption, the framework faces challenges ahead.\n"
    )


def test_ordinary_concessive_stays_silent():
    """Requires all three beats, so a plain "despite" sentence is quiet."""
    assert "structure.despite_faces_challenges" not in _ids(
        "Despite budget challenges, we shipped on time.\n"
    )


def test_false_range_fires_on_plural_to_plural():
    assert "structure.false_range" in _ids(
        "We serve everyone from startups to enterprises.\n"
    )


def test_ordinary_ranges_stay_silent():
    """"From X to Y" is ordinary English. Only plural to plural fires."""
    for text in (
        "We work from 9 to 5 most days.\n",
        "She walked from the store to home.\n",
        "Copy the file from src to dist.\n",
        "The value went from 3 to 7.\n",
    ):
        assert "structure.false_range" not in _ids(text), text


def test_frames_are_low_severity():
    doc = document.Document.from_markdown(
        "Our platform is not just a tool, it is a partner.\n"
    )
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    frame = [f for f in findings if f["rule"] == "structure"]
    assert frame and all(f["severity"] == "low" for f in frame)


def test_frame_messages_never_show_a_raw_pattern():
    """Regex rows carry a "term" so the developer never reads a pattern."""
    import rules
    for row in rules.RULES:
        if row["name"] != "structure":
            continue
        assert "term" in row, row["id"]
        assert "\\b" not in row["message"], row["id"]


REPO_ROOT = Path(__file__).parent.parent.parent.parent


def _repo_markdown():
    skip = {".git", ".venv", "node_modules", ".superpowers", "syndicate", ".claude"}
    for p in sorted(REPO_ROOT.rglob("*.md")):
        if not skip.intersection(p.relative_to(REPO_ROOT).parts):
            yield p


def test_the_calibration_scan_actually_reaches_files():
    """A skip filter bug once made the calibration test iterate zero
    files and pass vacuously. Pin that it sees a real corpus."""
    files = list(_repo_markdown())
    assert len(files) >= 10, f"calibration scanned only {len(files)} files"
    assert any(p.name == "README.md" for p in files)


def test_frames_stay_calibrated_across_the_repo():
    """Pins the spec's calibration so a later broadening cannot pass unnoticed.

    Every hit must be suppressed by the file that quotes it. A nonzero count
    here means either a pattern got broader or a document lost its
    suppression, and either way someone should look.
    """
    import voice_check
    offenders = {}
    for path in _repo_markdown():
        hits = [f for f in voice_check.scan(path) if f["rule"] == "structure"]
        if hits:
            offenders[str(path.relative_to(REPO_ROOT))] = sorted(
                {f["rule_id"] for f in hits}
            )
    assert offenders == {}, offenders
