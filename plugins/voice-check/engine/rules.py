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
    id:       str, globally unique stable identifier, "<name>.<slug>"
    severity: "high" | "medium" | "low", used for display filtering only
"""
import re
from typing import List, Dict

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
DEFAULT_SEVERITY = "medium"

_SEVERITY_BY_NAME = {
    "no_dashes": "high",
    "markup_artifacts": "high",
    "ai_vocab_cluster": "low",
}


def slug(text: str) -> str:
    """Turn a rule pattern into a readable id fragment.

    Only used for word and phrase rows, whose patterns are plain language.
    Regex rows carry an explicit id instead, because slugging a regex
    produces unreadable noise.
    """
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "rule"


def _finalize(rows):
    """Fill in id and severity on every row that does not set them."""
    for r in rows:
        r.setdefault("severity", _SEVERITY_BY_NAME.get(r["name"], DEFAULT_SEVERITY))
        r.setdefault("id", f"{r['name']}.{slug(r['pattern'])}")
    return rows


# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------

RULES: List[dict] = _finalize([
    # -- dashes -------------------------------------------------------------
    {
        "name": "no_dashes",
        "id": "no_dashes.em_en",
        "category": "dashes",
        "kind": "regex",
        "pattern": r"[\u2014\u2013]",
        "message": "Em or en dash banned. Use commas, periods, colons, or parentheses.",
        "scope": "line",
    },
    {
        "name": "no_dashes",
        "id": "no_dashes.spaced_hyphen",
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
            "id": f"promotional_tone.{slug}",
            "category": "promotional",
            "kind": "regex",
            "pattern": p,
            "message": f"Promotional tone: {label}. Write neutral, not ad copy.",
            "scope": "line",
        }
        for p, label, slug in [
            (r"\bboasts\b", "'boasts'", "boasts"),
            (r"\bvibrant\b", "'vibrant'", "vibrant"),
            (r"\bnestled\b", "'nestled'", "nestled"),
            (r"\bin the heart of\b", "'in the heart of'", "in_the_heart_of"),
            (r"\bgroundbreaking\b", "'groundbreaking'", "groundbreaking"),
            (r"\bshowcasing\b", "'showcasing'", "showcasing"),
            (r"\bcommitment to\b", "'commitment to'", "commitment_to"),
            (r"\bnatural beauty\b", "'natural beauty'", "natural_beauty"),
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
            "id": f"copula_avoidance.{verb}_as",
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
        "id": "dangling_participle.gerund_phrase",
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
            "don't get me wrong",
            "let's dive in",
            "let's delve into",
            "we will explore",
            "let's examine",
        ]
    ],
    {
        "name": "bridge_phrases",
        "id": "bridge_phrases.in_this_section_we",
        "category": "bridge_phrases",
        "kind": "regex",
        "pattern": r"\bin this section,?\s+we\b",
        "message": "Faux-conversational bridge: 'in this section we'. Cut the meta commentary.",
        "scope": "line",
    },
    {
        "name": "bridge_phrases",
        "id": "bridge_phrases.at_the_end_of_the_day",
        "category": "bridge_phrases",
        "kind": "regex",
        "pattern": r"\bat the end of the day\b(?!\s+shift\b)",
        "message": "Faux-conversational bridge: 'at the end of the day'. Cut it or state the point directly.",
        "scope": "line",
    },

    # -- 2026 vocabulary cluster, phrase-level only -------------------------
    # Bare words (quietly, shift, signal, compound...) are too common for
    # word-boundary matching; those are skill-only. See references/rules.md.
    *[
        {
            "name": "vocab_2026",
            "category": "vocab_2026",
            "kind": "phrase",
            "pattern": p,
            "message": f"2026 AI vocabulary: '{p}'. Replace with something concrete.",
            "scope": "line",
        }
        for p in [
            "this matters because",
            "the pull of",
            "built different",
            "do the work",
            "decisions compound",
        ]
    ],
    {
        "name": "vocab_2026",
        "id": "vocab_2026.quietly_gerund",
        "category": "vocab_2026",
        "kind": "regex",
        # Stop list keeps non-gerund "ing" words (during, morning...) from firing.
        "pattern": r"\bquietly\s+(?!(?:during|morning|evening|something|anything|everything|nothing)\b)\w+ing\b",
        "message": "2026 AI vocabulary: 'quietly [verb]ing'. Name the action plainly.",
        "scope": "line",
    },
    {
        "name": "vocab_2026",
        "id": "vocab_2026.send_a_signal",
        "category": "vocab_2026",
        "kind": "regex",
        "pattern": r"\bsends?\s+(?:a|the)\s+signal\b",
        "message": "2026 AI vocabulary: 'send a signal'. Say what actually happens.",
        "scope": "line",
    },

    # -- leaked model markup artifacts --------------------------------------
    {
        "name": "markup_artifacts",
        "id": "markup_artifacts.citation_tokens",
        "category": "markup_artifacts",
        "kind": "regex",
        "pattern": (
            r"contentReference|oaicite|turn\d+search\d+|\[cite[:_]"
            r"|\[span_\d+\]|grok_card|grok_render|ppl-ai-file-upload"
            r"|attached_file"
        ),
        "message": "Leaked AI citation artifact. Delete the token; restore a real citation if one belongs here.",
        "scope": "line",
    },
    {
        "name": "markup_artifacts",
        "id": "markup_artifacts.emoji_bullet",
        "category": "markup_artifacts",
        "kind": "regex",
        "pattern": r"^\s*[☀-➿⬀-⯿\U0001F300-\U0001FAFF]️?\s+",
        "message": "Emoji used as a bullet marker. Use standard list markers.",
        "scope": "line",
    },
])


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

