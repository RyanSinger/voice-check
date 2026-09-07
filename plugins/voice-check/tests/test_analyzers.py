"""Tests for computed analyzers.

An analyzer measures a property of a document rather than matching a
pattern. The bold header rule needs a ratio, which no rule row can express:
doc_min is an absolute count, so a document with 100 bullets and 5 bolded
would satisfy doc_min 4 while being 5 percent bolded.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import analyzers  # noqa: E402
import config  # noqa: E402
import document  # noqa: E402
import scanner  # noqa: E402


def _run(text):
    doc = document.Document.from_markdown(text)
    return analyzers.mechanical_bold_headers(doc, config.Config.empty())


def _bullets(n, bolded):
    """Build a document with n bullets, the first `bolded` of them bold."""
    out = ["# Heading", ""]
    for i in range(n):
        if i < bolded:
            out.append(f"- **Term {i}:** some explanation here")
        else:
            out.append(f"- plain bullet {i} with no bold run")
    return "\n".join(out) + "\n"


def test_fires_when_most_bullets_are_bolded():
    assert _run(_bullets(5, 5))


def test_silent_when_no_bullets_at_all():
    assert _run("Just a paragraph of prose with no list in it.\n") == []


def test_silent_on_an_empty_document():
    assert _run("") == []


def test_three_bullets_is_below_the_minimum():
    """MIN_BULLETS is 4, so a short list never counts as mechanical."""
    assert _run(_bullets(3, 3)) == []


def test_four_bullets_meets_the_minimum():
    assert _run(_bullets(4, 4))


def test_ratio_below_threshold_stays_silent():
    """5 of 10 is 50 percent, under the 0.6 threshold."""
    assert _run(_bullets(10, 5)) == []


def test_ratio_at_threshold_fires():
    """6 of 10 is exactly 0.6, and the comparison is inclusive."""
    assert _run(_bullets(10, 6))


def test_many_bullets_with_few_bolded_stays_silent():
    """The case doc_min cannot express: 5 bolded clears an absolute count
    of 4, but 5 percent is nowhere near mechanical."""
    assert _run(_bullets(100, 5)) == []


def test_evidence_lines_point_at_the_bolded_bullets():
    entries = _run(_bullets(5, 5))
    assert len(entries) == 1
    # Two header lines precede the bullets, so they start at line 3.
    assert entries[0]["lines"] == [3, 4, 5, 6, 7]


def test_message_is_plain_language():
    entries = _run(_bullets(5, 5))
    assert "**" not in entries[0]["message"]
    assert "bullet" in entries[0]["message"].lower()


def test_registry_entry_matches_the_rule_row_contract():
    """Phase 1's config and suppression code reads name and id off a row.
    An analyzer entry must carry the same keys or none of that applies."""
    assert analyzers.ANALYZERS
    for entry in analyzers.ANALYZERS:
        for field in ("name", "id", "category", "severity", "fn"):
            assert field in entry, entry
        assert entry["name"] == "structure"
        assert entry["id"].startswith("structure.")
        assert callable(entry["fn"])


def _scan(text, cfg=None, rel_path="a.md", line_ranges=None):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg or config.Config.empty(), rel_path, line_ranges)


def _bold_findings(findings):
    return [f for f in findings if f["rule_id"] == "structure.bold_headers"]


def test_analyzer_finding_reaches_the_scanner():
    f = _bold_findings(_scan(_bullets(5, 5)))
    assert len(f) == 1
    assert f[0]["rule"] == "structure"
    assert f[0]["severity"] == "low"


def test_analyzer_finding_points_at_a_real_line():
    """line must be a surviving evidence line, never 0."""
    f = _bold_findings(_scan(_bullets(5, 5)))
    assert f[0]["line"] == 3


def test_config_disable_by_name_removes_the_analyzer():
    cfg = config.Config.empty()
    cfg.disabled.append(("structure", None))
    assert _bold_findings(_scan(_bullets(5, 5), cfg)) == []


def test_config_disable_by_id_removes_only_the_analyzer():
    cfg = config.Config.empty()
    cfg.disabled.append(("structure.bold_headers", None))
    assert _bold_findings(_scan(_bullets(5, 5), cfg)) == []


def test_config_severity_override_reaches_the_analyzer():
    cfg = config.Config.empty()
    cfg.severity["structure.bold_headers"] = "high"
    f = _bold_findings(_scan(_bullets(5, 5), cfg))
    assert f[0]["severity"] == "high"


def test_suppression_over_every_evidence_line_drops_the_finding():
    text = "<!-- voice-check: disable structure.bold_headers -->\n" + _bullets(5, 5)
    assert _bold_findings(_scan(text)) == []


def test_analyzer_survives_line_ranges_when_evidence_is_inside():
    assert _bold_findings(_scan(_bullets(5, 5), line_ranges=[(4, 4)]))


def test_analyzer_dropped_when_no_evidence_is_in_range():
    assert _bold_findings(_scan(_bullets(5, 5), line_ranges=[(1, 1)])) == []


def test_excluded_path_skips_analyzers_too():
    cfg = config.Config.empty()
    cfg.exclude.append("skip/**")
    assert _bold_findings(_scan(_bullets(5, 5), cfg, rel_path="skip/a.md")) == []


def test_a_raising_analyzer_does_not_take_out_other_findings(monkeypatch, capsys):
    """One bad analyzer must not lose the rule passes or the other analyzers."""
    def boom(doc, cfg):
        raise RuntimeError("analyzer exploded")

    monkeypatch.setattr(
        analyzers, "ANALYZERS",
        [{"name": "structure", "id": "structure.boom", "category": "structure",
          "severity": "low", "fn": boom}],
    )
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert "structure.boom" in capsys.readouterr().err


def test_suppressed_evidence_is_excluded_before_the_range_check():
    """Suppression must reduce the evidence list BEFORE the range filter
    reads it, and the reported line must come from the surviving evidence.

    Both properties were mutation tested and found unguarded: checking
    ranges against unfiltered lines, and reporting item["lines"][0]
    instead of evidence[0], each passed the whole suite.
    """
    lines = _bullets(5, 5).splitlines()
    # Put an inline ignore on the FIRST bolded bullet only.
    lines[2] = lines[2] + " <!-- voice-check: ignore structure.bold_headers -->"
    text = "\n".join(lines) + "\n"

    # The reported line must be the SECOND bolded bullet, not the first.
    f = _bold_findings(_scan(text))
    assert len(f) == 1
    assert f[0]["line"] == 4

    # A range covering ONLY the suppressed line must drop the finding.
    assert _bold_findings(_scan(text, line_ranges=[(3, 3)])) == []

    # A range covering a surviving line keeps it.
    assert _bold_findings(_scan(text, line_ranges=[(5, 5)]))


def _register_bad_analyzer(monkeypatch, fn):
    monkeypatch.setattr(
        analyzers, "ANALYZERS",
        [{"name": "structure", "id": "structure.bad", "category": "structure",
          "severity": "low", "fn": fn}],
    )


def test_analyzer_returning_none_warns_and_leaves_other_findings(monkeypatch, capsys):
    """produced is not iterable, so the loop raises. Caught, not fatal."""
    _register_bad_analyzer(monkeypatch, lambda doc, cfg: None)
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert "structure.bad" in capsys.readouterr().err


def test_analyzer_item_missing_lines_key_warns_and_leaves_other_findings(monkeypatch, capsys):
    """A missing "lines" key is a shape violation, not zero evidence."""
    _register_bad_analyzer(monkeypatch, lambda doc, cfg: [{"message": "x"}])
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert "structure.bad" in capsys.readouterr().err


def test_analyzer_lines_not_a_list_warns_and_leaves_other_findings(monkeypatch, capsys):
    """"lines" holding a non iterable value raises when the loop reads it."""
    _register_bad_analyzer(monkeypatch, lambda doc, cfg: [{"message": "x", "lines": 3}])
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert "structure.bad" in capsys.readouterr().err


def test_analyzer_line_zero_produces_no_finding_and_no_warning(monkeypatch, capsys):
    """0 is not a valid 1 indexed line. It is dropped as evidence, quietly,
    the same as a suppressed or out of range line, not treated as an error."""
    _register_bad_analyzer(monkeypatch, lambda doc, cfg: [{"message": "x", "lines": [0]}])
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert not any(f["rule"] == "structure" for f in findings)
    assert capsys.readouterr().err == ""


def test_analyzer_line_past_end_of_file_is_dropped_quietly(monkeypatch, capsys):
    """A line number beyond the document is dropped as evidence, not an
    error: the shape is well formed, the value just cannot be used."""
    _register_bad_analyzer(monkeypatch, lambda doc, cfg: [{"message": "x", "lines": [999]}])
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert not any(f["rule"] == "structure" for f in findings)
    assert capsys.readouterr().err == ""


def test_known_identifiers_includes_analyzer_names_and_ids():
    """Otherwise disabling an analyzer would warn as an unknown rule."""
    assert "structure" in config.KNOWN_IDENTIFIERS
    assert "structure.bold_headers" in config.KNOWN_IDENTIFIERS
