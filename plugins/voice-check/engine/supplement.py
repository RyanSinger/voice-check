"""Discover and load per-repo voice-check supplements."""
from pathlib import Path
from typing import Optional


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
