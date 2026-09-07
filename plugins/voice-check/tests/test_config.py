"""Tests for per repo configuration loading."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402


def _write(tmp_path, body):
    d = tmp_path / ".claude"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "voice-check.md"
    p.write_text(body)
    return p


def test_find_for_walks_up_to_git_root(tmp_path):
    (tmp_path / ".git").mkdir()
    _write(tmp_path, "")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    target = nested / "doc.md"
    target.write_text("hi")
    assert config.find_for(target) == tmp_path / ".claude" / "voice-check.md"


def test_find_for_returns_none_when_absent(tmp_path):
    (tmp_path / ".git").mkdir()
    target = tmp_path / "doc.md"
    target.write_text("hi")
    assert config.find_for(target) is None


def test_words_block_becomes_a_rule_row(tmp_path):
    p = _write(tmp_path, "```voice-check-words\nsynergy\n```\n")
    c = config.load(p)
    assert any(r["pattern"] == "synergy" and r["kind"] == "word" for r in c.extra_rows)


def test_phrases_and_regex_blocks_load(tmp_path):
    p = _write(
        tmp_path,
        "```voice-check-phrases\nmove the needle\n```\n"
        "```voice-check-regex\n\\bsynerg\\w+\\b\n```\n",
    )
    c = config.load(p)
    kinds = {r["kind"] for r in c.extra_rows}
    assert kinds == {"phrase", "regex"}


def test_disable_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-disable\npuffery.crucial\n```\n")
    c = config.load(p)
    assert ("puffery.crucial", None) in c.disabled


def test_disable_block_with_path_scope(tmp_path):
    p = _write(tmp_path, "```voice-check-disable\nvocab_2026 in docs/ref/**\n```\n")
    c = config.load(p)
    assert ("vocab_2026", "docs/ref/**") in c.disabled


def test_severity_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-severity\npuffery = low\n```\n")
    c = config.load(p)
    assert c.severity["puffery"] == "low"


def test_exclude_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-exclude\nCHANGELOG.md\n```\n")
    c = config.load(p)
    assert c.is_excluded("CHANGELOG.md")
    assert not c.is_excluded("README.md")


def test_exclude_glob_matches_nested_paths(tmp_path):
    p = _write(tmp_path, "```voice-check-exclude\ndocs/vendor/**\n```\n")
    c = config.load(p)
    assert c.is_excluded("docs/vendor/a/b.md")


def test_one_bad_line_does_not_discard_the_rest(tmp_path):
    """A single invalid regex must not take the whole supplement with it."""
    p = _write(
        tmp_path,
        "```voice-check-regex\n[unclosed\n```\n"
        "```voice-check-words\nsynergy\n```\n",
    )
    c = config.load(p)
    assert any(r["pattern"] == "synergy" for r in c.extra_rows)
    assert any("unclosed" in w for w in c.warnings)


def test_invalid_regex_is_dropped_with_a_warning(tmp_path):
    p = _write(tmp_path, "```voice-check-regex\n[unclosed\n```\n")
    c = config.load(p)
    assert c.extra_rows == []
    assert len(c.warnings) == 1


def test_bad_severity_level_warns_and_is_ignored(tmp_path):
    p = _write(tmp_path, "```voice-check-severity\npuffery = enormous\n```\n")
    c = config.load(p)
    assert "puffery" not in c.severity
    assert any("enormous" in w for w in c.warnings)


def test_severity_for_prefers_override_then_row_default():
    c = config.Config.empty()
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert c.severity_for(row) == "medium"
    c.severity["puffery"] = "low"
    assert c.severity_for(row) == "low"
    c.severity["puffery.crucial"] = "high"
    assert c.severity_for(row) == "high"


def test_is_disabled_matches_name_or_id():
    c = config.Config.empty()
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert not c.is_disabled(row, "a.md")
    c.disabled.append(("puffery", None))
    assert c.is_disabled(row, "a.md")


def test_path_scoped_disable_applies_only_inside_the_glob():
    c = config.Config.empty()
    c.disabled.append(("puffery", "docs/**"))
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert c.is_disabled(row, "docs/a.md")
    assert not c.is_disabled(row, "src/a.md")


def test_comment_lines_inside_blocks_are_skipped(tmp_path):
    p = _write(tmp_path, "```voice-check-words\n# a note\nsynergy\n```\n")
    c = config.load(p)
    assert len(c.extra_rows) == 1


def test_unknown_rule_id_warns_but_still_records(tmp_path):
    """A stale disable must warn, never fail. Rule ids shift between versions."""
    p = _write(tmp_path, "```voice-check-disable\nno_such_rule.anywhere\n```\n")
    c = config.load(p)
    assert ("no_such_rule.anywhere", None) in c.disabled
    assert any("no_such_rule.anywhere" in w for w in c.warnings)
