"""Rule definitions for voice-check deterministic engine."""
import re
from typing import List


def check_dashes(line: str, line_num: int) -> List[dict]:
    """Detect em dashes, en dashes, and hyphens used as separators.

    Compound-word hyphens (no surrounding spaces) are allowed.
    """
    findings = []
    # Em dash and en dash: always banned
    for m in re.finditer(r'[—–]', line):
        findings.append({
            "rule": "no_dashes",
            "line": line_num,
            "col": m.start() + 1,
            "snippet": line.rstrip('\n'),
            "message": "Em or en dash banned. Use commas, periods, colons, or parentheses.",
        })
    # Hyphen with surrounding whitespace: separator (banned)
    for m in re.finditer(r'\s-\s', line):
        findings.append({
            "rule": "no_dashes",
            "line": line_num,
            "col": m.start() + 1,
            "snippet": line.rstrip('\n'),
            "message": "Hyphen used as separator. Use commas, periods, colons, or parentheses.",
        })
    return findings


AI_VOCAB_CLUSTER = {
    "additionally", "align", "crucial", "delve", "emphasizing",
    "enduring", "enhance", "fostering", "garner", "highlight",
    "interplay", "intricate", "intricacies", "key", "landscape",
    "pivotal", "showcase", "tapestry", "testament", "underscore",
    "valuable", "vibrant", "leveraging", "leverage",
}


def check_ai_vocab_cluster(text: str) -> List[dict]:
    """Flag if 2+ AI vocabulary cluster words appear in the document."""
    text_lower = text.lower()
    matches = []
    for word in AI_VOCAB_CLUSTER:
        # Word boundaries to avoid partial matches
        for m in re.finditer(rf'\b{re.escape(word)}\b', text_lower):
            matches.append((word, m.start()))
    if len(matches) < 2:
        return []
    matched_words = sorted(set(w for w, _ in matches))
    return [{
        "rule": "ai_vocab_cluster",
        "line": 0,  # document-level finding
        "col": 0,
        "snippet": "",
        "message": f"AI vocabulary cluster: {len(matches)} occurrences across {len(matched_words)} words: {', '.join(matched_words)}. Replace with plain language.",
    }]


PUFFERY_WORDS = {
    "groundbreaking", "renowned", "pivotal", "crucial", "testament",
    "indelible", "visionary", "transformative", "paradigm-shifting",
    "world-class", "best-in-class", "cutting-edge", "state-of-the-art",
}

PROMOTIONAL_PHRASES = [
    r"\bboasts\b",
    r"\bvibrant\b",
    r"\bnestled\b",
    r"\bin the heart of\b",
    r"\bgroundbreaking\b",
    r"\bshowcasing\b",
    r"\bcommitment to\b",
    r"\bnatural beauty\b",
]


def check_puffery(line: str, line_num: int) -> List[dict]:
    findings = []
    line_lower = line.lower()
    for word in PUFFERY_WORDS:
        for m in re.finditer(rf'\b{re.escape(word)}\b', line_lower):
            findings.append({
                "rule": "puffery",
                "line": line_num,
                "col": m.start() + 1,
                "snippet": line.rstrip('\n'),
                "message": f"Puffery: '{word}'. Show importance through specifics.",
            })
    return findings


def check_promotional(line: str, line_num: int) -> List[dict]:
    findings = []
    line_lower = line.lower()
    for pattern in PROMOTIONAL_PHRASES:
        for m in re.finditer(pattern, line_lower):
            findings.append({
                "rule": "promotional_tone",
                "line": line_num,
                "col": m.start() + 1,
                "snippet": line.rstrip('\n'),
                "message": f"Promotional tone: '{m.group()}'. Write neutral, not ad copy.",
            })
    return findings
