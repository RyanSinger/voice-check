"""Decide what text in a file counts as prose.

Masking is always length preserving: hidden characters are replaced with
spaces rather than deleted, so a finding's column still points at the right
character in the raw line and the raw line can still be quoted as a snippet.
"""
import re
import sys
from dataclasses import dataclass, field

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


BULLET_RE = re.compile(r"^(\s*)([-*+])(\s+)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
REF_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")
LINK_TARGET_RE = re.compile(r"\]\([^)\n]*\)")
AUTOLINK_RE = re.compile(r"<[^>\s]+>")
URL_RE = re.compile(r"(?:https?://|www\.)\S+")
QUOTED_RE = re.compile(r'"[^"\n]*"')
BLOCKQUOTE_RE = re.compile(r"^\s*>")

QUOTE_WORD_LIMIT = 6


def _mask_short_quotes(line: str) -> str:
    """Mask double quoted spans holding fewer than QUOTE_WORD_LIMIT words.

    A longer quotation is usually the author's own pull quote rather than a
    mention, so it stays scanned. Only double quotes participate: apostrophes
    make single quotes ambiguous.
    """
    def repl(m: re.Match) -> str:
        inner = m.group(0)[1:-1]
        if len(inner.split()) < QUOTE_WORD_LIMIT:
            return " " * (m.end() - m.start())
        return m.group(0)
    return QUOTED_RE.sub(repl, line)


def mask_line(line: str) -> str:
    """Mask everything on one line that is not prose. Length preserving."""
    # Normalize curly quotes and apostrophes to their straight forms. Each is
    # a single character, so column positions are unaffected.
    out = line.replace("’", "'").replace("“", '"').replace("”", '"')

    if BLOCKQUOTE_RE.match(out):
        return " " * len(out)

    out = INLINE_CODE_RE.sub(blank, out)
    out = REF_DEF_RE.sub(blank, out)
    out = LINK_TARGET_RE.sub(blank, out)
    out = AUTOLINK_RE.sub(blank, out)
    out = URL_RE.sub(blank, out)
    out = _mask_short_quotes(out)

    bm = BULLET_RE.match(out)
    if bm:
        start, end = bm.start(2), bm.end(2)
        out = out[:start] + " " + out[end:]

    return out


DIRECTIVE_RE = re.compile(
    r"<!--\s*voice-check:\s*(ignore|disable|enable)\b([^>]*?)-->",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Suppression:
    """A line range in which some or all rules are suppressed.

    An empty `rules` set means every rule is suppressed. Otherwise a rule is
    suppressed when either its name or its id appears in the set.
    """

    start: int
    end: int
    rules: frozenset

    def covers(self, line: int, rule_name: str, rule_id: str) -> bool:
        if not (self.start <= line <= self.end):
            return False
        if not self.rules:
            return True
        return rule_name in self.rules or rule_id in self.rules


def _parse_rule_args(raw: str) -> frozenset:
    """Split a directive's argument list into rule names and ids."""
    parts = [p.strip() for p in re.split(r"[,\s]+", raw.strip()) if p.strip()]
    return frozenset(parts)


def parse_suppressions(lines):
    """Read voice-check directives from raw lines, skipping fenced regions.

    Runs on raw text because the masking pass hides HTML comments. Skips
    fenced blocks so a documented example of the syntax stays inert.
    """
    out = []
    open_disable = None
    in_fence = False

    for num, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for m in DIRECTIVE_RE.finditer(line):
            kind = m.group(1).lower()
            rule_args = _parse_rule_args(m.group(2))

            if kind == "ignore":
                out.append(Suppression(num, num, rule_args))
            elif kind == "disable":
                if open_disable is None:
                    open_disable = (num, rule_args)
            elif kind == "enable":
                if open_disable is not None:
                    out.append(Suppression(open_disable[0], num, open_disable[1]))
                    open_disable = None

    if open_disable is not None:
        out.append(Suppression(open_disable[0], sys.maxsize, open_disable[1]))

    return out


@dataclass
class Document:
    """A file split into raw lines, masked lines, and masked full text."""

    lines: list
    scan_lines: list
    prose_text: str
    suppressions: list = field(default_factory=list)

    @classmethod
    def from_markdown(cls, text: str) -> "Document":
        raw = text.splitlines()
        blocked = mask_blocks(raw)
        scan_lines = [mask_line(line) for line in blocked]
        return cls(
            lines=raw,
            scan_lines=scan_lines,
            # Built from scan_lines rather than an independent pass, so line
            # scope and doc scope rules always see identical masked text.
            prose_text="\n".join(scan_lines),
            # Parsed from raw text, before masking hides the HTML comments.
            suppressions=parse_suppressions(raw),
        )
