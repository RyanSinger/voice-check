"""Tests for the document masking layer.

Masking is length preserving: every masked line must have the same length as
its input, so finding columns stay aligned with the raw line.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import document  # noqa: E402


def _mask(text):
    return document.mask_blocks(text.splitlines())


def test_mask_blocks_preserves_line_lengths():
    src = "---\ntitle: hi\n---\n\ntext here\n\n```\ncode\n```\n"
    out = document.mask_blocks(src.splitlines())
    for raw, masked in zip(src.splitlines(), out):
        assert len(raw) == len(masked), f"length changed for {raw!r}"


def test_frontmatter_masked_at_file_start():
    out = _mask("---\ntitle: groundbreaking\n---\nreal text\n")
    assert out[1].strip() == ""
    assert out[3] == "real text"


def test_three_hyphens_mid_file_is_not_frontmatter():
    out = _mask("intro line\n---\ntitle: groundbreaking\n---\n")
    assert "groundbreaking" in out[2]


def test_unterminated_frontmatter_is_not_masked():
    out = _mask("---\ntitle: groundbreaking\nno closing delimiter\n")
    assert "groundbreaking" in out[1]


def test_fenced_code_masked_including_fence_lines():
    out = _mask("before\n```python\ngroundbreaking = 1\n```\nafter\n")
    assert out[0] == "before"
    assert out[1].strip() == ""
    assert out[2].strip() == ""
    assert out[3].strip() == ""
    assert out[4] == "after"


def test_single_line_html_comment_masked():
    out = _mask("text <!-- groundbreaking --> more\n")
    assert "groundbreaking" not in out[0]
    assert out[0].startswith("text ")
    assert out[0].endswith(" more")


def test_multi_line_html_comment_masked():
    out = _mask("a <!-- start\ngroundbreaking\nend --> b\n")
    assert "groundbreaking" not in out[1]
    assert out[0].startswith("a ")
    assert out[2].endswith(" b")


def test_mask_line_preserves_length():
    for line in [
        "a `code` b",
        "see https://example.com/state-of-the-art-review now",
        'he said "groundbreaking," loudly',
        "  - a bullet",
        "> a blockquote",
        "[text](https://groundbreaking.example.com)",
    ]:
        assert len(document.mask_line(line)) == len(line), repr(line)


def test_inline_code_masked():
    assert "groundbreaking" not in document.mask_line("a `groundbreaking` b")


def test_url_masked():
    out = document.mask_line("see https://example.com/state-of-the-art-review now")
    assert "state-of-the-art" not in out
    assert out.startswith("see ")
    assert out.endswith(" now")


def test_link_target_masked_but_link_text_scanned():
    out = document.mask_line("[groundbreaking work](https://pivotal.example.com)")
    assert "groundbreaking work" in out
    assert "pivotal" not in out


def test_autolink_masked():
    assert "pivotal" not in document.mask_line("<https://pivotal.example.com>")


def test_reference_definition_masked():
    assert "pivotal" not in document.mask_line("[ref]: https://pivotal.example.com")


def test_blockquote_line_masked_entirely():
    assert document.mask_line("> Our product is groundbreaking.").strip() == ""


def test_bullet_marker_stripped_so_hyphen_is_not_a_separator():
    out = document.mask_line("  - a nested bullet")
    assert "-" not in out


def test_short_quoted_span_masked():
    out = document.mask_line('avoid "groundbreaking," in copy')
    assert "groundbreaking" not in out


def test_five_word_quote_masks_and_six_word_quote_does_not():
    five = document.mask_line('he said "one two three four five" today')
    assert "one two three four five" not in five

    six = document.mask_line('he said "one two three four five six" today')
    assert "one two three four five six" in six


def test_curly_quotes_are_normalized_and_masked():
    out = document.mask_line('avoid “groundbreaking” in copy')
    assert "groundbreaking" not in out


def test_single_quotes_are_not_masked():
    """Apostrophes make single quotes ambiguous, so they never mask.

    In "it's a 'test' case" a naive single quote pattern matches the span
    "s a ", which would hide real prose.
    """
    line = "it's a 'groundbreaking' case"
    assert "groundbreaking" in document.mask_line(line)


def test_column_alignment_survives_masking():
    line = 'a `xx` b "quoted" groundbreaking'
    masked = document.mask_line(line)
    assert masked.index("groundbreaking") == line.index("groundbreaking")


def test_document_prose_text_is_joined_scan_lines():
    """Line scope and doc scope must never see different text (defect 6)."""
    doc = document.Document.from_markdown("a `key` b\n\nplain key\n")
    assert doc.prose_text == "\n".join(doc.scan_lines)


def test_document_doc_scope_input_excludes_inline_code():
    doc = document.Document.from_markdown("uses `key` and `align` here\n")
    assert "key" not in doc.prose_text
    assert "align" not in doc.prose_text


def test_document_keeps_raw_lines_for_snippets():
    doc = document.Document.from_markdown("a `key` b\n")
    assert doc.lines[0] == "a `key` b"
