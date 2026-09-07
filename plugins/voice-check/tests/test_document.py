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
