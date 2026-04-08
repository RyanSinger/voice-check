"""voice-check rules engine. Deterministic checks for the pre-commit hook path."""
from pathlib import Path
from typing import List

import rules
import supplement


def scan(file_path: Path) -> List[dict]:
    """Scan a file for writing rule violations. Return a list of findings.

    Each finding is a dict with: rule, line, col, snippet, message.
    Empty list means clean.

    If a per-repo supplement file is found via supplement.find_for(), its
    extra rule rows are merged into the scan table for this invocation.
    """
    file_path = Path(file_path)
    text = file_path.read_text()

    extra_rows: List[dict] = []
    sup_path = supplement.find_for(file_path)
    if sup_path is not None:
        try:
            extra_rows = supplement.load_rows(sup_path)
        except Exception:
            extra_rows = []

    return rules.scan_text(text, extra_rows=extra_rows)


def format_findings(findings: List[dict]) -> str:
    """Format findings for stdout."""
    if not findings:
        return ""
    lines = []
    for f in findings:
        if f["line"] > 0:
            loc = f"line {f['line']}"
        else:
            loc = "document"
        lines.append(f"  [{f['rule']}] {loc}: {f['message']}")
        if f.get("snippet"):
            lines.append(f"    > {f['snippet']}")
    return "\n".join(lines)


def main():
    import argparse
    import sys as _sys
    parser = argparse.ArgumentParser(prog="voice-check")
    parser.add_argument("file", type=Path, help="Markdown file to scan")
    parser.add_argument("--report-only", action="store_true", help="Print findings, do not modify file")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"voice-check: file not found: {args.file}", file=_sys.stderr)
        raise SystemExit(2)

    findings = scan(args.file)
    if findings:
        print(format_findings(findings))
    # Always exit 0 (advisory)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
