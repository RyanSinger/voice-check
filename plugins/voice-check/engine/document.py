"""Decide what text in a file counts as prose.

Masking is always length preserving: hidden characters are replaced with
spaces rather than deleted, so a finding's column still points at the right
character in the raw line and the raw line can still be quoted as a snippet.
"""
import re

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->")


def blank(m: re.Match) -> str:
    """Return a run of spaces the same length as the matched text."""
    return " " * (m.end() - m.start())


def mask_blocks(lines):
    """Mask frontmatter, fenced code, and HTML comments across lines.

    Returns a new list the same length as `lines`, where every entry has the
    same length as its input.
    """
    out = list(lines)
    n = len(out)
    i = 0

    # YAML frontmatter, recognized only when line 1 is exactly three hyphens
    # and a closing delimiter exists.
    if n and out[0].strip() == "---":
        j = 1
        while j < n and out[j].strip() != "---":
            j += 1
        if j < n:
            for k in range(j + 1):
                out[k] = " " * len(out[k])
            i = j + 1

    in_fence = False
    in_comment = False
    while i < n:
        line = out[i]

        if in_comment:
            end = line.find("-->")
            if end == -1:
                out[i] = " " * len(line)
            else:
                cut = end + 3
                out[i] = " " * cut + line[cut:]
                in_comment = False
            i += 1
            continue

        if FENCE_RE.match(line):
            in_fence = not in_fence
            out[i] = " " * len(line)
            i += 1
            continue

        if in_fence:
            out[i] = " " * len(line)
            i += 1
            continue

        line = HTML_COMMENT_RE.sub(blank, line)
        start = line.find("<!--")
        if start != -1:
            out[i] = line[:start] + " " * (len(line) - start)
            in_comment = True
        else:
            out[i] = line
        i += 1

    return out
