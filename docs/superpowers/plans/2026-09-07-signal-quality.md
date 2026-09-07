# Signal Quality (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the voice-check pre-commit hook quiet enough to trust, by teaching the engine to tell a mention from a use, accept suppression directives, respect per-repo configuration, and report only on lines you actually changed.

**Architecture:** The engine splits into five modules with an acyclic dependency graph. `document.py` decides what text is prose and produces length-preserving masked lines plus suppression directives. `config.py` loads global defaults merged with a per-repo supplement. `rules.py` shrinks to the rule table plus compilation, with every row gaining a stable id and a severity. `scanner.py` runs rows against a document and applies suppression, severity, and line ranges. `voice_check.py` remains the CLI.

**Tech Stack:** Python 3.11 or later, standard library only. pytest for tests. Bash for the git hook. No new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-09-07-signal-quality-design.md`

## Global Constraints

- The engine imports from the Python standard library only. No new runtime dependencies.
- Python 3.11 or later.
- The pre-commit hook is advisory and **always exits 0**. Severity never blocks a commit.
- The `# === voice-check section start ===` and `# === voice-check section end ===` hook contract is preserved exactly.
- **No dashes in any prose output**, including commit messages, documentation, code comments, and test docstrings. Em dashes, en dashes, and hyphens used as separators are all banned. Use commas, periods, colons, or parentheses. Hyphens inside compound words are fine.
- Masking is always **length preserving**: replace hidden characters with spaces, never delete them, so column numbers stay aligned with the raw line.
- Every degradation path falls toward reporting more, never toward silently reporting less. The single exception is an unexpected exception under `--report-only`, where printing nothing beats blocking a commit.

## Working Directory

All paths are relative to `/Users/ryan/voice-check` unless stated otherwise. Test commands run from `plugins/voice-check`.

Set up the virtualenv once before starting:

```bash
cd /Users/ryan/voice-check/plugins/voice-check
python3 -m venv .venv
.venv/bin/pip install pytest
```

Run the full suite with:

```bash
cd /Users/ryan/voice-check/plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

## File Structure

**Created:**

- `plugins/voice-check/engine/document.py`: what text is prose. Owns the `Document` and `Suppression` types, block masking, line masking, and suppression directive parsing.
- `plugins/voice-check/engine/config.py`: what rules apply here and how loudly. Owns supplement discovery, all six fenced block kinds, and per line error reporting. Replaces `supplement.py`.
- `plugins/voice-check/engine/scanner.py`: what is wrong with this document. Owns rule execution, suppression application, severity tagging, and line range filtering.
- `plugins/voice-check/tests/test_document.py`
- `plugins/voice-check/tests/test_config.py`
- `plugins/voice-check/tests/test_scanner.py`
- `plugins/voice-check/tests/test_regressions.py`
- `plugins/voice-check/tests/fixtures/technical.md`
- `plugins/voice-check/tests/fixtures/mentions.md`

**Modified:**

- `plugins/voice-check/engine/rules.py`: gains `id` and `severity` on every row, loses the scanner and the dead shims.
- `plugins/voice-check/engine/voice_check.py`: gains `--min-severity` and `--lines`, becomes the orchestrator.
- `plugins/voice-check/templates/pre-commit.sh`: computes staged diff ranges.
- `plugins/voice-check/tests/test_hook_pipeline.py`: stale assertion fixed, diff scoping coverage added.
- `plugins/voice-check/tests/test_engine.py`: updated for the new module layout.
- `.github/workflows/test.yml`: runs the whole suite.
- `plugins/voice-check/references/rules.md`, `README.md`, `CLAUDE.md`, `plugins/voice-check/.claude-plugin/plugin.json`, both `SKILL.md` files.

**Deleted:**

- `plugins/voice-check/engine/supplement.py` (absorbed into `config.py`).

---

### Task 1: Repair the red suite and widen CI

The suite fails on a clean checkout of `main` and CI cannot see it. Everything downstream depends on a trustworthy green baseline, so this comes first.

**Files:**
- Modify: `plugins/voice-check/tests/test_hook_pipeline.py:136-140`
- Modify: `.github/workflows/test.yml:20`

**Interfaces:**
- Consumes: nothing.
- Produces: a green suite and a CI job that runs it. No code interfaces.

- [ ] **Step 1: Reproduce the failure**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`

Expected: `1 failed, 62 passed`. The failure is `test_install_hook_renders_engine_path` with an `AssertionError` on `rendered hook missing VOICE_CHECK_ENGINE line`.

Confirm the cause before changing anything:

```bash
grep -n 'BAKED_ENGINE=\|^VOICE_CHECK_ENGINE=' plugins/voice-check/templates/pre-commit.sh
```

Expected: one hit, `11:BAKED_ENGINE="__VOICE_CHECK_ENGINE__"`. Commit `6e7b700` renamed the variable and the test was never updated.

- [ ] **Step 2: Fix the stale assertion**

In `plugins/voice-check/tests/test_hook_pipeline.py`, replace this block:

```python
    engine_line = next(
        (ln for ln in content.splitlines() if ln.startswith("VOICE_CHECK_ENGINE=")),
        None,
    )
    assert engine_line is not None, "rendered hook missing VOICE_CHECK_ENGINE line"
```

with:

```python
    engine_line = next(
        (ln for ln in content.splitlines() if ln.startswith("BAKED_ENGINE=")),
        None,
    )
    assert engine_line is not None, "rendered hook missing BAKED_ENGINE line"
```

- [ ] **Step 3: Run the suite to verify it is green**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `63 passed`

- [ ] **Step 4: Widen the CI job**

In `.github/workflows/test.yml`, change the run line from:

```yaml
        run: cd plugins/voice-check && python -m pytest tests/test_engine.py -v
```

to:

```yaml
        run: cd plugins/voice-check && python -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add plugins/voice-check/tests/test_hook_pipeline.py .github/workflows/test.yml
git commit -m "fix(tests): read BAKED_ENGINE in hook test, run whole suite in CI

Commit 6e7b700 renamed the hook variable from VOICE_CHECK_ENGINE to
BAKED_ENGINE but test_install_hook_renders_engine_path still searched for
the old name, so the suite has been red on main. CI missed it because the
workflow ran only test_engine.py, leaving the 8 hook pipeline and skill
path tests unexecuted.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Rule identity and severity

Give every rule row a stable id and a severity, and delete the dead back-compat code. This is additive to the row schema, so the existing scanner keeps working and the suite stays green throughout.

**Files:**
- Modify: `plugins/voice-check/engine/rules.py`
- Test: `plugins/voice-check/tests/test_engine.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `rules.RULES: list[dict]`, where every row now carries `id: str` and `severity: str` in addition to the existing `name`, `category`, `kind`, `pattern`, `message`, `scope`, and optional `doc_min` and `doc_group`.
  - `rules.SEVERITY_ORDER: dict[str, int]` mapping `"low"` to 1, `"medium"` to 2, `"high"` to 3.
  - `rules.DEFAULT_SEVERITY: str` equal to `"medium"`.
  - `rules.compiled(row: dict) -> re.Pattern` (unchanged signature).
  - `rules.slug(text: str) -> str`, turning plain language into an id fragment. Public because `config.py` reuses it for supplement row ids.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_engine.py`:

```python
import rules  # noqa: E402


def test_every_rule_row_has_a_unique_id():
    ids = [r["id"] for r in rules.RULES]
    assert len(ids) == len(set(ids)), "duplicate rule ids found"
    assert all(ids), "some rule row has an empty id"


def test_every_rule_row_has_a_valid_severity():
    for r in rules.RULES:
        assert r["severity"] in rules.SEVERITY_ORDER, r["id"]


def test_word_rows_derive_readable_ids():
    by_id = {r["id"] for r in rules.RULES}
    assert "puffery.groundbreaking" in by_id
    assert "hedging.would_like_to" in by_id


def test_regex_rows_carry_explicit_ids():
    by_id = {r["id"] for r in rules.RULES}
    assert "no_dashes.em_en" in by_id
    assert "no_dashes.spaced_hyphen" in by_id


def test_default_severity_assignments():
    sev = {r["name"]: r["severity"] for r in rules.RULES}
    assert sev["no_dashes"] == "high"
    assert sev["markup_artifacts"] == "high"
    assert sev["ai_vocab_cluster"] == "low"
    assert sev["puffery"] == "medium"


def test_dead_backcompat_shims_are_gone():
    for name in (
        "check_dashes", "check_puffery", "check_promotional",
        "check_ai_vocab_cluster", "AI_VOCAB_CLUSTER",
        "PUFFERY_WORDS", "PROMOTIONAL_PHRASES",
    ):
        assert not hasattr(rules, name), f"{name} should have been deleted"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_engine.py -q -k "rule_row or readable_ids or explicit_ids or severity_assignments or backcompat"`
Expected: FAIL with `AttributeError` or `KeyError: 'id'`

- [ ] **Step 3: Add the slug helper and finalizer to rules.py**

Insert immediately after the `import re` line at the top of `plugins/voice-check/engine/rules.py`:

```python
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
```

- [ ] **Step 4: Wrap the rule table**

Change the table declaration line in `rules.py` from:

```python
RULES: List[dict] = [
```

to:

```python
RULES: List[dict] = _finalize([
```

and change its closing `]` (the line reading `]` immediately before the `# Back-compat export` comment) to:

```python
])
```

- [ ] **Step 5: Add explicit ids to the regex rows**

Add an `"id"` entry to each hand written regex row. The two dash rows become:

```python
    {
        "name": "no_dashes",
        "id": "no_dashes.em_en",
        "category": "dashes",
        "kind": "regex",
        "pattern": r"[—–]",
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
```

Add these ids to the remaining literal regex rows, matching them by their existing `pattern`:

| Existing pattern fragment | id to add |
| --- | --- |
| `\bin this section,?\s+we\b` | `bridge_phrases.in_this_section_we` |
| `\bat the end of the day\b(?!\s+shift\b)` | `bridge_phrases.at_the_end_of_the_day` |
| `\bquietly\s+(?!...)\w+ing\b` | `vocab_2026.quietly_gerund` |
| `\bsends?\s+(?:a\|the)\s+signal\b` | `vocab_2026.send_a_signal` |
| `contentReference\|oaicite\|...` | `markup_artifacts.citation_tokens` |
| `^\s*[☀-➿...]️?\s+` | `markup_artifacts.emoji_bullet` |
| `,\s+(?:highlighting\|ensuring\|...)` | `dangling_participle.gerund_phrase` |

- [ ] **Step 6: Give the generated regex rows readable ids**

The promotional and copula rows are generated by comprehensions over regex patterns, so their slugs would be unreadable. Change the promotional comprehension to carry a slug in its tuple:

```python
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
```

And the copula comprehension gains an id built from its verb:

```python
            "id": f"copula_avoidance.{verb}_as",
```

- [ ] **Step 7: Delete the dead back-compat block**

Delete everything in `rules.py` from the comment line reading `# Back-compat export expected by older tests and external callers.` through the end of the file, except keep `scan_text`, `_compile`, `_row_key`, `_COMPILED_CACHE`, `compiled`, `_FENCE_RE`, `_BULLET_RE`, `_INLINE_CODE_RE`, `_prepare_line_for_rules`, and `_strip_code_blocks`, which later tasks move rather than delete.

Concretely, delete these definitions: `AI_VOCAB_CLUSTER`, `PUFFERY_WORDS`, `PROMOTIONAL_PHRASES`, `_filter_rows`, `check_dashes`, `check_puffery`, `check_promotional`, `check_ai_vocab_cluster`.

Verify nothing referenced them:

```bash
grep -rn 'check_dashes\|check_puffery\|check_promotional\|check_ai_vocab_cluster\|AI_VOCAB_CLUSTER\|PUFFERY_WORDS\|PROMOTIONAL_PHRASES' plugins/voice-check/
```

Expected: no output.

- [ ] **Step 8: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `69 passed`

- [ ] **Step 9: Commit**

```bash
git add plugins/voice-check/engine/rules.py plugins/voice-check/tests/test_engine.py
git commit -m "feat(rules): stable per row ids and severity, drop dead shims

Every rule row now carries a unique id and a severity. Word and phrase rows
derive readable ids from their pattern; regex rows carry explicit ids.
no_dashes and markup_artifacts default to high, ai_vocab_cluster to low,
everything else to medium.

Deletes the back-compat exports and shim functions, which had no call sites
anywhere in the repository.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Document block masking

Create `document.py` with the block level masking pass: YAML frontmatter, fenced code, and HTML comments. Nothing is wired into the scanner yet, so the suite stays green.

**Files:**
- Create: `plugins/voice-check/engine/document.py`
- Test: `plugins/voice-check/tests/test_document.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `document.blank(m: re.Match) -> str`, returning a run of spaces the same length as the match.
  - `document.mask_blocks(lines: list[str]) -> list[str]`, returning a parallel list where frontmatter, fenced code, and HTML comment regions are replaced by spaces. Every returned line has the same length as its input.
  - `document.FENCE_RE`, `document.HTML_COMMENT_RE` as module level compiled patterns.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_document.py`:

```python
"""Tests for the document masking layer.

Masking is length preserving: every masked line must have the same length as
its input, so finding columns stay aligned with the raw line.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import document  # noqa: E402


def _mask(text):
    return document.mask_blocks(text.splitlines())


def test_mask_blocks_preserves_line_lengths():
    src = "---\ntitle: hi\n---\n\ntext here\n\n```\ncode\n```\n"
    out = document.mask_blocks(src.splitlines())
    for raw, masked in zip(src.splitlines(), out):
        assert len(raw) == len(masked), f"length changed for {raw!r}"


def test_frontmatter_masked_at_file_start():
    out = _mask("---\ntitle: groundbreaking\n---\nreal text\n")
    assert out[1].strip() == ""
    assert out[3] == "real text"


def test_three_hyphens_mid_file_is_not_frontmatter():
    out = _mask("intro line\n---\ntitle: groundbreaking\n---\n")
    assert "groundbreaking" in out[2]


def test_unterminated_frontmatter_is_not_masked():
    out = _mask("---\ntitle: groundbreaking\nno closing delimiter\n")
    assert "groundbreaking" in out[1]


def test_fenced_code_masked_including_fence_lines():
    out = _mask("before\n```python\ngroundbreaking = 1\n```\nafter\n")
    assert out[0] == "before"
    assert out[1].strip() == ""
    assert out[2].strip() == ""
    assert out[3].strip() == ""
    assert out[4] == "after"


def test_single_line_html_comment_masked():
    out = _mask("text <!-- groundbreaking --> more\n")
    assert "groundbreaking" not in out[0]
    assert out[0].startswith("text ")
    assert out[0].endswith(" more")


def test_multi_line_html_comment_masked():
    out = _mask("a <!-- start\ngroundbreaking\nend --> b\n")
    assert "groundbreaking" not in out[1]
    assert out[0].startswith("a ")
    assert out[2].endswith(" b")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'document'`

- [ ] **Step 3: Write document.py**

Create `plugins/voice-check/engine/document.py`:

```python
"""Decide what text in a file counts as prose.

Masking is always length preserving: hidden characters are replaced with
spaces rather than deleted, so a finding's column still points at the right
character in the raw line and the raw line can still be quoted as a snippet.
"""
import re

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->")


def blank(m: re.Match) -> str:
    """Return a run of spaces the same length as the matched text."""
    return " " * (m.end() - m.start())


def mask_blocks(lines):
    """Mask frontmatter, fenced code, and HTML comments across lines.

    Returns a new list the same length as `lines`, where every entry has the
    same length as its input.
    """
    out = list(lines)
    n = len(out)
    i = 0

    # YAML frontmatter, recognized only when line 1 is exactly three hyphens
    # and a closing delimiter exists.
    if n and out[0].strip() == "---":
        j = 1
        while j < n and out[j].strip() != "---":
            j += 1
        if j < n:
            for k in range(j + 1):
                out[k] = " " * len(out[k])
            i = j + 1

    in_fence = False
    in_comment = False
    while i < n:
        line = out[i]

        if in_comment:
            end = line.find("-->")
            if end == -1:
                out[i] = " " * len(line)
            else:
                cut = end + 3
                out[i] = " " * cut + line[cut:]
                in_comment = False
            i += 1
            continue

        if FENCE_RE.match(line):
            in_fence = not in_fence
            out[i] = " " * len(line)
            i += 1
            continue

        if in_fence:
            out[i] = " " * len(line)
            i += 1
            continue

        line = HTML_COMMENT_RE.sub(blank, line)
        start = line.find("<!--")
        if start != -1:
            out[i] = line[:start] + " " * (len(line) - start)
            in_comment = True
        else:
            out[i] = line
        i += 1

    return out
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q`
Expected: `7 passed`

- [ ] **Step 5: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `76 passed`

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/engine/document.py plugins/voice-check/tests/test_document.py
git commit -m "feat(document): block level masking for frontmatter, fences, comments

New document module owns the question of what text is prose. This commit
adds the block pass. Masking replaces hidden characters with spaces rather
than deleting them, so column positions stay aligned with the raw line.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Document line masking and the Document type

Add the line level masking pass and the `Document` container. This is where the mention versus use fix actually lands, and where defect 6 closes: `prose_text` is built by joining `scan_lines`, so line scope and document scope rules cannot see different text.

**Files:**
- Modify: `plugins/voice-check/engine/document.py`
- Test: `plugins/voice-check/tests/test_document.py`

**Interfaces:**
- Consumes: `document.mask_blocks`, `document.blank` from Task 3.
- Produces:
  - `document.mask_line(line: str) -> str`, length preserving.
  - `document.Document`, a dataclass with fields `lines: list[str]`, `scan_lines: list[str]`, `prose_text: str`, and `suppressions: list` (empty until Task 5).
  - `document.Document.from_markdown(text: str) -> Document`, the only constructor callers use.
  - `document.QUOTE_WORD_LIMIT: int` equal to 6.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_document.py`:

```python
def test_mask_line_preserves_length():
    for line in [
        "a `code` b",
        "see https://example.com/state-of-the-art-review now",
        'he said "groundbreaking," loudly',
        "  - a bullet",
        "> a blockquote",
        "[text](https://groundbreaking.example.com)",
    ]:
        assert len(document.mask_line(line)) == len(line), repr(line)


def test_inline_code_masked():
    assert "groundbreaking" not in document.mask_line("a `groundbreaking` b")


def test_url_masked():
    out = document.mask_line("see https://example.com/state-of-the-art-review now")
    assert "state-of-the-art" not in out
    assert out.startswith("see ")
    assert out.endswith(" now")


def test_link_target_masked_but_link_text_scanned():
    out = document.mask_line("[groundbreaking work](https://pivotal.example.com)")
    assert "groundbreaking work" in out
    assert "pivotal" not in out


def test_autolink_masked():
    assert "pivotal" not in document.mask_line("<https://pivotal.example.com>")


def test_reference_definition_masked():
    assert "pivotal" not in document.mask_line("[ref]: https://pivotal.example.com")


def test_blockquote_line_masked_entirely():
    assert document.mask_line("> Our product is groundbreaking.").strip() == ""


def test_bullet_marker_stripped_so_hyphen_is_not_a_separator():
    out = document.mask_line("  - a nested bullet")
    assert "-" not in out


def test_short_quoted_span_masked():
    out = document.mask_line('avoid "groundbreaking," in copy')
    assert "groundbreaking" not in out


def test_five_word_quote_masks_and_six_word_quote_does_not():
    five = document.mask_line('he said "one two three four five" today')
    assert "one two three four five" not in five

    six = document.mask_line('he said "one two three four five six" today')
    assert "one two three four five six" in six


def test_curly_quotes_are_normalized_and_masked():
    out = document.mask_line('avoid “groundbreaking” in copy')
    assert "groundbreaking" not in out


def test_single_quotes_are_not_masked():
    """Apostrophes make single quotes ambiguous, so they never mask.

    In "it's a 'test' case" a naive single quote pattern matches the span
    "s a ", which would hide real prose.
    """
    line = "it's a 'groundbreaking' case"
    assert "groundbreaking" in document.mask_line(line)


def test_column_alignment_survives_masking():
    line = 'a `xx` b "quoted" groundbreaking'
    masked = document.mask_line(line)
    assert masked.index("groundbreaking") == line.index("groundbreaking")


def test_document_prose_text_is_joined_scan_lines():
    """Line scope and doc scope must never see different text (defect 6)."""
    doc = document.Document.from_markdown("a `key` b\n\nplain key\n")
    assert doc.prose_text == "\n".join(doc.scan_lines)


def test_document_doc_scope_input_excludes_inline_code():
    doc = document.Document.from_markdown("uses `key` and `align` here\n")
    assert "key" not in doc.prose_text
    assert "align" not in doc.prose_text


def test_document_keeps_raw_lines_for_snippets():
    doc = document.Document.from_markdown("a `key` b\n")
    assert doc.lines[0] == "a `key` b"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q -k "mask_line or document_"`
Expected: FAIL with `AttributeError: module 'document' has no attribute 'mask_line'`

- [ ] **Step 3: Add line masking to document.py**

Append to `plugins/voice-check/engine/document.py`:

```python
from dataclasses import dataclass, field

BULLET_RE = re.compile(r"^(\s*)([-*+])(\s+)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
REF_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")
LINK_TARGET_RE = re.compile(r"\]\([^)\n]*\)")
AUTOLINK_RE = re.compile(r"<[^>\s]+>")
URL_RE = re.compile(r"(?:https?://|www\.)\S+")
QUOTED_RE = re.compile(r'"[^"\n]*"')
BLOCKQUOTE_RE = re.compile(r"^\s*>")

QUOTE_WORD_LIMIT = 6


def _mask_short_quotes(line: str) -> str:
    """Mask double quoted spans holding fewer than QUOTE_WORD_LIMIT words.

    A longer quotation is usually the author's own pull quote rather than a
    mention, so it stays scanned. Only double quotes participate: apostrophes
    make single quotes ambiguous.
    """
    def repl(m: re.Match) -> str:
        inner = m.group(0)[1:-1]
        if len(inner.split()) < QUOTE_WORD_LIMIT:
            return " " * (m.end() - m.start())
        return m.group(0)
    return QUOTED_RE.sub(repl, line)


def mask_line(line: str) -> str:
    """Mask everything on one line that is not prose. Length preserving."""
    # Normalize curly quotes and apostrophes to their straight forms. Each is
    # a single character, so column positions are unaffected.
    out = line.replace("’", "'").replace("“", '"').replace("”", '"')

    if BLOCKQUOTE_RE.match(out):
        return " " * len(out)

    out = INLINE_CODE_RE.sub(blank, out)
    out = REF_DEF_RE.sub(blank, out)
    out = LINK_TARGET_RE.sub(blank, out)
    out = AUTOLINK_RE.sub(blank, out)
    out = URL_RE.sub(blank, out)
    out = _mask_short_quotes(out)

    bm = BULLET_RE.match(out)
    if bm:
        start, end = bm.start(2), bm.end(2)
        out = out[:start] + " " + out[end:]

    return out


@dataclass
class Document:
    """A file split into raw lines, masked lines, and masked full text."""

    lines: list
    scan_lines: list
    prose_text: str
    suppressions: list = field(default_factory=list)

    @classmethod
    def from_markdown(cls, text: str) -> "Document":
        raw = text.splitlines()
        blocked = mask_blocks(raw)
        scan_lines = [mask_line(line) for line in blocked]
        return cls(
            lines=raw,
            scan_lines=scan_lines,
            # Built from scan_lines rather than an independent pass, so line
            # scope and doc scope rules always see identical masked text.
            prose_text="\n".join(scan_lines),
            suppressions=[],
        )
```

Move the `from dataclasses import ...` line to the top of the file alongside `import re`.

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q`
Expected: `23 passed`

- [ ] **Step 5: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `92 passed`

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/engine/document.py plugins/voice-check/tests/test_document.py
git commit -m "feat(document): line masking and the Document type

Masks inline code, URLs, link targets, autolinks, reference definitions,
blockquotes, bullet markers, and double quoted spans under six words. Single
quotes never mask because apostrophes make them ambiguous.

prose_text is built by joining scan_lines rather than by an independent
pass, so line scope and document scope rules can no longer see different
text. Closes defect 6 from the spec.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Suppression directive parsing

Parse `voice-check` directives out of the raw text. Two ordering constraints drive the design: directives must be read before masking (because masking hides HTML comments), and directive parsing must skip fenced regions (because `references/rules.md` will document the syntax inside a fence).

**Files:**
- Modify: `plugins/voice-check/engine/document.py`
- Test: `plugins/voice-check/tests/test_document.py`

**Interfaces:**
- Consumes: `document.FENCE_RE` from Task 3, `document.Document` from Task 4.
- Produces:
  - `document.Suppression`, a frozen dataclass with `start: int`, `end: int`, `rules: frozenset`. An empty `rules` set means all rules.
  - `document.Suppression.covers(line: int, rule_name: str, rule_id: str) -> bool`.
  - `document.parse_suppressions(lines: list[str]) -> list[Suppression]`.
  - `Document.from_markdown` now populates `suppressions`.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_document.py`:

```python
def _sups(text):
    return document.parse_suppressions(text.splitlines())


def test_line_ignore_covers_only_its_own_line():
    s = _sups("a\nb <!-- voice-check: ignore -->\nc\n")
    assert len(s) == 1
    assert s[0].covers(2, "puffery", "puffery.groundbreaking")
    assert not s[0].covers(1, "puffery", "puffery.groundbreaking")
    assert not s[0].covers(3, "puffery", "puffery.groundbreaking")


def test_bare_directive_covers_every_rule():
    s = _sups("x <!-- voice-check: ignore -->\n")
    assert s[0].covers(1, "anything", "anything.at_all")


def test_directive_with_rule_name_covers_only_that_name():
    s = _sups("x <!-- voice-check: ignore puffery -->\n")
    assert s[0].covers(1, "puffery", "puffery.groundbreaking")
    assert not s[0].covers(1, "hedging", "hedging.would_like_to")


def test_directive_with_rule_id_covers_only_that_id():
    s = _sups("x <!-- voice-check: ignore puffery.crucial -->\n")
    assert s[0].covers(1, "other", "puffery.crucial")
    assert not s[0].covers(1, "other", "puffery.groundbreaking")


def test_directive_accepts_a_comma_separated_list():
    s = _sups("x <!-- voice-check: ignore puffery, hedging -->\n")
    assert s[0].covers(1, "puffery", "p.x")
    assert s[0].covers(1, "hedging", "h.x")
    assert not s[0].covers(1, "promotional_tone", "pt.x")


def test_disable_enable_pair_covers_the_block():
    s = _sups(
        "a\n<!-- voice-check: disable -->\nb\nc\n<!-- voice-check: enable -->\nd\n"
    )
    assert len(s) == 1
    assert s[0].covers(3, "puffery", "puffery.x")
    assert not s[0].covers(1, "puffery", "puffery.x")
    assert not s[0].covers(6, "puffery", "puffery.x")


def test_unterminated_disable_covers_to_end_of_file():
    s = _sups("a\n<!-- voice-check: disable -->\nb\nc\n")
    assert len(s) == 1
    assert s[0].covers(999999, "puffery", "puffery.x")
    assert not s[0].covers(1, "puffery", "puffery.x")


def test_directive_inside_a_fenced_block_has_no_effect():
    """rules.md documents this syntax in a fence; the example must be inert."""
    s = _sups("```\n<!-- voice-check: disable -->\n```\ntext\n")
    assert s == []


def test_document_from_markdown_populates_suppressions():
    doc = document.Document.from_markdown("x <!-- voice-check: ignore -->\n")
    assert len(doc.suppressions) == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q -k "ignore or disable or directive or suppressions"`
Expected: FAIL with `AttributeError: module 'document' has no attribute 'parse_suppressions'`

- [ ] **Step 3: Implement suppression parsing**

Append to `plugins/voice-check/engine/document.py`:

```python
import sys

DIRECTIVE_RE = re.compile(
    r"<!--\s*voice-check:\s*(ignore|disable|enable)\b([^>]*?)-->",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Suppression:
    """A line range in which some or all rules are suppressed.

    An empty `rules` set means every rule is suppressed. Otherwise a rule is
    suppressed when either its name or its id appears in the set.
    """

    start: int
    end: int
    rules: frozenset

    def covers(self, line: int, rule_name: str, rule_id: str) -> bool:
        if not (self.start <= line <= self.end):
            return False
        if not self.rules:
            return True
        return rule_name in self.rules or rule_id in self.rules


def _parse_rule_args(raw: str) -> frozenset:
    """Split a directive's argument list into rule names and ids."""
    parts = [p.strip() for p in re.split(r"[,\s]+", raw.strip()) if p.strip()]
    return frozenset(parts)


def parse_suppressions(lines):
    """Read voice-check directives from raw lines, skipping fenced regions.

    Runs on raw text because the masking pass hides HTML comments. Skips
    fenced blocks so a documented example of the syntax stays inert.
    """
    out = []
    open_disable = None
    in_fence = False

    for num, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for m in DIRECTIVE_RE.finditer(line):
            kind = m.group(1).lower()
            rule_args = _parse_rule_args(m.group(2))

            if kind == "ignore":
                out.append(Suppression(num, num, rule_args))
            elif kind == "disable":
                if open_disable is None:
                    open_disable = (num, rule_args)
            elif kind == "enable":
                if open_disable is not None:
                    out.append(Suppression(open_disable[0], num, open_disable[1]))
                    open_disable = None

    if open_disable is not None:
        out.append(Suppression(open_disable[0], sys.maxsize, open_disable[1]))

    return out
```

Move `import sys` to the top of the file alongside `import re`.

- [ ] **Step 4: Wire suppressions into Document.from_markdown**

In `Document.from_markdown`, replace `suppressions=[],` with:

```python
            # Parsed from raw text, before masking hides the HTML comments.
            suppressions=parse_suppressions(raw),
```

- [ ] **Step 5: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_document.py -q`
Expected: `32 passed`

- [ ] **Step 6: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `101 passed`

- [ ] **Step 7: Commit**

```bash
git add plugins/voice-check/engine/document.py plugins/voice-check/tests/test_document.py
git commit -m "feat(document): parse voice-check suppression directives

Supports three forms: a line scoped ignore, a disable and enable pair
covering a block, and an unterminated disable running to end of file. Each
accepts an optional list of rule names or rule ids.

Directives are read from raw text because masking hides HTML comments, and
fenced regions are skipped so a documented example stays inert.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Config module

Replace `supplement.py` with `config.py`, adding the three new block kinds and per line error reporting. The current bare `except Exception` in `voice_check.py` discards an entire supplement when one line is bad, which this task fixes.

**Files:**
- Create: `plugins/voice-check/engine/config.py`
- Delete: `plugins/voice-check/engine/supplement.py`
- Modify: `plugins/voice-check/engine/voice_check.py`
- Modify: `plugins/voice-check/tests/test_engine.py` (supplement tests move)
- Test: `plugins/voice-check/tests/test_config.py`

**Interfaces:**
- Consumes: `rules.RULES` from Task 2.
- Produces:
  - `config.Config`, a dataclass with `extra_rows: list`, `disabled: list` of `(identifier, glob_or_None)` tuples, `severity: dict`, `exclude: list`, `warnings: list`.
  - `config.Config.empty() -> Config`.
  - `config.Config.is_excluded(rel_path: str) -> bool`.
  - `config.Config.is_disabled(row: dict, rel_path: str) -> bool`.
  - `config.Config.severity_for(row: dict) -> str`.
  - `config.find_for(target: Path) -> Path | None`, same walk up behavior as the old `supplement.find_for`.
  - `config.load(path: Path) -> Config`.
  - `config.KNOWN_IDENTIFIERS: set[str]`, every rule name and rule id, used to warn on a stale disable or severity entry.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_config.py`:

```python
"""Tests for per repo configuration loading."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402


def _write(tmp_path, body):
    d = tmp_path / ".claude"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "voice-check.md"
    p.write_text(body)
    return p


def test_find_for_walks_up_to_git_root(tmp_path):
    (tmp_path / ".git").mkdir()
    _write(tmp_path, "")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    target = nested / "doc.md"
    target.write_text("hi")
    assert config.find_for(target) == tmp_path / ".claude" / "voice-check.md"


def test_find_for_returns_none_when_absent(tmp_path):
    (tmp_path / ".git").mkdir()
    target = tmp_path / "doc.md"
    target.write_text("hi")
    assert config.find_for(target) is None


def test_words_block_becomes_a_rule_row(tmp_path):
    p = _write(tmp_path, "```voice-check-words\nsynergy\n```\n")
    c = config.load(p)
    assert any(r["pattern"] == "synergy" and r["kind"] == "word" for r in c.extra_rows)


def test_phrases_and_regex_blocks_load(tmp_path):
    p = _write(
        tmp_path,
        "```voice-check-phrases\nmove the needle\n```\n"
        "```voice-check-regex\n\\bsynerg\\w+\\b\n```\n",
    )
    c = config.load(p)
    kinds = {r["kind"] for r in c.extra_rows}
    assert kinds == {"phrase", "regex"}


def test_disable_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-disable\npuffery.crucial\n```\n")
    c = config.load(p)
    assert ("puffery.crucial", None) in c.disabled


def test_disable_block_with_path_scope(tmp_path):
    p = _write(tmp_path, "```voice-check-disable\nvocab_2026 in docs/ref/**\n```\n")
    c = config.load(p)
    assert ("vocab_2026", "docs/ref/**") in c.disabled


def test_severity_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-severity\npuffery = low\n```\n")
    c = config.load(p)
    assert c.severity["puffery"] == "low"


def test_exclude_block_parsed(tmp_path):
    p = _write(tmp_path, "```voice-check-exclude\nCHANGELOG.md\n```\n")
    c = config.load(p)
    assert c.is_excluded("CHANGELOG.md")
    assert not c.is_excluded("README.md")


def test_exclude_glob_matches_nested_paths(tmp_path):
    p = _write(tmp_path, "```voice-check-exclude\ndocs/vendor/**\n```\n")
    c = config.load(p)
    assert c.is_excluded("docs/vendor/a/b.md")


def test_one_bad_line_does_not_discard_the_rest(tmp_path):
    """A single invalid regex must not take the whole supplement with it."""
    p = _write(
        tmp_path,
        "```voice-check-regex\n[unclosed\n```\n"
        "```voice-check-words\nsynergy\n```\n",
    )
    c = config.load(p)
    assert any(r["pattern"] == "synergy" for r in c.extra_rows)
    assert any("unclosed" in w for w in c.warnings)


def test_invalid_regex_is_dropped_with_a_warning(tmp_path):
    p = _write(tmp_path, "```voice-check-regex\n[unclosed\n```\n")
    c = config.load(p)
    assert c.extra_rows == []
    assert len(c.warnings) == 1


def test_bad_severity_level_warns_and_is_ignored(tmp_path):
    p = _write(tmp_path, "```voice-check-severity\npuffery = enormous\n```\n")
    c = config.load(p)
    assert "puffery" not in c.severity
    assert any("enormous" in w for w in c.warnings)


def test_severity_for_prefers_override_then_row_default():
    c = config.Config.empty()
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert c.severity_for(row) == "medium"
    c.severity["puffery"] = "low"
    assert c.severity_for(row) == "low"
    c.severity["puffery.crucial"] = "high"
    assert c.severity_for(row) == "high"


def test_is_disabled_matches_name_or_id():
    c = config.Config.empty()
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert not c.is_disabled(row, "a.md")
    c.disabled.append(("puffery", None))
    assert c.is_disabled(row, "a.md")


def test_path_scoped_disable_applies_only_inside_the_glob():
    c = config.Config.empty()
    c.disabled.append(("puffery", "docs/**"))
    row = {"name": "puffery", "id": "puffery.crucial", "severity": "medium"}
    assert c.is_disabled(row, "docs/a.md")
    assert not c.is_disabled(row, "src/a.md")


def test_comment_lines_inside_blocks_are_skipped(tmp_path):
    p = _write(tmp_path, "```voice-check-words\n# a note\nsynergy\n```\n")
    c = config.load(p)
    assert len(c.extra_rows) == 1


def test_unknown_rule_id_warns_but_still_records(tmp_path):
    """A stale disable must warn, never fail. Rule ids shift between versions."""
    p = _write(tmp_path, "```voice-check-disable\nno_such_rule.anywhere\n```\n")
    c = config.load(p)
    assert ("no_such_rule.anywhere", None) in c.disabled
    assert any("no_such_rule.anywhere" in w for w in c.warnings)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write config.py**

Create `plugins/voice-check/engine/config.py`:

```python
"""Load the rules that apply in this repo, and how loudly they report.

A supplement lives at `.claude/voice-check.md`, found by walking up from the
target file to the git root and stopping at the first match. Beyond prose the
skills read, the engine parses fenced blocks whose info string is one of:

    voice-check-words       one word per line, matched with word boundaries
    voice-check-phrases     one literal phrase per line, case insensitive
    voice-check-regex       one raw regex per line, case insensitive
    voice-check-disable     rule name or id, optionally "<rule> in <glob>"
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

import rules

RULE_KINDS = {
    "voice-check-phrases": "phrase",
    "voice-check-words": "word",
    "voice-check-regex": "regex",
}

SETTING_KINDS = {
    "voice-check-disable",
    "voice-check-severity",
    "voice-check-exclude",
}

# Every identifier a disable or severity entry may name. Supplement rules add
# their own names at scan time, so an unknown identifier warns rather than
# failing: rule ids shift between versions and a stale entry must not be fatal.
KNOWN_IDENTIFIERS = (
    {r["name"] for r in rules.RULES} | {r["id"] for r in rules.RULES}
)


@dataclass
class Config:
    extra_rows: List[dict] = field(default_factory=list)
    disabled: List[tuple] = field(default_factory=list)
    severity: dict = field(default_factory=dict)
    exclude: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "Config":
        return cls()

    def is_excluded(self, rel_path: str) -> bool:
        return any(fnmatch(rel_path, g) for g in self.exclude)

    def is_disabled(self, row: dict, rel_path: str) -> bool:
        for identifier, glob in self.disabled:
            if identifier not in (row["name"], row["id"]):
                continue
            if glob is None or fnmatch(rel_path, glob):
                return True
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

    if info == "voice-check-disable":
        parts = value.split(" in ", 1)
        identifier = parts[0].strip()
        glob = parts[1].strip() if len(parts) == 2 else None
        if not identifier:
            cfg.warnings.append(f"{where}: empty disable entry")
            return
        if identifier not in KNOWN_IDENTIFIERS:
            cfg.warnings.append(f"{where}: unknown rule {identifier!r}, disable has no effect")
        cfg.disabled.append((identifier, glob))
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_config.py -q`
Expected: `17 passed`

- [ ] **Step 5: Delete supplement.py and move its tests**

```bash
git rm plugins/voice-check/engine/supplement.py
```

In `plugins/voice-check/tests/test_engine.py`, delete these four tests, whose behavior is now covered by `test_config.py`:

- `test_find_supplement_walks_up_to_git_root`
- `test_find_supplement_returns_none_when_absent`
- `test_find_supplement_stops_at_git_root`
- `test_supplement_load_rows_parses_all_kinds`

Keep `test_supplement_rule_applied_from_fenced_block` and `test_supplement_phrase_block_applied`, which exercise end to end behavior through `voice_check.scan` and are still valid.

- [ ] **Step 6: Repoint voice_check.py at config**

In `plugins/voice-check/engine/voice_check.py`, replace `import supplement` with `import config`, and replace the body of `scan` with:

```python
def scan(file_path: Path) -> List[dict]:
    """Scan a file for writing rule violations. Return a list of findings."""
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8", errors="replace")

    cfg = config.Config.empty()
    cfg_path = config.find_for(file_path)
    if cfg_path is not None:
        cfg = config.load(cfg_path)

    return rules.scan_text(text, extra_rows=cfg.extra_rows)
```

The bare `except Exception` is gone: `config.load` handles its own errors per line and never raises.

- [ ] **Step 7: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `114 passed`

- [ ] **Step 8: Commit**

```bash
git add -A plugins/voice-check/engine plugins/voice-check/tests
git commit -m "feat(config): replace supplement.py, add disable, severity, exclude

Adds three fenced block kinds on top of the existing words, phrases, and
regex blocks. Every line is parsed on its own, so one bad entry is skipped
with a warning instead of discarding the whole supplement, which is what the
bare except Exception in voice_check.py used to do.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Scanner cutover

Move rule execution out of `rules.py` into `scanner.py`, running against a `Document` instead of raw text. This is the cutover: after it, masking, suppression, severity, and line ranges are all live.

Two behaviors need care. Suppression must filter document scope hits **before** the `doc_min` threshold check, otherwise a file level disable would not stop a cluster finding. And a document scope finding is reported under line ranges only when at least one of its occurrences falls inside a changed range.

**Files:**
- Create: `plugins/voice-check/engine/scanner.py`
- Modify: `plugins/voice-check/engine/rules.py` (delete `scan_text`, `_prepare_line_for_rules`, `_strip_code_blocks`, `_FENCE_RE`, `_BULLET_RE`, `_INLINE_CODE_RE`)
- Modify: `plugins/voice-check/engine/voice_check.py`
- Test: `plugins/voice-check/tests/test_scanner.py`

**Interfaces:**
- Consumes: `document.Document`, `document.Suppression` (Tasks 4 and 5); `config.Config` (Task 6); `rules.RULES`, `rules.compiled`, `rules.SEVERITY_ORDER` (Task 2).
- Produces:
  - `scanner.scan(doc, cfg, rel_path="", line_ranges=None) -> list[dict]`. Each finding is a dict with keys `rule`, `rule_id`, `severity`, `line`, `col`, `snippet`, `message`.
  - `scanner.in_ranges(line: int, line_ranges) -> bool`. A `line_ranges` of `None` means every line qualifies.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_scanner.py`:

```python
"""Tests for the scanner: suppression, severity, and line range behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402
import document  # noqa: E402
import scanner  # noqa: E402


def _scan(text, cfg=None, rel_path="a.md", line_ranges=None):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg or config.Config.empty(), rel_path, line_ranges)


def test_findings_carry_rule_id_and_severity():
    f = _scan("The plan is simple — ship it.\n")
    assert len(f) == 1
    assert f[0]["rule"] == "no_dashes"
    assert f[0]["rule_id"] == "no_dashes.em_en"
    assert f[0]["severity"] == "high"


def test_snippet_quotes_the_raw_line_not_the_masked_line():
    f = _scan("a `x` b — c\n")
    assert f[0]["snippet"] == "a `x` b — c"


def test_mention_inside_short_quotes_is_not_flagged():
    assert _scan('avoid "groundbreaking," in copy\n') == []


def test_use_outside_quotes_is_still_flagged():
    f = _scan("our groundbreaking platform\n")
    assert any(x["rule"] == "puffery" for x in f)


def test_line_ignore_directive_suppresses_that_line():
    text = "our groundbreaking platform <!-- voice-check: ignore -->\n"
    assert _scan(text) == []


def test_line_ignore_with_rule_name_suppresses_only_that_rule():
    text = "a — b groundbreaking <!-- voice-check: ignore puffery -->\n"
    f = _scan(text)
    names = {x["rule"] for x in f}
    assert "puffery" not in names
    assert "no_dashes" in names


def test_doc_scope_hits_inside_a_suppressed_range_do_not_count():
    """A file level disable must stop the cluster finding, not just hide it."""
    text = (
        "<!-- voice-check: disable -->\n"
        "additionally the key landscape is pivotal\n"
    )
    assert _scan(text) == []


def test_doc_scope_fires_when_hits_are_not_suppressed():
    f = _scan("additionally the key landscape is pivotal\n")
    assert any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_config_disable_removes_a_rule_by_name():
    cfg = config.Config.empty()
    cfg.disabled.append(("puffery", None))
    assert _scan("our groundbreaking platform\n", cfg) == []


def test_config_disable_removes_a_single_row_by_id():
    cfg = config.Config.empty()
    cfg.disabled.append(("puffery.groundbreaking", None))
    assert _scan("our groundbreaking platform\n", cfg) == []
    assert _scan("a renowned author\n", cfg) != []


def test_config_severity_override_applies():
    cfg = config.Config.empty()
    cfg.severity["puffery"] = "high"
    f = _scan("our groundbreaking platform\n", cfg)
    assert f[0]["severity"] == "high"


def test_line_scope_findings_outside_ranges_are_dropped():
    text = "a — b\nc — d\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert len(f) == 1
    assert f[0]["line"] == 2


def test_doc_scope_reported_when_an_occurrence_is_inside_a_range():
    text = "plain line\nadditionally the key landscape is pivotal\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_doc_scope_dropped_when_every_occurrence_is_outside_the_ranges():
    text = "additionally the key landscape is pivotal\nplain line\n"
    f = _scan(text, line_ranges=[(2, 2)])
    assert not any(x["rule"] == "ai_vocab_cluster" for x in f)


def test_in_ranges_treats_none_as_everything():
    assert scanner.in_ranges(5, None) is True
    assert scanner.in_ranges(5, [(1, 3)]) is False
    assert scanner.in_ranges(2, [(1, 3)]) is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_scanner.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner'`

- [ ] **Step 3: Write scanner.py**

Create `plugins/voice-check/engine/scanner.py`:

```python
"""Run rule rows against a Document and produce findings.

The only module that knows about both rules and documents. Applies, in order:
row selection from config, line scope matching, document scope aggregation,
suppression, severity tagging, and line range filtering.
"""
from typing import Dict, List, Optional

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
                hits.append((row["pattern"], hit_line))

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

    return findings
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_scanner.py -q`
Expected: `15 passed`

- [ ] **Step 5: Repoint voice_check.scan at the scanner**

In `plugins/voice-check/engine/voice_check.py`, add `import document`, `import scanner` alongside the existing imports, and replace `scan` with:

```python
def scan(file_path: Path, line_ranges=None) -> List[dict]:
    """Scan a file for writing rule violations. Return a list of findings."""
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8", errors="replace")

    cfg = config.Config.empty()
    cfg_path = config.find_for(file_path)
    if cfg_path is not None:
        cfg = config.load(cfg_path)

    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg, rel_path=_rel_path(file_path), line_ranges=line_ranges)


def _rel_path(file_path: Path) -> str:
    """Path relative to the git root, for matching config globs.

    Falls back to the file name when no git root is found.
    """
    current = file_path.resolve().parent
    while True:
        if (current / ".git").exists():
            try:
                return file_path.resolve().relative_to(current).as_posix()
            except ValueError:
                break
        if current.parent == current:
            break
        current = current.parent
    return file_path.name
```

- [ ] **Step 6: Delete the moved code from rules.py**

Delete from `plugins/voice-check/engine/rules.py`: `scan_text`, `_prepare_line_for_rules`, `_strip_code_blocks`, `_FENCE_RE`, `_BULLET_RE`, and `_INLINE_CODE_RE`. Keep `_compile`, `_row_key`, `_COMPILED_CACHE`, `compiled`, `slug`, `_finalize`, `RULES`, `SEVERITY_ORDER`, `DEFAULT_SEVERITY`, and `_SEVERITY_BY_NAME`.

Update the module docstring's row schema block to document the two new fields:

```
    id:       str, globally unique stable identifier, "<name>.<slug>"
    severity: "high" | "medium" | "low", used for display filtering only
```

- [ ] **Step 7: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `129 passed`

If `test_engine.py` tests fail because they assert exact finding counts that masking has now changed, update those assertions rather than reverting masking. Record any such change in the commit message.

- [ ] **Step 8: Commit**

```bash
git add -A plugins/voice-check/engine plugins/voice-check/tests
git commit -m "feat(scanner): run rules against a masked Document

Moves rule execution out of rules.py into scanner.py, running against a
Document rather than raw text. Masking, suppression, config disabling,
severity tagging, and line range filtering are all live after this commit.

Suppression filters document scope hits before the doc_min threshold check,
so a file level disable stops a cluster finding rather than hiding it. A
document scope finding survives line range filtering when at least one of
its occurrences falls inside a changed range.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: CLI flags and error handling

Add `--min-severity` and `--lines`, the severity collapse line, config warning output, and the error handling contract from the spec.

**Files:**
- Modify: `plugins/voice-check/engine/voice_check.py`
- Test: `plugins/voice-check/tests/test_engine.py`

**Interfaces:**
- Consumes: `scanner.scan`, `config.load`, `rules.SEVERITY_ORDER`.
- Produces:
  - `voice_check.parse_ranges(raw: str) -> list[tuple[int, int]] | None`. Returns `None` on malformed input.
  - `voice_check.format_findings(findings: list[dict], min_severity: str = "medium") -> str`.
  - CLI accepting `--report-only`, `--min-severity {high,medium,low}` defaulting to `medium`, and `--lines RANGES`.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_engine.py`:

```python
import subprocess  # noqa: E402

ENGINE = str(Path(__file__).parent.parent / "engine" / "voice_check.py")


def _cli(*args):
    return subprocess.run(
        [sys.executable, ENGINE, *args],
        capture_output=True, text=True,
    )


def test_parse_ranges_reads_a_comma_separated_list():
    assert voice_check.parse_ranges("12-18,40-41") == [(12, 18), (40, 41)]


def test_parse_ranges_accepts_a_single_line():
    assert voice_check.parse_ranges("7") == [(7, 7)]


def test_parse_ranges_returns_none_on_garbage():
    assert voice_check.parse_ranges("not-a-range") is None
    assert voice_check.parse_ranges("") is None


def test_high_severity_finding_prints_in_full(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("The plan is simple — ship it.\n")
    out = _cli("--report-only", str(f))
    assert out.returncode == 0
    assert "no_dashes" in out.stdout
    assert "line 1" in out.stdout


def test_low_severity_finding_collapses_by_default(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("additionally the key landscape is pivotal\n")
    out = _cli("--report-only", str(f))
    assert "below medium severity" in out.stdout
    assert "ai_vocab_cluster" in out.stdout
    assert "occurrences across" not in out.stdout


def test_min_severity_low_prints_everything(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("additionally the key landscape is pivotal\n")
    out = _cli("--report-only", "--min-severity", "low", str(f))
    assert "occurrences across" in out.stdout
    assert "below medium severity" not in out.stdout


def test_min_severity_high_collapses_medium_findings(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("our groundbreaking platform\n")
    out = _cli("--report-only", "--min-severity", "high", str(f))
    assert "below high severity" in out.stdout
    assert "Show importance through specifics" not in out.stdout


def test_lines_flag_restricts_line_scope_findings(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("a — b\nc — d\n")
    out = _cli("--report-only", "--lines", "2-2", str(f))
    assert "line 2" in out.stdout
    assert "line 1" not in out.stdout


def test_malformed_lines_flag_warns_and_scans_whole_file(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("a — b\nc — d\n")
    out = _cli("--report-only", "--lines", "garbage", str(f))
    assert out.returncode == 0
    assert "line 1" in out.stdout
    assert "line 2" in out.stdout
    assert "garbage" in out.stderr


def test_non_utf8_file_does_not_crash(tmp_path):
    f = tmp_path / "d.md"
    f.write_bytes(b"\xff\xfe binary junk \x00\x01\n")
    out = _cli("--report-only", str(f))
    assert out.returncode == 0


def test_config_warnings_print_to_stderr(tmp_path):
    (tmp_path / ".git").mkdir()
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "voice-check.md").write_text("```voice-check-regex\n[unclosed\n```\n")
    f = tmp_path / "d.md"
    f.write_text("plain text\n")
    out = _cli("--report-only", str(f))
    assert out.returncode == 0
    assert "unclosed" in out.stderr


def test_missing_file_exits_two():
    out = _cli("--report-only", "/nonexistent/nope.md")
    assert out.returncode == 2


def test_clean_file_prints_nothing_and_exits_zero(tmp_path):
    f = tmp_path / "c.md"
    f.write_text("The plan is simple. Ship it. Iterate on real usage.\n")
    out = _cli("--report-only", str(f))
    assert out.returncode == 0
    assert out.stdout.strip() == ""
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_engine.py -q -k "parse_ranges or severity or lines_flag or non_utf8 or config_warnings"`
Expected: FAIL with `AttributeError: module 'voice_check' has no attribute 'parse_ranges'`

- [ ] **Step 3: Rewrite voice_check.py**

Replace the whole of `plugins/voice-check/engine/voice_check.py` with:

```python
"""voice-check rules engine. Deterministic checks for the pre-commit hook path.

Always advisory: under --report-only this program exits 0 in every case,
including on malformed configuration, unreadable files, and unexpected
exceptions. Every degradation path falls toward reporting more, never toward
silently reporting less.
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_engine.py -q`
Expected: all pass

- [ ] **Step 5: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `142 passed`

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/engine/voice_check.py plugins/voice-check/tests/test_engine.py
git commit -m "feat(cli): min severity, line ranges, and the error contract

Adds --min-severity (default medium) which collapses lower severity findings
to a single count line rather than hiding them, and --lines for diff scoped
reporting. Config warnings print to stderr.

Reads files as utf-8 with errors=replace so a binary file cannot raise, and
catches unexpected exceptions under --report-only so a commit is never
blocked. Without --report-only the exception still raises, so debugging works.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Hook diff scoping

Teach the installed hook to compute changed line ranges from the staged diff and pass them to the engine.

**Files:**
- Modify: `plugins/voice-check/templates/pre-commit.sh`
- Test: `plugins/voice-check/tests/test_hook_pipeline.py`

**Interfaces:**
- Consumes: the `--lines` flag from Task 8.
- Produces: no code interface. The hook contract markers are unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_hook_pipeline.py`. Reuse the module's existing `_init_repo`, `_run_installer`, `_git_env`, and `_hook_path` helpers.

```python
def test_hook_reports_only_on_changed_lines(tmp_path, fresh_repo, fake_home):
    """A pre-existing violation elsewhere in the file must stay quiet."""
    _run_installer(fresh_repo, fake_home)

    doc = fresh_repo / "doc.md"
    doc.write_text("old line with an em dash — here\nsecond line\n")
    subprocess.run(["git", "add", "doc.md"], cwd=fresh_repo, check=True, env=_git_env())
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed", "--no-verify"],
        cwd=fresh_repo, check=True, env=_git_env(),
    )

    # Touch only the second line, introducing a fresh violation there.
    doc.write_text("old line with an em dash — here\nsecond line — changed\n")
    subprocess.run(["git", "add", "doc.md"], cwd=fresh_repo, check=True, env=_git_env())

    out = subprocess.run(
        ["git", "commit", "-m", "edit"],
        cwd=fresh_repo, capture_output=True, text=True, env=_git_env(),
    )
    assert out.returncode == 0, "hook must never block a commit"
    combined = out.stdout + out.stderr
    assert "line 2" in combined
    assert "line 1" not in combined


def test_hook_still_exits_zero_when_git_diff_produces_no_ranges(tmp_path, fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    doc = fresh_repo / "doc.md"
    doc.write_text("clean prose here\n")
    subprocess.run(["git", "add", "doc.md"], cwd=fresh_repo, check=True, env=_git_env())
    out = subprocess.run(
        ["git", "commit", "-m", "clean"],
        cwd=fresh_repo, capture_output=True, text=True, env=_git_env(),
    )
    assert out.returncode == 0
```

If `fresh_repo` and `fake_home` are not already pytest fixtures in this file, define them from the existing helpers at the top of the file:

```python
@pytest.fixture
def fresh_repo(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    return repo


@pytest.fixture
def fake_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -q -k "changed_lines or no_ranges"`
Expected: FAIL, because `line 1` still appears in the output

- [ ] **Step 3: Add range computation to the hook template**

In `plugins/voice-check/templates/pre-commit.sh`, replace the scanning loop (from `findings_total=0` through the `done <<< "$staged_md"` line) with:

```bash
findings_total=0

# Extract the added-line ranges for one staged file from its diff hunks.
# Prints "12-18,40-41" or nothing. Falls back to nothing on any failure, and
# an empty result means the whole file is scanned.
changed_ranges() {
  git diff --cached -U0 -- "$1" 2>/dev/null | awk '
    /^@@/ {
      if (match($0, /\+[0-9]+(,[0-9]+)?/)) {
        spec = substr($0, RSTART + 1, RLENGTH - 1)
        split(spec, a, ",")
        start = a[1]
        len = (a[2] == "" ? 1 : a[2])
        if (len > 0) printf "%s-%s,", start, start + len - 1
      }
    }
  ' | sed 's/,$//'
}

while IFS= read -r f; do
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    continue
  fi

  ranges=$(changed_ranges "$f")
  if [ -n "$ranges" ]; then
    out=$("$PYTHON" "$ENGINE" --report-only --lines "$ranges" "$f" 2>&1 || true)
  else
    out=$("$PYTHON" "$ENGINE" --report-only "$f" 2>&1 || true)
  fi

  if [ -n "$out" ]; then
    echo "--- $f ---"
    echo "$out"
    findings_total=$((findings_total + 1))
  fi
done <<< "$staged_md"
```

The `set -e` at the top of the hook does not apply inside a command substitution whose result is tested, and every engine invocation is already guarded with `|| true`, so a failure in `changed_ranges` degrades to a whole file scan rather than aborting the hook.

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -q`
Expected: all pass

- [ ] **Step 5: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `144 passed`

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/templates/pre-commit.sh plugins/voice-check/tests/test_hook_pipeline.py
git commit -m "feat(hook): report only on lines the commit actually changed

The hook now derives added line ranges from git diff --cached -U0 and passes
them to the engine as --lines. Editing one line of a document no longer
surfaces that document's entire violation history.

Any failure computing ranges degrades to a whole file scan, and the hook
still exits 0 in every case.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Regression fixtures and the self scan test

Encode the defects found while writing the spec as permanent tests, and make the repo scan its own documentation in CI.

**Files:**
- Create: `plugins/voice-check/tests/fixtures/technical.md`
- Create: `plugins/voice-check/tests/fixtures/mentions.md`
- Create: `plugins/voice-check/tests/test_regressions.py`
- Modify: `plugins/voice-check/references/rules.md` (add its suppression directive)

**Interfaces:**
- Consumes: `voice_check.scan` from Task 8.
- Produces: no code interface.

- [ ] **Step 1: Create the technical prose fixture**

Create `plugins/voice-check/tests/fixtures/technical.md`:

```markdown
# API Setup

Set your API key in the environment. The key is read at startup.
Align the config with the schema below. Additionally, set the region.
```

- [ ] **Step 2: Create the mentions fixture**

Create `plugins/voice-check/tests/fixtures/mentions.md`:

```markdown
# Style Notes

The style guide says to avoid "groundbreaking" and "pivotal" in copy.

Hedging language ("would like to," "could potentially," "it is worth noting")
is banned, as is copula avoidance ("serves as," "stands as").

> Our product is groundbreaking.

See https://example.com/state-of-the-art-review for details.

Inline mentions of `key`, `align`, and `additionally` are code, not prose.
```

- [ ] **Step 3: Write the failing tests**

Create `plugins/voice-check/tests/test_regressions.py`:

```python
"""Regression tests built from defects found while specifying Phase 1.

Each case is a real failure observed against the pre Phase 1 engine, not a
synthetic approximation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import voice_check  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent.parent
PLUGIN_ROOT = Path(__file__).parent.parent


def _names(findings):
    return sorted({f["rule"] for f in findings})


def test_technical_prose_does_not_trip_the_vocabulary_cluster():
    """API key, the key is read, Align the config, Additionally."""
    findings = voice_check.scan(FIXTURES / "technical.md")
    assert findings == [], _names(findings)


def test_quoted_mentions_and_urls_are_not_flagged():
    findings = voice_check.scan(FIXTURES / "mentions.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_readme():
    findings = voice_check.scan(REPO_ROOT / "README.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_rule_list():
    findings = voice_check.scan(PLUGIN_ROOT / "references" / "rules.md")
    assert findings == [], _names(findings)


def test_engine_reports_nothing_on_its_own_spec():
    spec = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-09-07-signal-quality-design.md"
    findings = voice_check.scan(spec)
    assert findings == [], _names(findings)


def test_doc_scope_ignores_words_inside_inline_code():
    """Defect 6: doc scope used to skip inline code masking."""
    import document
    import config
    import scanner

    doc = document.Document.from_markdown("uses `key` and `align` and `additionally`\n")
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    assert findings == []


def test_line_scope_and_doc_scope_see_identical_text():
    """The two scopes must never drift apart again."""
    import document

    src = "a `key` b\n> quoted line\nplain text with align\n"
    doc = document.Document.from_markdown(src)
    assert doc.prose_text == "\n".join(doc.scan_lines)
```

- [ ] **Step 4: Run to verify the state of each case**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_regressions.py -q`

Expected: the fixture and inline code tests pass. `test_engine_reports_nothing_on_its_own_rule_list` fails, because `rules.md` lists banned vocabulary unquoted and no masking heuristic should catch that. This is the case the spec assigns to suppression.

- [ ] **Step 5: Add the suppression directive to rules.md**

In `plugins/voice-check/references/rules.md`, wrap the vocabulary listing sections in a suppression range. Put this line immediately before the `## AI Vocabulary Cluster` heading:

```markdown
<!-- voice-check: disable ai_vocab_cluster, puffery, promotional_tone, vocab_2026, bridge_phrases, hedging, vague_attribution, dangling_participle -->
```

and this line immediately after the end of the `## Markup Artifacts` section, before `## Per-repo supplements`:

```markdown
<!-- voice-check: enable -->
```

This file lists banned words as its subject matter, so suppressing the rules that match its own examples is correct rather than a workaround.

- [ ] **Step 6: Run the regression tests again**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_regressions.py -q`
Expected: `7 passed`

If `README.md` or the spec still report findings, add a targeted `<!-- voice-check: ignore -->` to the offending line rather than widening the masking rules. Note in the commit message which lines needed it.

- [ ] **Step 7: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `151 passed`

- [ ] **Step 8: Commit**

```bash
git add plugins/voice-check/tests plugins/voice-check/references/rules.md
git commit -m "test: regression fixtures and a self scan of the repo docs

Encodes the defects found while writing the spec: technical prose tripping
the vocabulary cluster, quoted mentions and URLs being flagged, and document
scope rules skipping inline code.

The self scan asserts the engine reports nothing on this repo's README, rule
list, and Phase 1 spec, which puts the question of whether the tool trusts
its own documentation into CI. rules.md carries a suppression range, since
listing banned vocabulary is its subject matter.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Documentation, skills, and version bump

Bring the prose in line with the code. The skills need a real behavioral change: severity collapsing makes "zero findings" ambiguous, so both skills must ask for every finding.

**Files:**
- Modify: `plugins/voice-check/skills/voice-check/SKILL.md`
- Modify: `plugins/voice-check/skills/writing-guard/SKILL.md`
- Modify: `plugins/voice-check/references/rules.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `plugins/voice-check/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: everything above.
- Produces: no code interface.

- [ ] **Step 1: Update both skills to request every finding**

In `plugins/voice-check/skills/voice-check/SKILL.md`, change the Step 2 command to:

```bash
python3 ../../engine/voice_check.py --report-only --min-severity low <target-file>
```

Add this sentence after that code block:

> `--min-severity low` is required. Without it the engine collapses lower severity findings into a summary line, and Step 4 could not tell a clean file from a quiet one.

Apply the same change to step 5 of `plugins/voice-check/skills/writing-guard/SKILL.md`.

- [ ] **Step 2: Document the new syntax in rules.md**

In the `## Per-repo supplements` section of `plugins/voice-check/references/rules.md`, extend the block kind list:

```
voice-check-words      one word per line, matched with word boundaries
voice-check-phrases    one literal phrase per line, matched case-insensitive
voice-check-regex      one raw regex per line, matched case-insensitive
voice-check-disable    rule name or id, optionally "<rule> in <path glob>"
voice-check-severity   "<rule name or id> = high|medium|low"
voice-check-exclude    one path glob per line, skipped entirely
```

Add a new section documenting suppression. Keep the examples inside a fenced block, which is exactly why directive parsing skips fences:

````markdown
## Suppression directives

Any file can suppress rules inline with an HTML comment, which stays
invisible in rendered markdown:

```
<!-- voice-check: ignore -->                 suppress this line
<!-- voice-check: ignore puffery -->         suppress one rule on this line
<!-- voice-check: disable -->                suppress from here on
<!-- voice-check: enable -->                 resume after a disable
```

Arguments accept a rule name, which covers every row under that name, or a
single rule id such as `puffery.crucial`. A comma separated list works too.
A `disable` with no matching `enable` runs to the end of the file.

Directives inside fenced code blocks have no effect, so the examples above
are inert.
````

- [ ] **Step 3: Update the README**

In `README.md`, add a section after "Layered rules: per-repo supplements":

````markdown
## Severity and noise control

Every rule carries a severity. `no_dashes` and `markup_artifacts` are high,
`ai_vocab_cluster` is low, everything else is medium.

The engine defaults to `--min-severity medium`. Findings below the threshold
collapse into one summary line rather than disappearing:

```
1 finding below medium severity (ai_vocab_cluster). Re-run with --min-severity low for detail.
```

A repo can override any rule's severity in its supplement, disable rules by
name or id, and exclude paths entirely. See `references/rules.md`.

## Mentions versus uses

The engine masks text that is not prose before matching: fenced code, inline
code, YAML frontmatter, HTML comments, URLs, markdown link targets,
blockquotes, and double quoted spans under six words. Writing about a banned
word in quotes no longer trips the rule that bans it.

Single quotes never mask, because apostrophes make them ambiguous.

## Only what you changed

The pre-commit hook derives changed line ranges from `git diff --cached -U0`
and reports only on those lines. Editing one line of an old document does not
surface that document's whole history. A vocabulary cluster is reported when
at least one of its occurrences falls on a changed line.
````

Also update the "What it catches" bullets to mention that rules are now identified as `<name>.<slug>` and can be disabled individually.

- [ ] **Step 4: Update CLAUDE.md**

In `/Users/ryan/voice-check/CLAUDE.md`, replace the Python engine paragraph in the Architecture section with:

```markdown
3. **Python engine** (`plugins/voice-check/engine/`): five modules with an
   acyclic dependency graph. `voice_check.py` is the CLI entry
   (`--report-only` for hook mode, `--min-severity` for verbosity, `--lines`
   for diff scoping, always exits 0, advisory). `document.py` decides what
   text is prose, producing length preserving masked lines plus suppression
   directives parsed from the raw text. `config.py` finds `.claude/voice-check.md`
   by walking up to the git root (first match wins, no aggregation) and parses
   six fenced block kinds. `rules.py` holds the rule table, where every row has
   a stable id and a severity. `scanner.py` runs rows against a document and
   applies suppression, severity, and line ranges.
```

Update the test count line in the Commands section to match the final number from Task 10, and change the pytest invocation to `tests/` rather than `tests/test_engine.py`.

- [ ] **Step 5: Bump the version**

In `plugins/voice-check/.claude-plugin/plugin.json`, change `"version": "2.2.2"` to `"version": "2.3.0"`. This is a feature release: new flags, new config kinds, and new suppression syntax, with no breaking change to the hook contract.

- [ ] **Step 6: Verify the docs pass their own engine**

Run:

```bash
cd /Users/ryan/voice-check && for f in README.md CLAUDE.md plugins/voice-check/references/rules.md plugins/voice-check/skills/voice-check/SKILL.md plugins/voice-check/skills/writing-guard/SKILL.md; do
  echo "### $f"
  python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low "$f"
done
```

Expected: no output under any heading. Fix any finding in the prose rather than suppressing it, unless the finding is a genuine mention that masking should have caught, in which case widen the masking and add a test.

- [ ] **Step 7: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `151 passed`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: severity, suppression, masking, and diff scoping; bump to 2.3.0

Both skills now invoke the engine with --min-severity low, because severity
collapsing would otherwise make 'zero findings' ambiguous in their re-run
loops.

Documents the three new supplement block kinds and the suppression directive
syntax, with the examples inside a fenced block so they stay inert.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Verification Checklist

Run this after Task 11. Every line must hold before Phase 1 is done.

- [ ] `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q` reports all passing, roughly 151 tests
- [ ] `python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low README.md` prints nothing
- [ ] The same command prints nothing for `plugins/voice-check/references/rules.md` and the Phase 1 spec
- [ ] `grep -rn 'supplement' plugins/voice-check/engine/` returns no import of the deleted module
- [ ] A staged edit to one line of a file with older violations elsewhere reports only the edited line
- [ ] `git commit` in a repo with the hook installed exits 0 even with a deliberately broken `.claude/voice-check.md`
- [ ] Every spec success criterion (1 through 9) has a passing test behind it

## Spec Coverage

| Spec requirement | Task |
| --- | --- |
| Mention versus use masking | 3, 4 |
| Quoted span policy, double quotes only, six word limit | 4 |
| Suppression directives, three forms | 5 |
| Directives skip fenced regions | 5 |
| Stable per row rule identity | 2 |
| Default severity assignments | 2 |
| Dead shim removal | 2 |
| Per repo disable, severity, exclude | 6 |
| Supplement per line error handling | 6 |
| Document scope masking (defect 6) | 4, 10 |
| Suppression filters doc scope hits before threshold | 7 |
| Diff scoping, line scope | 7, 9 |
| Diff scoping, document scope semantics | 7 |
| Severity display and collapse line | 8 |
| Encoding, malformed flags, exception contract | 8 |
| Regression fixtures | 10 |
| Self scan test | 10 |
| Skill `--min-severity low` change | 11 |
| Documentation and version bump | 11 |
| CI runs the whole suite | 1 |
| Red suite prerequisite | 1 |
