"""Rule definitions for voice-check deterministic engine.

Rules are stored as a single data table. A generic scanner iterates the table
to produce findings. Supplement rules are appended to the same table format
at scan time by the CLI entry point.

Row schema (dict):
    name:     str, short rule id (e.g. "no_dashes")
    category: str, grouping label shown in messages
    kind:     "regex" | "phrase" | "word"
        regex:  pattern is a raw regex compiled case-insensitive
        phrase: pattern is a literal phrase, matched case-insensitive with
                loose word boundaries on each side
        word:   pattern is a single word, matched case-insensitive with \\b
    pattern:  str
    message:  str
    scope:    "line" | "doc"
        line scope yields one finding per match with line and column
        doc scope aggregates across the whole document
    doc_min:  int, for scope=doc, minimum number of distinct matches required
              to fire a single aggregated finding (default 1)
"""
import re
from typing import List, Dict, Iterable, Optional


# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------

RULES: List[dict] = [
    # -- dashes -------------------------------------------------------------
    {
        "name": "no_dashes",
        "category": "dashes",
        "kind": "regex",
        "pattern": r"[\u2014\u2013]",
        "message": "Em or en dash banned. Use commas, periods, colons, or parentheses.",
        "scope": "line",
    },
    {
        "name": "no_dashes",
        "category": "dashes",
        "kind": "regex",
        "pattern": r"\s-\s",
        "message": "Hyphen used as separator. Use commas, periods, colons, or parentheses.",
        "scope": "line",
    },

    # -- puffery (line scope, single-word flags) ----------------------------
    *[
        {
            "name": "puffery",
            "category": "puffery",
            "kind": "word",
            "pattern": w,
            "message": f"Puffery: '{w}'. Show importance through specifics.",
            "scope": "line",
        }
        for w in [
            "groundbreaking", "renowned", "pivotal", "crucial", "testament",
            "indelible", "visionary", "transformative", "paradigm-shifting",
            "world-class", "best-in-class", "cutting-edge", "state-of-the-art",
        ]
    ],

    # -- promotional tone ---------------------------------------------------
    *[
        {
            "name": "promotional_tone",
            "category": "promotional",
            "kind": "regex",
            "pattern": p,
            "message": f"Promotional tone: {label}. Write neutral, not ad copy.",
            "scope": "line",
        }
        for p, label in [
            (r"\bboasts\b", "'boasts'"),
            (r"\bvibrant\b", "'vibrant'"),
            (r"\bnestled\b", "'nestled'"),
            (r"\bin the heart of\b", "'in the heart of'"),
            (r"\bgroundbreaking\b", "'groundbreaking'"),
            (r"\bshowcasing\b", "'showcasing'"),
            (r"\bcommitment to\b", "'commitment to'"),
            (r"\bnatural beauty\b", "'natural beauty'"),
        ]
    ],

    # -- hedging ------------------------------------------------------------
    *[
        {
            "name": "hedging",
            "category": "hedging",
            "kind": "phrase",
            "pattern": p,
            "message": f"Hedging: '{p}'. Take ownership or cut the qualifier.",
            "scope": "line",
        }
        for p in [
            "would like to",
            "could potentially",
            "might want to",
            "it is worth noting",
            "it should be noted",
            "it is important to note",
            "i can take on",
            "i could help with",
            "pushing for this direction",
        ]
    ],

    # -- copula avoidance ---------------------------------------------------
    *[
        {
            "name": "copula_avoidance",
            "category": "copula_avoidance",
            "kind": "regex",
            # Require the phrase to be followed by a determiner or noun-like
            # token so that incidental uses (e.g. "he serves as needed") are
            # less likely to fire. Conservative to preserve clean fixtures.
            "pattern": rf"\b{verb}\s+as\s+(?:a|an|the|our|their|his|her|its|[A-Za-z]+)\b",
            "message": f"Copula avoidance: '{verb} as'. Just say 'is'.",
            "scope": "line",
        }
        for verb in ["serves", "stands", "acts", "functions"]
    ],

    # -- dangling participles ----------------------------------------------
    # Comma followed by a gerund phrase near end of sentence. Gerunds chosen
    # from the README seed list to avoid catching neutral -ing words.
    {
        "name": "dangling_participle",
        "category": "dangling_participles",
        "kind": "regex",
        "pattern": (
            r",\s+(?:highlighting|ensuring|fostering|emphasizing|"
            r"underscoring|reflecting|contributing|encompassing|"
            r"showcasing)\b[^.!?\n]*"
        ),
        "message": "Dangling participle. Cut the trailing '-ing' phrase or say something concrete.",
        "scope": "line",
    },

    # -- vague attributions -------------------------------------------------
    *[
        {
            "name": "vague_attribution",
            "category": "vague_attributions",
            "kind": "phrase",
            "pattern": p,
            "message": f"Vague attribution: '{p}'. Name the source or cut the claim.",
            "scope": "line",
        }
        for p in [
            "experts say",
            "experts agree",
            "industry observers note",
            "industry reports suggest",
            "sources say",
            "critics argue",
            "many believe",
            "it is widely believed",
            "observers note",
        ]
    ],

    # -- AI vocabulary cluster (doc scope) ----------------------------------
    *[
        {
            "name": "ai_vocab_cluster",
            "category": "ai_vocab_cluster",
            "kind": "word",
            "pattern": w,
            "message": "ai_vocab_cluster member",
            "scope": "doc",
            "doc_min": 2,
            "doc_group": "ai_vocab_cluster",
        }
        for w in [
            "additionally", "align", "crucial", "delve", "emphasizing",
            "enduring", "enhance", "fostering", "garner", "highlight",
            "interplay", "intricate", "intricacies", "key", "landscape",
            "pivotal", "showcase", "tapestry", "testament", "underscore",
            "valuable", "vibrant", "leveraging", "leverage",
        ]
    ],

    # -- faux-conversational bridges (2026 refresh) -------------------------
    *[
        {
            "name": "bridge_phrases",
            "category": "bridge_phrases",
            "kind": "phrase",
            "pattern": p,
            "message": f"Faux-conversational bridge: '{p}'. Cut it or state the point directly.",
            "scope": "line",
        }
        for p in [
            "here's the thing",
            "but here's the truth",
            "at the end of the day",
            "don't get me wrong",
            "let's dive in",
            "let's delve into",
            "we will explore",
            "let's examine",
        ]
    ],
    {
        "name": "bridge_phrases",
        "category": "bridge_phrases",
        "kind": "regex",
        "pattern": r"\bin this section,?\s+we\b",
        "message": "Faux-conversational bridge: 'in this section we'. Cut the meta commentary.",
        "scope": "line",
    },
]


# Back-compat export expected by older tests and external callers.
AI_VOCAB_CLUSTER = {
    "additionally", "align", "crucial", "delve", "emphasizing",
    "enduring", "enhance", "fostering", "garner", "highlight",
    "interplay", "intricate", "intricacies", "key", "landscape",
    "pivotal", "showcase", "tapestry", "testament", "underscore",
    "valuable", "vibrant", "leveraging", "leverage",
}

PUFFERY_WORDS = {
    r["pattern"] for r in RULES if r["name"] == "puffery"
}

PROMOTIONAL_PHRASES = [
    r["pattern"] for r in RULES if r["name"] == "promotional_tone"
]


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------

def _compile(row: dict) -> re.Pattern:
    kind = row["kind"]
    pat = row["pattern"]
    if kind == "regex":
        return re.compile(pat, re.IGNORECASE)
    if kind == "phrase":
        # Loose word boundary: require non-letter on either side, or line edge.
        return re.compile(rf"(?<![A-Za-z]){re.escape(pat)}(?![A-Za-z])", re.IGNORECASE)
    if kind == "word":
        return re.compile(rf"\b{re.escape(pat)}\b", re.IGNORECASE)
    raise ValueError(f"unknown rule kind: {kind}")


def _row_key(row: dict) -> str:
    return f"{row['name']}|{row['category']}|{row['kind']}|{row['pattern']}|{row['scope']}"


_COMPILED_CACHE: Dict[str, re.Pattern] = {}


def compiled(row: dict) -> re.Pattern:
    k = _row_key(row)
    c = _COMPILED_CACHE.get(k)
    if c is None:
        c = _compile(row)
        _COMPILED_CACHE[k] = c
    return c


# ---------------------------------------------------------------------------
# Generic scanner
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_BULLET_RE = re.compile(r"^(\s*)([-*+])(\s+)")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _prepare_line_for_rules(line: str) -> str:
    """Strip inline code spans and leading bullet-list markers from a line.

    Returns a version of the line safe for line-scope rule matching. We
    replace stripped characters with spaces so that column positions remain
    aligned with the original line (callers still snippet the raw line).
    """
    # Replace inline code spans with same-length runs of spaces
    def _blank(m: re.Match) -> str:
        return " " * (m.end() - m.start())
    out = _INLINE_CODE_RE.sub(_blank, line)

    # Strip the leading bullet marker (turn "  - foo" into "    foo")
    bm = _BULLET_RE.match(out)
    if bm:
        # Replace the [-*+] with a space, keep indentation and trailing space.
        start, end = bm.start(2), bm.end(2)
        out = out[:start] + " " + out[end:]
    return out


def _strip_code_blocks(text: str) -> str:
    """Return text with fenced code block contents replaced by blank lines.

    Preserves line count so line numbers are unaffected if needed elsewhere.
    """
    out_lines = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out_lines.append("")
            continue
        if in_fence:
            out_lines.append("")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def scan_text(text: str, extra_rows: Optional[Iterable[dict]] = None) -> List[dict]:
    """Run every rule row (built in plus extras) over text and return findings."""
    rows = list(RULES)
    if extra_rows:
        rows.extend(extra_rows)

    findings: List[dict] = []

    # Line-scope pass. Track fenced code blocks and skip their contents.
    line_rows = [r for r in rows if r.get("scope", "line") == "line"]
    in_fence = False
    for line_num, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        scan_line = _prepare_line_for_rules(line)
        for row in line_rows:
            rx = compiled(row)
            for m in rx.finditer(scan_line):
                findings.append({
                    "rule": row["name"],
                    "line": line_num,
                    "col": m.start() + 1,
                    "snippet": line.rstrip("\n"),
                    "message": row["message"],
                })

    # Doc-scope pass: group rows by doc_group and aggregate.
    # Exclude fenced code block content from doc-scope input.
    doc_text = _strip_code_blocks(text)
    doc_rows = [r for r in rows if r.get("scope") == "doc"]
    groups: Dict[str, List[dict]] = {}
    for r in doc_rows:
        groups.setdefault(r.get("doc_group", r["name"]), []).append(r)

    for group_name, group_rows in groups.items():
        hits: List[tuple] = []  # (pattern, start)
        for row in group_rows:
            rx = compiled(row)
            for m in rx.finditer(doc_text):
                hits.append((row["pattern"], m.start()))
        if not hits:
            continue
        threshold = max((r.get("doc_min", 1) for r in group_rows), default=1)
        if len(hits) < threshold:
            continue
        matched_terms = sorted({h[0] for h in hits})
        rule_name = group_rows[0]["name"]
        findings.append({
            "rule": rule_name,
            "line": 0,
            "col": 0,
            "snippet": "",
            "message": (
                f"AI vocabulary cluster: {len(hits)} occurrences across "
                f"{len(matched_terms)} words: {', '.join(matched_terms)}. "
                f"Replace with plain language."
            ) if rule_name == "ai_vocab_cluster" else (
                f"{rule_name}: {len(hits)} matches: {', '.join(matched_terms)}."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Back-compat shims for older callers and tests that imported these helpers
# directly. Each delegates to the table scanner, filtered to the relevant
# rule category.
# ---------------------------------------------------------------------------

def _filter_rows(category: str, scope: str) -> List[dict]:
    return [r for r in RULES if r["category"] == category and r.get("scope", "line") == scope]


def check_dashes(line: str, line_num: int) -> List[dict]:
    out = []
    for row in _filter_rows("dashes", "line"):
        for m in compiled(row).finditer(line):
            out.append({
                "rule": row["name"],
                "line": line_num,
                "col": m.start() + 1,
                "snippet": line.rstrip("\n"),
                "message": row["message"],
            })
    return out


def check_puffery(line: str, line_num: int) -> List[dict]:
    out = []
    for row in _filter_rows("puffery", "line"):
        for m in compiled(row).finditer(line):
            out.append({
                "rule": row["name"],
                "line": line_num,
                "col": m.start() + 1,
                "snippet": line.rstrip("\n"),
                "message": row["message"],
            })
    return out


def check_promotional(line: str, line_num: int) -> List[dict]:
    out = []
    for row in _filter_rows("promotional", "line"):
        for m in compiled(row).finditer(line):
            out.append({
                "rule": row["name"],
                "line": line_num,
                "col": m.start() + 1,
                "snippet": line.rstrip("\n"),
                "message": row["message"],
            })
    return out


def check_ai_vocab_cluster(text: str) -> List[dict]:
    # Run only the ai_vocab_cluster doc-scope rules via the scanner.
    rows = [r for r in RULES if r["category"] == "ai_vocab_cluster"]

    scan_src = _strip_code_blocks(text)
    hits = []
    for row in rows:
        for m in compiled(row).finditer(scan_src):
            hits.append((row["pattern"], m.start()))
    if len(hits) < 2:
        return []
    matched_words = sorted({h[0] for h in hits})
    return [{
        "rule": "ai_vocab_cluster",
        "line": 0,
        "col": 0,
        "snippet": "",
        "message": (
            f"AI vocabulary cluster: {len(hits)} occurrences across "
            f"{len(matched_words)} words: {', '.join(matched_words)}. "
            f"Replace with plain language."
        ),
    }]
