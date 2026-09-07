"""Tests for the scanner: suppression, severity, and line range behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402
import document  # noqa: E402
import scanner  # noqa: E402


def _scan(text, cfg=None, rel_path="a.md", line_ranges=None):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg or config.Config.empty(), rel_path, line_ranges)


def test_findings_carry_rule_id_and_severity():
    f = _scan("The plan is simple — ship it.\n")
    assert len(f) == 1
    assert f[0]["rule"] == "no_dashes"
    assert f[0]["rule_id"] == "no_dashes.em_en"
    assert f[0]["severity"] == "high"


def test_snippet_quotes_the_raw_line_not_the_masked_line():
    f = _scan("a `x` b — c\n")
    assert f[0]["snippet"] == "a `x` b — c"


def test_mention_inside_short_quotes_is_not_flagged():
    assert _scan('avoid "groundbreaking," in copy\n') == []


def test_use_outside_quotes_is_still_flagged():
    f = _scan("our groundbreaking platform\n")
    assert any(x["rule"] == "puffery" for x in f)


def test_line_ignore_directive_suppresses_that_line():
    text = "our groundbreaking platform <!-- voice-check: ignore -->\n"
    assert _scan(text) == []


def test_line_ignore_with_rule_name_suppresses_only_that_rule():
    text = "a — b groundbreaking <!-- voice-check: ignore puffery -->\n"
    f = _scan(text)
    names = {x["rule"] for x in f}
    assert "puffery" not in names
    assert "no_dashes" in names


def test_doc_scope_hits_inside_a_suppressed_range_do_not_count():
    """A file level disable must stop the cluster finding, not just hide it."""
    text = (
        "<!-- voice-check: disable -->\n"
        "additionally the key landscape is pivotal\n"
    )
    assert _scan(text) == []


def test_doc_scope_fires_when_hits_are_not_suppressed():
    f = _scan("additionally the key landscape is pivotal\n")
    assert any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_config_disable_removes_a_rule_by_name():
    # "renowned" is puffery only. "groundbreaking" also fires promotional_tone
    # (both are documented, intentional dual category tells in rules.md), so
    # it cannot serve as a single rule example: disabling puffery alone would
    # still leave a promotional_tone finding behind. Use a clean single
    # category word instead.
    cfg = config.Config.empty()
    cfg.disabled.append(("puffery", None))
    assert _scan("our renowned platform\n", cfg) == []


def test_config_disable_removes_a_single_row_by_id():
    cfg = config.Config.empty()
    cfg.disabled.append(("puffery.renowned", None))
    assert _scan("our renowned platform\n", cfg) == []
    assert _scan("a groundbreaking author\n", cfg) != []


def test_config_severity_override_applies():
    cfg = config.Config.empty()
    cfg.severity["puffery"] = "high"
    f = _scan("our groundbreaking platform\n", cfg)
    assert f[0]["severity"] == "high"


def test_line_scope_findings_outside_ranges_are_dropped():
    text = "a — b\nc — d\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert len(f) == 1
    assert f[0]["line"] == 2


def test_doc_scope_reported_when_an_occurrence_is_inside_a_range():
    text = "plain line\nadditionally the key landscape is pivotal\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_doc_scope_dropped_when_every_occurrence_is_outside_the_ranges():
    text = "additionally the key landscape is pivotal\nplain line\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert not any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_in_ranges_treats_none_as_everything():
    assert scanner.in_ranges(5, None) is True
    assert scanner.in_ranges(5, [(1, 3)]) is False
    assert scanner.in_ranges(2, [(1, 3)]) is True
