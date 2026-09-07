"""Regression tests built from defects found while specifying Phase 1.

Each case is a real failure observed against the pre Phase 1 engine, not a
synthetic approximation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import voice_check  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent.parent
PLUGIN_ROOT = Path(__file__).parent.parent


def _names(findings):
    return sorted({f["rule"] for f in findings})


def test_technical_prose_does_not_trip_the_vocabulary_cluster():
    """API key, the key is read, Align the config, Additionally."""
    findings = voice_check.scan(FIXTURES / "technical.md")
    assert findings == [], _names(findings)


def test_quoted_mentions_and_urls_are_not_flagged():
    findings = voice_check.scan(FIXTURES / "mentions.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_readme():
    findings = voice_check.scan(REPO_ROOT / "README.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_rule_list():
    findings = voice_check.scan(PLUGIN_ROOT / "references" / "rules.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_spec():
    spec = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-09-07-signal-quality-design.md"
    findings = voice_check.scan(spec)
    assert findings == [], _names(findings)


def test_doc_scope_ignores_words_inside_inline_code():
    """Defect 6: doc scope used to skip inline code masking.

    "crucial", "delve", and "tapestry" are live cluster and puffery members,
    unlike "key", "align", and "additionally", whose rules were narrowed in
    a later task so none of them can fire in a plain sentence any more. With
    inline code masking removed, this exact sentence reports
    ['puffery', 'ai_vocab_cluster']; masked, it reports nothing. That is
    what pins the defect.
    """
    import document
    import config
    import scanner

    doc = document.Document.from_markdown(
        "uses `crucial` and `delve` and `tapestry`\n"
    )
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    assert findings == []


def test_line_scope_and_doc_scope_see_identical_text():
    """The two scopes must never drift apart again."""
    import document

    src = "a `key` b\n> quoted line\nplain text with align\n"
    doc = document.Document.from_markdown(src)
    assert doc.prose_text == "\n".join(doc.scan_lines)
