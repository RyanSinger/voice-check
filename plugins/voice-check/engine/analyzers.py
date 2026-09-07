"""Rules that compute over a document rather than matching against it.

A rule row answers "does this pattern appear?". An analyzer answers
questions of proportion and shape that a pattern cannot reach. The bold
header rule is the motivating case: it needs the FRACTION of bullets that
open with a bold run, and doc_min is an absolute count, so a document with
100 bullets and 5 bolded would satisfy doc_min 4 while being 5 percent.

Registry entries carry the same keys a rule row carries, with "fn" in place
of "pattern" and "kind". That is deliberate: config.is_disabled,
config.severity_for, and Suppression.covers all read "name" and "id" and
nothing else, so every per repo control from Phase 1 applies to analyzers
with no change to those modules.

An analyzer returns entries of {"message": str, "lines": [int, ...]}, where
lines are the source lines that evidence the finding. It does not build a
complete finding and knows nothing about severity, suppression, or line
ranges. The scanner applies all three.
"""
import re

BULLET_RE = re.compile(r"^\s*[-*+]\s+")
BOLD_BULLET_RE = re.compile(r"^\s*[-*+]\s+\*\*[^*\n]+\*\*")

MIN_BULLETS = 4
RATIO_THRESHOLD = 0.6


def mechanical_bold_headers(doc, cfg):
    """Flag a list whose bullets nearly all open with a bold run.

    Reads doc.lines, the RAW lines, not doc.scan_lines. Masking replaces the
    bullet marker with a space, so the masked view cannot see the structure
    this rule measures. Do not "fix" this to use scan_lines for consistency.
    """
    bullet_lines = []
    bold_lines = []
    for num, line in enumerate(doc.lines, start=1):
        if not BULLET_RE.match(line):
            continue
        bullet_lines.append(num)
        if BOLD_BULLET_RE.match(line):
            bold_lines.append(num)

    if len(bullet_lines) < MIN_BULLETS:
        return []

    ratio = len(bold_lines) / len(bullet_lines)
    if ratio < RATIO_THRESHOLD:
        return []

    percent = round(ratio * 100)
    return [{
        "message": (
            f"Mechanical bold headers: {len(bold_lines)} of "
            f"{len(bullet_lines)} bullets ({percent} percent) open with a "
            f"bold run. Use them sparingly, not on every entry."
        ),
        "lines": bold_lines,
    }]


ANALYZERS = [
    {
        "name": "structure",
        "id": "structure.bold_headers",
        "category": "structure",
        "severity": "low",
        "fn": mechanical_bold_headers,
    },
]
