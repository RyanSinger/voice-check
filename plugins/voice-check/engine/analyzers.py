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


EMBEDDED_TOKEN_RE = re.compile(
    r"utm_source=(?:chatgpt\.com|openai|copilot\.com)"
    r"|referrer=grok\.com"
    r"|attributableIndex",
    re.IGNORECASE,
)


def embedded_artifacts(doc, cfg):
    """Flag leaked AI tokens that live inside URLs or JSON.

    These cannot be rule rows. A tracking parameter sits inside a URL, and
    `mask_line` blanks URLs entirely; a JSON attribution key sits inside
    double quotes, and the short quote masker blanks those. Both are correct
    masking decisions, since neither a URL nor a quoted key is prose, but
    they mean a line scope rule can never see the token.

    Reads doc.lines, the RAW lines, for exactly that reason. Do not switch
    this to doc.scan_lines: the masking that makes the rest of the engine
    accurate is what hides these.

    One entry per matching line, so each finding points at its own line.
    """
    out = []
    for num, line in enumerate(doc.lines, start=1):
        m = EMBEDDED_TOKEN_RE.search(line)
        if not m:
            continue
        out.append({
            "message": (
                f"Leaked AI artifact embedded in a URL or JSON: "
                f"'{m.group(0)}'. Delete the token, and restore a real link "
                f"or citation if one belongs here."
            ),
            "lines": [num],
        })
    return out


ANALYZERS = [
    {
        # Ships off. Measured across 206 markdown files, this rule fired on
        # 6.8 percent of them with no identifiable true positive: every hit
        # was a definition list. The Wikipedia examples this rule was built
        # from are definition lists too, so no syntactic test separates the
        # tell from the legitimate pattern. Enable it per repo with a
        # voice-check-enable block naming structure.bold_headers.
        "name": "structure",
        "id": "structure.bold_headers",
        "category": "structure",
        "severity": "low",
        "default_off": True,
        "fn": mechanical_bold_headers,
    },
    {
        # Shares the markup_artifacts name so disabling that family kills
        # both the citation token row and this analyzer, which is the intent.
        "name": "markup_artifacts",
        "id": "markup_artifacts.embedded_tokens",
        "category": "markup_artifacts",
        "severity": "high",
        "fn": embedded_artifacts,
    },
]
