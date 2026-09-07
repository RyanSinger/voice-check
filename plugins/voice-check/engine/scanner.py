"""Run rule rows against a Document and produce findings.

The only module that knows about both rules and documents. Applies, in order:
row selection from config, line scope matching, document scope aggregation,
suppression, severity tagging, line range filtering, and the analyzer pass.
"""
import sys
from typing import Dict, List

import analyzers
import rules


def in_ranges(line: int, line_ranges) -> bool:
    """True when line falls in one of the ranges. None means every line."""
    if line_ranges is None:
        return True
    return any(start <= line <= end for start, end in line_ranges)


def _suppressed(doc, line: int, row: dict) -> bool:
    return any(s.covers(line, row["name"], row["id"]) for s in doc.suppressions)


def _offset_to_line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _select_rows(cfg, rel_path: str) -> List[dict]:
    rows = list(rules.RULES) + list(cfg.extra_rows)
    return [r for r in rows if not cfg.is_disabled(r, rel_path)]


def scan(doc, cfg, rel_path: str = "", line_ranges=None) -> List[dict]:
    """Scan a Document and return findings tagged with severity."""
    if cfg.is_excluded(rel_path):
        return []

    rows = _select_rows(cfg, rel_path)
    findings: List[dict] = []

    # Line scope
    line_rows = [r for r in rows if r.get("scope", "line") == "line"]
    for line_num, scan_line in enumerate(doc.scan_lines, start=1):
        if not in_ranges(line_num, line_ranges):
            continue
        for row in line_rows:
            if _suppressed(doc, line_num, row):
                continue
            for m in rules.compiled(row).finditer(scan_line):
                findings.append({
                    "rule": row["name"],
                    "rule_id": row["id"],
                    "severity": cfg.severity_for(row),
                    "line": line_num,
                    "col": m.start() + 1,
                    "snippet": doc.lines[line_num - 1].rstrip("\n"),
                    "message": row["message"],
                })

    # Document scope, grouped by doc_group
    doc_rows = [r for r in rows if r.get("scope") == "doc"]
    groups: Dict[str, List[dict]] = {}
    for r in doc_rows:
        groups.setdefault(r.get("doc_group", r["name"]), []).append(r)

    for group_rows in groups.values():
        hits = []
        for row in group_rows:
            for m in rules.compiled(row).finditer(doc.prose_text):
                hit_line = _offset_to_line(doc.prose_text, m.start())
                # Suppression filters hits before the threshold check, so a
                # file level disable stops the finding rather than hiding it.
                if _suppressed(doc, hit_line, row):
                    continue
                # Word and phrase patterns are already plain language. A
                # regex row's pattern is not fit for display, so it carries
                # an explicit "term" the message should show instead.
                hits.append((row.get("term", row["pattern"]), hit_line))

        if not hits:
            continue

        threshold = max((r.get("doc_min", 1) for r in group_rows), default=1)
        if len(hits) < threshold:
            continue

        # A document scope finding survives line range filtering when at
        # least one of its occurrences falls inside a changed range.
        if not any(in_ranges(line, line_ranges) for _, line in hits):
            continue

        matched_terms = sorted({p for p, _ in hits})
        first = group_rows[0]
        rule_name = first["name"]
        if rule_name == "ai_vocab_cluster":
            message = (
                f"AI vocabulary cluster: {len(hits)} occurrences across "
                f"{len(matched_terms)} words: {', '.join(matched_terms)}. "
                f"Replace with plain language."
            )
        else:
            message = f"{rule_name}: {len(hits)} matches: {', '.join(matched_terms)}."

        findings.append({
            "rule": rule_name,
            "rule_id": first["id"],
            "severity": cfg.severity_for(first),
            "line": 0,
            "col": 0,
            "snippet": "",
            "message": message,
        })

    # Analyzer pass. Analyzers compute over the document instead of matching
    # it, and return {"message", "lines"} entries. Everything that makes an
    # entry into a finding happens here, so an analyzer needs no knowledge of
    # suppression, severity, or line ranges.
    for entry in analyzers.ANALYZERS:
        if cfg.is_disabled(entry, rel_path):
            continue
        try:
            # Malformed output is treated the same as a raising analyzer: an
            # entry missing "lines", holding the wrong type, or naming lines
            # outside the document must not lose the rule passes or the
            # other analyzers, and must never turn into a "line": 0 finding
            # backed by a negative index snippet. So entry processing lives
            # inside this same try, not just the call to "fn".
            produced = entry["fn"](doc, cfg)
            for item in produced:
                # A missing "lines" key is a genuine shape violation, not an
                # analyzer that simply found nothing, so it raises here and
                # is reported the same way a raising analyzer is. A present
                # "lines" that is not iterable (an int, for example) raises
                # naturally at the "for ln in raw_lines" below. Individual
                # bad values inside an otherwise well formed list (0,
                # negative, past end of file, non integer) are not shape
                # violations. They are dropped as evidence that does not
                # survive, the same as a suppressed or out of range line.
                raw_lines = item["lines"]
                evidence = [
                    ln for ln in raw_lines
                    if isinstance(ln, int) and 1 <= ln <= len(doc.lines)
                    and not _suppressed(doc, ln, entry)
                ]
                if not evidence:
                    continue
                if not any(in_ranges(ln, line_ranges) for ln in evidence):
                    continue
                first = evidence[0]
                findings.append({
                    "rule": entry["name"],
                    "rule_id": entry["id"],
                    "severity": cfg.severity_for(entry),
                    "line": first,
                    "col": 0,
                    "snippet": doc.lines[first - 1].rstrip("\n"),
                    "message": item["message"],
                })
        except Exception as exc:  # noqa: BLE001
            # One failing or malformed analyzer must not cost us the rule
            # passes or the other analyzers. This is the one place the
            # project's "degrade toward reporting more" principle cannot
            # hold.
            print(
                f"voice-check: analyzer {entry['id']} failed ({exc}), skipping",
                file=sys.stderr,
            )
            continue

    return findings
