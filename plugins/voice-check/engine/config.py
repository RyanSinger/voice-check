"""Load the rules that apply in this repo, and how loudly they report.

A supplement lives at `.claude/voice-check.md`, found by walking up from the
target file to the git root and stopping at the first match. Beyond prose the
skills read, the engine parses fenced blocks whose info string is one of:

    voice-check-words       one word per line, matched with word boundaries
    voice-check-phrases     one literal phrase per line, case insensitive
    voice-check-regex       one raw regex per line, case insensitive
    voice-check-disable     rule name or id, optionally "<rule> in <glob>"
    voice-check-enable      same shape, switches on a rule that ships off
    voice-check-severity    "<rule name or id> = high|medium|low"
    voice-check-exclude     one path glob per line, skipped entirely

Every line is parsed on its own. A bad line is skipped and recorded as a
warning, and the rest of the file still loads.

Path globs use fnmatch semantics, where `*` also matches a path separator, so
`docs/vendor/**` matches `docs/vendor/a/b.md`.
"""
import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional

import analyzers
import rules

RULE_KINDS = {
    "voice-check-phrases": "phrase",
    "voice-check-words": "word",
    "voice-check-regex": "regex",
}

SETTING_KINDS = {
    "voice-check-disable",
    "voice-check-enable",
    "voice-check-severity",
    "voice-check-exclude",
}

# Every identifier a disable or severity entry may name. Supplement rules add
# their own names at scan time, so an unknown identifier warns rather than
# failing: rule ids shift between versions and a stale entry must not be fatal.
KNOWN_IDENTIFIERS = (
    {r["name"] for r in rules.RULES}
    | {r["id"] for r in rules.RULES}
    | {a["name"] for a in analyzers.ANALYZERS}
    | {a["id"] for a in analyzers.ANALYZERS}
)


@dataclass
class Config:
    extra_rows: List[dict] = field(default_factory=list)
    disabled: List[tuple] = field(default_factory=list)
    enabled: List[tuple] = field(default_factory=list)
    severity: dict = field(default_factory=dict)
    exclude: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "Config":
        return cls()

    def is_excluded(self, rel_path: str) -> bool:
        return any(fnmatch(rel_path, g) for g in self.exclude)

    def _names(self, entries, row: dict, rel_path: str) -> bool:
        """True when entries name this row and apply at this path."""
        for identifier, glob in entries:
            if identifier not in (row["name"], row["id"]):
                continue
            if glob is None or fnmatch(rel_path, glob):
                return True
        return False

    def is_disabled(self, row: dict, rel_path: str) -> bool:
        """A row is off when explicitly disabled, or when it ships off by
        default and no repo has asked for it.

        An explicit disable beats an explicit enable: when a supplement says
        both, the quieter reading is the safer one.
        """
        if self._names(self.disabled, row, rel_path):
            return True
        if row.get("default_off"):
            return not self._names(self.enabled, row, rel_path)
        return False

    def severity_for(self, row: dict) -> str:
        """Row default, overridden by rule name, overridden by rule id."""
        level = row.get("severity", rules.DEFAULT_SEVERITY)
        if row["name"] in self.severity:
            level = self.severity[row["name"]]
        if row["id"] in self.severity:
            level = self.severity[row["id"]]
        return level


def find_for(target: Path) -> Optional[Path]:
    """Walk up from target to the git root looking for .claude/voice-check.md.

    Stops at the first match. Returns None if none exists at or below the git
    root, or if the filesystem root is reached first.
    """
    target = Path(target).resolve()
    current = target.parent if target.is_file() else target
    while True:
        candidate = current / ".claude" / "voice-check.md"
        if candidate.is_file():
            return candidate
        if (current / ".git").exists():
            return None
        if current.parent == current:
            return None
        current = current.parent


def _add_rule_row(cfg: Config, kind: str, value: str, where: str) -> None:
    if kind == "regex":
        try:
            re.compile(value, re.IGNORECASE)
        except re.error as exc:
            cfg.warnings.append(f"{where}: invalid regex {value!r} ({exc})")
            return
    cfg.extra_rows.append({
        "name": f"supplement:{kind}",
        "id": f"supplement.{kind}.{rules.slug(value)}",
        "category": "supplement",
        "kind": kind,
        "pattern": value,
        "message": f"Supplement rule ({kind}): '{value}'.",
        "scope": "line",
        "severity": rules.DEFAULT_SEVERITY,
    })


def _add_setting(cfg: Config, info: str, value: str, where: str) -> None:
    if info == "voice-check-exclude":
        cfg.exclude.append(value)
        return

    if info in ("voice-check-disable", "voice-check-enable"):
        verb = "disable" if info.endswith("disable") else "enable"
        target = cfg.disabled if verb == "disable" else cfg.enabled
        parts = value.split(" in ", 1)
        identifier = parts[0].strip()
        glob = parts[1].strip() if len(parts) == 2 else None
        if not identifier:
            cfg.warnings.append(f"{where}: empty {verb} entry")
            return
        if identifier not in KNOWN_IDENTIFIERS:
            cfg.warnings.append(
                f"{where}: unknown rule {identifier!r}, {verb} has no effect")
        target.append((identifier, glob))
        return

    if info == "voice-check-severity":
        if "=" not in value:
            cfg.warnings.append(f"{where}: severity needs '<rule> = <level>', got {value!r}")
            return
        identifier, level = (p.strip() for p in value.split("=", 1))
        if level not in rules.SEVERITY_ORDER:
            cfg.warnings.append(f"{where}: unknown severity level {level!r}")
            return
        if not identifier:
            cfg.warnings.append(f"{where}: empty severity entry")
            return
        if identifier not in KNOWN_IDENTIFIERS:
            cfg.warnings.append(f"{where}: unknown rule {identifier!r}, severity has no effect")
        cfg.severity[identifier] = level


def load(path: Path) -> Config:
    """Parse a supplement file into a Config. Never raises on bad content."""
    cfg = Config()
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        cfg.warnings.append(f"{path}: could not read supplement ({exc})")
        return cfg

    in_block = False
    info_head = ""

    for num, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_block:
                in_block = False
                info_head = ""
            else:
                head = stripped[3:].strip().split()[0] if stripped[3:].strip() else ""
                if head in RULE_KINDS or head in SETTING_KINDS:
                    in_block = True
                    info_head = head
            continue

        if not in_block or not stripped or stripped.startswith("#"):
            continue

        where = f"{path}:{num}"
        if info_head in RULE_KINDS:
            _add_rule_row(cfg, RULE_KINDS[info_head], stripped, where)
        else:
            _add_setting(cfg, info_head, stripped, where)

    return cfg
