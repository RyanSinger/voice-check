"""Discover and load per-repo voice-check supplements.

A supplement file is a markdown file at `.claude/voice-check.md` in a repo.
Beyond free-form prose that the Claude skill reads, the engine looks for
fenced code blocks whose info string starts with one of:

    voice-check-phrases   each non-blank line is a literal phrase to flag
    voice-check-words     each non-blank line is a single word to flag
    voice-check-regex     each non-blank line is a raw regex to flag

Lines beginning with `#` inside a block are treated as comments and skipped.
Each loaded line becomes a rule row matching the schema used by
`rules.scan_text`. The rule name is `supplement:<kind>` and the category is
`supplement` so findings are clearly attributable.
"""
from pathlib import Path
from typing import Optional, List


SUPPORTED_KINDS = {
    "voice-check-phrases": "phrase",
    "voice-check-words": "word",
    "voice-check-regex": "regex",
}


def find_for(target: Path) -> Optional[Path]:
    """Walk up from target to git root, looking for .claude/voice-check.md.

    Stops at the first one found. Returns None if no supplement exists
    or if we walk past the git root without finding one.
    """
    target = Path(target).resolve()
    current = target.parent if target.is_file() else target
    while True:
        candidate = current / ".claude" / "voice-check.md"
        if candidate.is_file():
            return candidate
        # Stop at git root
        if (current / ".git").exists():
            return None
        # Stop at filesystem root
        if current.parent == current:
            return None
        current = current.parent


def load_rows(path: Path) -> List[dict]:
    """Parse a supplement markdown file and return extra rule rows.

    Rows use the same schema as `rules.RULES` entries. Each fenced block
    contributes one row per non-blank, non-comment line.
    """
    text = Path(path).read_text()
    rows: List[dict] = []

    in_block = False
    current_kind: Optional[str] = None  # phrase | word | regex

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                info = stripped[3:].strip()
                # info may be "voice-check-phrases" or "voice-check-phrases extras"
                info_head = info.split()[0] if info else ""
                kind = SUPPORTED_KINDS.get(info_head)
                if kind is not None:
                    in_block = True
                    current_kind = kind
                else:
                    in_block = False
                    current_kind = None
            else:
                in_block = False
                current_kind = None
            continue

        if not in_block or current_kind is None:
            continue

        if not stripped or stripped.startswith("#"):
            continue

        rows.append({
            "name": f"supplement:{current_kind}",
            "category": "supplement",
            "kind": current_kind,
            "pattern": stripped,
            "message": f"Supplement rule ({current_kind}): '{stripped}'.",
            "scope": "line",
        })

    return rows
