"""voice-check rules engine. Deterministic checks for the pre-commit hook path.

Always advisory: under --report-only this program exits 0 in every case
except a missing target file, which is a usage error reported before any
scanning takes place. Malformed configuration, unreadable files, and
unexpected exceptions during a scan all still exit 0. Every degradation path
falls toward reporting more, never toward silently reporting less.
"""
import re
import sys
from pathlib import Path
from typing import List, Optional

import config
import document
import rules
import scanner


def parse_ranges(raw: str) -> Optional[List[tuple]]:
    """Parse "12-18,40-41" into [(12, 18), (40, 41)].

    Returns None when the input is malformed, so the caller can fall back to
    scanning the whole file.
    """
    if not raw or not raw.strip():
        return None
    out = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            return None
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        if start < 1 or end < start:
            return None
        out.append((start, end))
    return out or None


def _rel_path(file_path: Path) -> str:
    """Path relative to the git root, for matching config globs."""
    resolved = file_path.resolve()
    current = resolved.parent
    while True:
        if (current / ".git").exists():
            try:
                return resolved.relative_to(current).as_posix()
            except ValueError:
                break
        if current.parent == current:
            break
        current = current.parent
    return file_path.name


def load_config(file_path: Path) -> config.Config:
    cfg_path = config.find_for(file_path)
    if cfg_path is None:
        return config.Config.empty()
    return config.load(cfg_path)


def scan(file_path: Path, line_ranges=None, cfg: Optional[config.Config] = None) -> List[dict]:
    """Scan a file for writing rule violations. Return a list of findings."""
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if cfg is None:
        cfg = load_config(file_path)
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg, rel_path=_rel_path(file_path), line_ranges=line_ranges)


def format_findings(findings: List[dict], min_severity: str = "medium") -> str:
    """Format findings, collapsing anything below min_severity to one line."""
    if not findings:
        return ""

    floor = rules.SEVERITY_ORDER.get(min_severity, 2)
    shown, hidden = [], []
    for f in findings:
        if rules.SEVERITY_ORDER.get(f.get("severity", "medium"), 2) >= floor:
            shown.append(f)
        else:
            hidden.append(f)

    lines = []
    for f in shown:
        loc = f"line {f['line']}" if f["line"] > 0 else "document"
        lines.append(f"  [{f['rule']}] {loc}: {f['message']}")
        if f.get("snippet"):
            lines.append(f"    > {f['snippet']}")

    if hidden:
        names = ", ".join(sorted({f["rule"] for f in hidden}))
        noun = "finding" if len(hidden) == 1 else "findings"
        lines.append(
            f"  {len(hidden)} {noun} below {min_severity} severity ({names}). "
            f"Re-run with --min-severity low for detail."
        )

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="voice-check")
    parser.add_argument("file", type=Path, help="Markdown file to scan")
    parser.add_argument("--report-only", action="store_true",
                        help="Print findings, do not modify file")
    parser.add_argument("--min-severity", choices=["high", "medium", "low"],
                        default="medium",
                        help="Findings below this level collapse to a count line")
    parser.add_argument("--lines", default=None,
                        help='Restrict findings to these line ranges, e.g. "12-18,40-41"')
    args = parser.parse_args()

    if not args.file.exists():
        print(f"voice-check: file not found: {args.file}", file=sys.stderr)
        raise SystemExit(2)

    line_ranges = None
    if args.lines is not None:
        line_ranges = parse_ranges(args.lines)
        if line_ranges is None:
            print(
                f"voice-check: ignoring malformed --lines value {args.lines!r}, "
                f"scanning the whole file",
                file=sys.stderr,
            )

    try:
        cfg = load_config(args.file)
        for w in cfg.warnings:
            print(f"voice-check: {w}", file=sys.stderr)

        findings = scan(args.file, line_ranges=line_ranges, cfg=cfg)
        out = format_findings(findings, args.min_severity)
        if out:
            print(out)
    except Exception as exc:  # noqa: BLE001
        if args.report_only:
            print(f"voice-check: scan failed ({exc}), skipping", file=sys.stderr)
            raise SystemExit(0)
        raise

    raise SystemExit(0)


if __name__ == "__main__":
    main()
