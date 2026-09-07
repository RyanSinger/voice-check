# Structural Detection (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the always-on pre-commit hook to catch structural AI writing tells, which it currently misses entirely, by adding five syntactic frames as rule rows and one computed analyzer for mechanical bold headers.

**Architecture:** Five frames are ordinary line-scope regex rows in the existing table, so they need no new machinery. The bold header rule needs a ratio rather than a count, which no rule row can express, so a new `analyzers.py` module holds functions that compute over a document. Analyzer registry entries share the rule row contract (`name`, `id`, `category`, `severity`), which is what lets Phase 1's disable, severity, suppression, and diff scoping apply to them without changing those modules.

**Tech Stack:** Python 3.11 or later, standard library only. pytest for tests.

**Spec:** `docs/superpowers/specs/2026-09-07-structural-detection-design.md`

## Global Constraints

- The engine imports from the Python standard library only. No new runtime dependencies.
- Python 3.11 or later.
- The pre-commit hook is advisory and **always exits 0**.
- The `# === voice-check section start ===` / `# === voice-check section end ===` hook contract is preserved exactly.
- **No dashes in any prose output**, including commit messages, documentation, code comments, and test docstrings. Em dashes, en dashes, and hyphens used as separators are all banned. Use commas, periods, colons, or parentheses. Hyphens inside compound words are fine.
- Structural rules carry `name: "structure"` and default to `low` severity.
- Every regex row carries an explicit `id` and a `term`. A raw pattern must never reach a developer's terminal.

## Working Directory

All paths are relative to the repository root unless stated otherwise. Test commands run from `plugins/voice-check`.

Set up the virtualenv once if it does not exist:

```bash
cd plugins/voice-check
python3 -m venv .venv
.venv/bin/pip install pytest
```

Run the full suite with:

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

**Baseline: 160 tests passing.**

## File Structure

**Created:**

- `plugins/voice-check/engine/analyzers.py`: functions that compute over a document rather than matching against it. Owns the `ANALYZERS` registry and `mechanical_bold_headers`.
- `plugins/voice-check/tests/test_structure.py`: the five frames, positives and negatives, plus the calibration regression test.
- `plugins/voice-check/tests/test_analyzers.py`: the analyzer in isolation and its integration with Phase 1's controls.

**Modified:**

- `plugins/voice-check/engine/rules.py`: six new frame rows, and `structure` added to the severity map.
- `plugins/voice-check/engine/scanner.py`: a third pass running the analyzer registry.
- `plugins/voice-check/engine/config.py`: `KNOWN_IDENTIFIERS` unions the analyzer registry.
- `plugins/voice-check/references/rules.md`: retag five bullets, record the rhythm result, extend the suppression range.
- `plugins/voice-check/references/examples.md` and `references/wikipedia-signs.md`: suppression ranges.
- `docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md`: suppression range.
- `README.md`, `CLAUDE.md`, `plugins/voice-check/.claude-plugin/plugin.json`.

---

### Task 1: The five syntactic frames

Six line-scope regex rows. No new machinery: these are rows in a table that already exists, with ids and severities that already work.

**Files:**
- Modify: `plugins/voice-check/engine/rules.py`
- Modify: `plugins/voice-check/references/rules.md`, `references/examples.md`, `references/wikipedia-signs.md`, `docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md`
- Test: `plugins/voice-check/tests/test_structure.py`

**Interfaces:**
- Consumes: `rules.RULES` and `rules._SEVERITY_BY_NAME` from the shipped engine; `scanner.scan(doc, cfg, rel_path, line_ranges)`; `document.Document.from_markdown(text)`; `config.Config.empty()`.
- Produces: six rows in `rules.RULES` with `name: "structure"` and ids `structure.not_just_but`, `structure.not_about_but_about`, `structure.while_also`, `structure.advantages_disadvantages`, `structure.despite_faces_challenges`, `structure.false_range`.

**A warning about step order.** Adding these rows makes `references/rules.md` fire, which breaks the existing self scan test in `tests/test_regressions.py`. That is expected and Step 5 fixes it. Do not panic when a previously green test goes red at Step 4, and do not weaken the self scan test to compensate.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_structure.py`:

```python
"""Tests for the structural frame rules.

Frames match sentence shapes rather than words, so they fire on legitimate
prose more readily than a vocabulary rule does. The negative cases matter
more than the positives here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import config  # noqa: E402
import document  # noqa: E402
import scanner  # noqa: E402


def _ids(text):
    doc = document.Document.from_markdown(text)
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    return {f["rule_id"] for f in findings}


def test_negative_parallelism_fires():
    assert "structure.not_just_but" in _ids(
        "Our platform is not just a tool, it is a partner.\n"
    )


def test_not_only_but_also_fires():
    """"Not only X but Y" is the same construction and should fire."""
    assert "structure.not_just_but" in _ids("He was not only tired but hungry.\n")


def test_plain_not_just_stays_silent():
    assert "structure.not_just_but" not in _ids(
        "I could not just sit there and watch.\n"
    )


def test_contrast_reframe_fires():
    assert "structure.not_about_but_about" in _ids(
        "It's not about the tooling, it's about the culture.\n"
    )


def test_single_negation_stays_silent():
    assert "structure.not_about_but_about" not in _ids("It's not about money.\n")


def test_balanced_debate_concessive_fires():
    assert "structure.while_also" in _ids(
        "While the approach has merit, it also carries risk.\n"
    )


def test_ordinary_while_clause_stays_silent():
    assert "structure.while_also" not in _ids(
        "While the tests ran, we reviewed the diff.\n"
    )


def test_advantages_disadvantages_fires():
    assert "structure.advantages_disadvantages" in _ids(
        "The framework has clear advantages and some disadvantages.\n"
    )


def test_benefits_alone_stays_silent():
    assert "structure.advantages_disadvantages" not in _ids(
        "The benefits are clear and worth the effort.\n"
    )


def test_challenges_and_prospects_fires():
    assert "structure.despite_faces_challenges" in _ids(
        "Despite its strong adoption, the framework faces challenges ahead.\n"
    )


def test_ordinary_concessive_stays_silent():
    """Requires all three beats, so a plain "despite" sentence is quiet."""
    assert "structure.despite_faces_challenges" not in _ids(
        "Despite budget challenges, we shipped on time.\n"
    )


def test_false_range_fires_on_plural_to_plural():
    assert "structure.false_range" in _ids(
        "We serve everyone from startups to enterprises.\n"
    )


def test_ordinary_ranges_stay_silent():
    """"From X to Y" is ordinary English. Only plural to plural fires."""
    for text in (
        "We work from 9 to 5 most days.\n",
        "She walked from the store to home.\n",
        "Copy the file from src to dist.\n",
        "The value went from 3 to 7.\n",
    ):
        assert "structure.false_range" not in _ids(text), text


def test_frames_are_low_severity():
    doc = document.Document.from_markdown(
        "Our platform is not just a tool, it is a partner.\n"
    )
    findings = scanner.scan(doc, config.Config.empty(), "a.md")
    frame = [f for f in findings if f["rule"] == "structure"]
    assert frame and all(f["severity"] == "low" for f in frame)


def test_frame_messages_never_show_a_raw_pattern():
    """Regex rows carry a "term" so the developer never reads a pattern."""
    import rules
    for row in rules.RULES:
        if row["name"] != "structure":
            continue
        assert "term" in row, row["id"]
        assert "\\b" not in row["message"], row["id"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_structure.py -q`
Expected: the positive tests FAIL (no `structure` rules exist yet); the negative tests pass vacuously.

- [ ] **Step 3: Register the severity**

In `plugins/voice-check/engine/rules.py`, add one entry to `_SEVERITY_BY_NAME`:

```python
_SEVERITY_BY_NAME = {
    "no_dashes": "high",
    "markup_artifacts": "high",
    "ai_vocab_cluster": "low",
    "structure": "low",
}
```

- [ ] **Step 4: Add the six rows**

Append this block inside the `RULES` list in `plugins/voice-check/engine/rules.py`, after the existing `markup_artifacts` rows and before the closing `])`:

```python
    # -- structural frames --------------------------------------------------
    # These match sentence SHAPES rather than words, so they fire on
    # legitimate prose more readily than a vocabulary rule does. They are low
    # severity, so Phase 1's collapse behavior summarizes them to a single
    # counted line unless the reader asks for detail.
    #
    # Every row carries "term" because a raw pattern must never reach a
    # developer's terminal, the same reason ai_vocab_cluster.additionally
    # carries one.
    *[
        {
            "name": "structure",
            "id": f"structure.{sid}",
            "category": "structure",
            "kind": "regex",
            "pattern": pattern,
            "term": term,
            "message": message,
            "scope": "line",
        }
        for sid, pattern, term, message in [
            (
                "not_just_but",
                r"\bnot (?:just|only|merely|simply)\b[^.!?\n]{1,80}?(?:,\s*)?\b(?:but|it['’]?s|it is)\b",
                "not just X, but Y",
                "Negative parallelism. The false opposition manufactures insight. Make the direct claim.",
            ),
            (
                "not_about_but_about",
                r"\b(?:it|this|that)['’]?s not about\b[^.!?\n]{1,80}?\b(?:it|this|that)['’]?s about\b",
                "it's not about X, it's about Y",
                "Contrast reframe. State the point directly instead of resolving a false opposition.",
            ),
            (
                "while_also",
                r"\bwhile\b[^.!?\n]{1,80}?,\s*(?:it|they|there)\s+also\b",
                "while X, it also Y",
                "Balanced-debate framing. Take a position or report the facts.",
            ),
            (
                "advantages_disadvantages",
                r"\b(?:advantages?|benefits?|strengths?)\b[^.!?\n]{0,60}?\b(?:disadvantages?|drawbacks?|weaknesses?|downsides?)\b",
                "advantages paired with disadvantages",
                "Balanced-debate framing. Take a position or report the facts.",
            ),
            (
                "despite_faces_challenges",
                r"\bdespite\s+(?:its|their|these|the)\b[^.!?\n]{1,80}?\bfaces?\b[^.!?\n]{0,40}?\bchallenges?\b",
                "despite X, Y faces challenges",
                "Challenges-and-prospects frame. Cut it or say something concrete.",
            ),
            (
                "false_range",
                # Lowercase plural to lowercase plural. "From X to Y" is
                # ordinary English, so the plural shape is what separates a
                # false enumeration of scope from a real range. Gerund pairs
                # such as "from onboarding to offboarding" are deliberately
                # missed: broadening to catch them would also fire on "from
                # testing to shipping", which is a genuine sequence.
                r"\bfrom\s+[a-z]+s\b[^.!?\n]{0,30}?\bto\s+[a-z]+s\b",
                "from Xs to Ys",
                "False range. Cut it unless a real spectrum exists.",
            ),
        ]
    ],
```

- [ ] **Step 5: Run the suite and expect a specific regression**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`

Expected: `tests/test_structure.py` all pass, AND `test_engine_reports_nothing_on_its_own_rule_list` in `tests/test_regressions.py` now FAILS. That failure is correct: `references/rules.md` quotes these very patterns as rule descriptions.

- [ ] **Step 6: Extend the suppression range in rules.md**

`plugins/voice-check/references/rules.md` already has a suppression range. Find this line:

```
<!-- voice-check: disable ai_vocab_cluster, puffery, promotional_tone, vocab_2026, bridge_phrases, hedging, vague_attribution, dangling_participle -->
```

Add `structure` to its list:

```
<!-- voice-check: disable ai_vocab_cluster, puffery, promotional_tone, vocab_2026, bridge_phrases, hedging, vague_attribution, dangling_participle, structure -->
```

Confirm the matching `<!-- voice-check: enable -->` still sits after the Markup Artifacts section, and that the Structural Tells section falls inside the range. If it does not, move the `enable` so the range covers it, since that section quotes the frames.

- [ ] **Step 7: Suppress the three other files that quote the frames**

These fire because they document the patterns, not because they exhibit them. Each needs a suppression range covering the region that quotes frames. Add `<!-- voice-check: disable structure -->` before the first quoting line and `<!-- voice-check: enable -->` after the last:

- `plugins/voice-check/references/examples.md`: its "before" samples deliberately exhibit these patterns.
- `plugins/voice-check/references/wikipedia-signs.md`: it describes the patterns.
- `docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md`: it quotes them while discussing the rules.

Find the exact lines to wrap by running the engine on each file:

```bash
cd /Users/ryan/voice-check
for f in plugins/voice-check/references/examples.md plugins/voice-check/references/wikipedia-signs.md docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md; do
  echo "### $f"
  python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low "$f"
done
```

Place each range as tightly as the findings allow. Do not wrap a whole file when a section suffices.

- [ ] **Step 8: Add the calibration regression test**

The spec records that these six patterns produce exactly fourteen hits across this repository, all in files that quote them. That measurement is only useful if something pins it. Append to `plugins/voice-check/tests/test_structure.py`:

```python
REPO_ROOT = Path(__file__).parent.parent.parent.parent


def _repo_markdown():
    skip = {".git", ".venv", "node_modules", ".superpowers", "syndicate", ".claude"}
    for p in sorted(REPO_ROOT.rglob("*.md")):
        if not skip.intersection(p.parts):
            yield p


def test_frames_stay_calibrated_across_the_repo():
    """Pins the spec's calibration so a later broadening cannot pass unnoticed.

    Every hit must be suppressed by the file that quotes it. A nonzero count
    here means either a pattern got broader or a document lost its
    suppression, and either way someone should look.
    """
    import voice_check
    offenders = {}
    for path in _repo_markdown():
        hits = [f for f in voice_check.scan(path) if f["rule"] == "structure"]
        if hits:
            offenders[str(path.relative_to(REPO_ROOT))] = sorted(
                {f["rule_id"] for f in hits}
            )
    assert offenders == {}, offenders
```

- [ ] **Step 9: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `176 passed` (160 baseline plus 16 new).

If `test_frames_stay_calibrated_across_the_repo` fails, it names the file and rule ids. Add or widen that file's suppression range rather than narrowing a pattern, unless the hit is genuinely a false positive on real prose, in which case narrow the pattern and say so in your report.

- [ ] **Step 10: Commit**

```bash
git add plugins/voice-check/engine/rules.py plugins/voice-check/tests/test_structure.py plugins/voice-check/references/ docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md
git commit -m "feat(rules): five structural frames as low severity rows

Adds six regex rows under the name "structure" covering negative
parallelism, contrast reframes, balanced-debate framing in two forms,
challenges-and-prospects, and false ranges. Line scope, low severity, each
carrying an explicit id and a term so no raw pattern reaches a terminal.

Calibrated at fourteen hits across the repo, every one in a file that quotes
the patterns as examples rather than exhibiting them. Those files gain
suppression ranges, and a test pins the count so a later broadening cannot
pass unnoticed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: The analyzers module

A rule that measures rather than matches. Not wired into the scanner yet, so the suite stays green throughout.

**Files:**
- Create: `plugins/voice-check/engine/analyzers.py`
- Test: `plugins/voice-check/tests/test_analyzers.py`

**Interfaces:**
- Consumes: nothing. The analyzer reads `doc.lines` directly and takes `cfg` without using it yet.
- Produces:
  - `analyzers.BULLET_RE` and `analyzers.BOLD_BULLET_RE`, module level compiled patterns.
  - `analyzers.MIN_BULLETS` equal to 4, `analyzers.RATIO_THRESHOLD` equal to 0.6.
  - `analyzers.mechanical_bold_headers(doc, cfg) -> list[dict]`, each entry `{"message": str, "lines": [int, ...]}`.
  - `analyzers.ANALYZERS`, a list of registry entries carrying `name`, `id`, `category`, `severity`, `fn`.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_analyzers.py`:

```python
"""Tests for computed analyzers.

An analyzer measures a property of a document rather than matching a
pattern. The bold header rule needs a ratio, which no rule row can express:
doc_min is an absolute count, so a document with 100 bullets and 5 bolded
would satisfy doc_min 4 while being 5 percent bolded.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import analyzers  # noqa: E402
import config  # noqa: E402
import document  # noqa: E402


def _run(text):
    doc = document.Document.from_markdown(text)
    return analyzers.mechanical_bold_headers(doc, config.Config.empty())


def _bullets(n, bolded):
    """Build a document with n bullets, the first `bolded` of them bold."""
    out = ["# Heading", ""]
    for i in range(n):
        if i < bolded:
            out.append(f"- **Term {i}:** some explanation here")
        else:
            out.append(f"- plain bullet {i} with no bold run")
    return "\n".join(out) + "\n"


def test_fires_when_most_bullets_are_bolded():
    assert _run(_bullets(5, 5))


def test_silent_when_no_bullets_at_all():
    assert _run("Just a paragraph of prose with no list in it.\n") == []


def test_silent_on_an_empty_document():
    assert _run("") == []


def test_three_bullets_is_below_the_minimum():
    """MIN_BULLETS is 4, so a short list never counts as mechanical."""
    assert _run(_bullets(3, 3)) == []


def test_four_bullets_meets_the_minimum():
    assert _run(_bullets(4, 4))


def test_ratio_below_threshold_stays_silent():
    """5 of 10 is 50 percent, under the 0.6 threshold."""
    assert _run(_bullets(10, 5)) == []


def test_ratio_at_threshold_fires():
    """6 of 10 is exactly 0.6, and the comparison is inclusive."""
    assert _run(_bullets(10, 6))


def test_many_bullets_with_few_bolded_stays_silent():
    """The case doc_min cannot express: 5 bolded clears an absolute count
    of 4, but 5 percent is nowhere near mechanical."""
    assert _run(_bullets(100, 5)) == []


def test_evidence_lines_point_at_the_bolded_bullets():
    entries = _run(_bullets(5, 5))
    assert len(entries) == 1
    # Two header lines precede the bullets, so they start at line 3.
    assert entries[0]["lines"] == [3, 4, 5, 6, 7]


def test_message_is_plain_language():
    entries = _run(_bullets(5, 5))
    assert "**" not in entries[0]["message"]
    assert "bullet" in entries[0]["message"].lower()


def test_registry_entry_matches_the_rule_row_contract():
    """Phase 1's config and suppression code reads name and id off a row.
    An analyzer entry must carry the same keys or none of that applies."""
    assert analyzers.ANALYZERS
    for entry in analyzers.ANALYZERS:
        for field in ("name", "id", "category", "severity", "fn"):
            assert field in entry, entry
        assert entry["name"] == "structure"
        assert entry["id"].startswith("structure.")
        assert callable(entry["fn"])
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_analyzers.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'analyzers'`

- [ ] **Step 3: Write analyzers.py**

Create `plugins/voice-check/engine/analyzers.py`:

```python
"""Rules that compute over a document rather than matching against it.

A rule row answers "does this pattern appear?". An analyzer answers
questions of proportion and shape that a pattern cannot reach. The bold
header rule is the motivating case: it needs the FRACTION of bullets that
open with a bold run, and doc_min is an absolute count, so a document with
100 bullets and 5 bolded would satisfy doc_min 4 while being 5 percent.

Registry entries carry the same keys a rule row carries, with "fn" in place
of "pattern" and "kind". That is deliberate: config.is_disabled,
config.severity_for, and Suppression.covers all read "name" and "id" and
nothing else, so every per repo control from Phase 1 applies to analyzers
with no change to those modules.

An analyzer returns entries of {"message": str, "lines": [int, ...]}, where
lines are the source lines that evidence the finding. It does not build a
complete finding and knows nothing about severity, suppression, or line
ranges. The scanner applies all three.
"""
import re

BULLET_RE = re.compile(r"^\s*[-*+]\s+")
BOLD_BULLET_RE = re.compile(r"^\s*[-*+]\s+\*\*[^*\n]+\*\*")

MIN_BULLETS = 4
RATIO_THRESHOLD = 0.6


def mechanical_bold_headers(doc, cfg):
    """Flag a list whose bullets nearly all open with a bold run.

    Reads doc.lines, the RAW lines, not doc.scan_lines. Masking replaces the
    bullet marker with a space, so the masked view cannot see the structure
    this rule measures. Do not "fix" this to use scan_lines for consistency.
    """
    bullet_lines = []
    bold_lines = []
    for num, line in enumerate(doc.lines, start=1):
        if not BULLET_RE.match(line):
            continue
        bullet_lines.append(num)
        if BOLD_BULLET_RE.match(line):
            bold_lines.append(num)

    if len(bullet_lines) < MIN_BULLETS:
        return []

    ratio = len(bold_lines) / len(bullet_lines)
    if ratio < RATIO_THRESHOLD:
        return []

    percent = round(ratio * 100)
    return [{
        "message": (
            f"Mechanical bold headers: {len(bold_lines)} of "
            f"{len(bullet_lines)} bullets ({percent} percent) open with a "
            f"bold run. Use them sparingly, not on every entry."
        ),
        "lines": bold_lines,
    }]


ANALYZERS = [
    {
        "name": "structure",
        "id": "structure.bold_headers",
        "category": "structure",
        "severity": "low",
        "fn": mechanical_bold_headers,
    },
]
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_analyzers.py -q`
Expected: `11 passed`

- [ ] **Step 5: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `187 passed` (176 plus 11). The analyzer is not wired in yet, so nothing else changes.

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/engine/analyzers.py plugins/voice-check/tests/test_analyzers.py
git commit -m "feat(analyzers): computed rules, starting with mechanical bold headers

A rule row answers whether a pattern appears. An analyzer answers questions
of proportion that a pattern cannot reach. The motivating case needs the
fraction of bullets opening with a bold run, and doc_min is an absolute
count, so 5 bolded out of 100 would satisfy it while being 5 percent.

Registry entries share the rule row contract, so Phase 1's disable,
severity, and suppression apply with no change to those modules. Not wired
into the scanner yet.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Wire analyzers into the scanner

The cutover. After this, the analyzer is live and inherits diff scoping and suppression without containing code for either.

**Files:**
- Modify: `plugins/voice-check/engine/scanner.py`
- Modify: `plugins/voice-check/engine/config.py`
- Modify: `README.md`, `plugins/voice-check/references/rules.md`
- Test: `plugins/voice-check/tests/test_analyzers.py`

**Interfaces:**
- Consumes: `analyzers.ANALYZERS` and `analyzers.mechanical_bold_headers` from Task 2; `scanner.in_ranges`, `scanner._suppressed`, `config.is_disabled`, `config.severity_for` from the shipped engine.
- Produces: `scanner.scan` emits analyzer findings with the same keys as every other finding (`rule`, `rule_id`, `severity`, `line`, `col`, `snippet`, `message`); `config.KNOWN_IDENTIFIERS` includes analyzer names and ids.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_analyzers.py`. Move the `import scanner` line up to the top of the file beside the existing imports rather than leaving it mid file, so the file keeps a normal import block.

```python
import scanner  # noqa: E402


def _scan(text, cfg=None, rel_path="a.md", line_ranges=None):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg or config.Config.empty(), rel_path, line_ranges)


def _bold_findings(findings):
    return [f for f in findings if f["rule_id"] == "structure.bold_headers"]


def test_analyzer_finding_reaches_the_scanner():
    f = _bold_findings(_scan(_bullets(5, 5)))
    assert len(f) == 1
    assert f[0]["rule"] == "structure"
    assert f[0]["severity"] == "low"


def test_analyzer_finding_points_at_a_real_line():
    """line must be a surviving evidence line, never 0."""
    f = _bold_findings(_scan(_bullets(5, 5)))
    assert f[0]["line"] == 3


def test_config_disable_by_name_removes_the_analyzer():
    cfg = config.Config.empty()
    cfg.disabled.append(("structure", None))
    assert _bold_findings(_scan(_bullets(5, 5), cfg)) == []


def test_config_disable_by_id_removes_only_the_analyzer():
    cfg = config.Config.empty()
    cfg.disabled.append(("structure.bold_headers", None))
    assert _bold_findings(_scan(_bullets(5, 5), cfg)) == []


def test_config_severity_override_reaches_the_analyzer():
    cfg = config.Config.empty()
    cfg.severity["structure.bold_headers"] = "high"
    f = _bold_findings(_scan(_bullets(5, 5), cfg))
    assert f[0]["severity"] == "high"


def test_suppression_over_every_evidence_line_drops_the_finding():
    text = "<!-- voice-check: disable structure.bold_headers -->\n" + _bullets(5, 5)
    assert _bold_findings(_scan(text)) == []


def test_analyzer_survives_line_ranges_when_evidence_is_inside():
    assert _bold_findings(_scan(_bullets(5, 5), line_ranges=[(4, 4)]))


def test_analyzer_dropped_when_no_evidence_is_in_range():
    assert _bold_findings(_scan(_bullets(5, 5), line_ranges=[(1, 1)])) == []


def test_excluded_path_skips_analyzers_too():
    cfg = config.Config.empty()
    cfg.exclude.append("skip/**")
    assert _bold_findings(_scan(_bullets(5, 5), cfg, rel_path="skip/a.md")) == []


def test_a_raising_analyzer_does_not_take_out_other_findings(monkeypatch, capsys):
    """One bad analyzer must not lose the rule passes or the other analyzers."""
    def boom(doc, cfg):
        raise RuntimeError("analyzer exploded")

    monkeypatch.setattr(
        analyzers, "ANALYZERS",
        [{"name": "structure", "id": "structure.boom", "category": "structure",
          "severity": "low", "fn": boom}],
    )
    findings = _scan("A line with an em dash \u2014 here.\n")
    assert any(f["rule"] == "no_dashes" for f in findings)
    assert "structure.boom" in capsys.readouterr().err


def test_known_identifiers_includes_analyzer_names_and_ids():
    """Otherwise disabling an analyzer would warn as an unknown rule."""
    assert "structure" in config.KNOWN_IDENTIFIERS
    assert "structure.bold_headers" in config.KNOWN_IDENTIFIERS
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_analyzers.py -q -k "scanner or disable or severity_override or suppression or line_ranges or excluded or raising or known_identifiers"`
Expected: FAIL. The analyzer is not wired in, so no `structure.bold_headers` findings appear.

- [ ] **Step 3: Union the analyzer registry into KNOWN_IDENTIFIERS**

In `plugins/voice-check/engine/config.py`, add `import analyzers` beside the existing `import rules`, and extend the constant:

```python
# Every identifier a disable or severity entry may name. Supplement rules add
# their own names at scan time, so an unknown identifier warns rather than
# failing: rule ids shift between versions and a stale entry must not be fatal.
KNOWN_IDENTIFIERS = (
    {r["name"] for r in rules.RULES}
    | {r["id"] for r in rules.RULES}
    | {a["name"] for a in analyzers.ANALYZERS}
    | {a["id"] for a in analyzers.ANALYZERS}
)
```

- [ ] **Step 4: Add the third pass to the scanner**

In `plugins/voice-check/engine/scanner.py`, add `import sys` and `import analyzers` at the top beside `import rules`. Then insert this block immediately before the final `return findings`:

```python
    # Analyzer pass. Analyzers compute over the document instead of matching
    # it, and return {"message", "lines"} entries. Everything that makes an
    # entry into a finding happens here, so an analyzer needs no knowledge of
    # suppression, severity, or line ranges.
    for entry in analyzers.ANALYZERS:
        if cfg.is_disabled(entry, rel_path):
            continue
        try:
            produced = entry["fn"](doc, cfg)
        except Exception as exc:  # noqa: BLE001
            # One failing analyzer must not cost us the rule passes or the
            # other analyzers. This is the one place the project's "degrade
            # toward reporting more" principle cannot hold.
            print(
                f"voice-check: analyzer {entry['id']} failed ({exc}), skipping",
                file=sys.stderr,
            )
            continue

        for item in produced:
            evidence = [
                ln for ln in item["lines"]
                if not _suppressed(doc, ln, entry)
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
```

Also update the module docstring's list of what `scan` applies, adding the analyzer pass.

- [ ] **Step 5: Run to verify they pass**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/test_analyzers.py -q`
Expected: `22 passed`

- [ ] **Step 6: Run the full suite and expect a specific regression**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`

Expected: the self scan tests for `README.md` and `references/rules.md` now FAIL. That is correct and anticipated: both are glossary style definition lists whose bullets are 86 percent and 80 percent bolded. Step 7 fixes it.

- [ ] **Step 7: Add the glossary suppressions**

Both files legitimately use a bolded term per entry, which is what a definition list looks like. Suppress the analyzer specifically in each, never with a blanket ignore.

In `README.md`, immediately before the bulleted list under "What it catches", add:

```markdown
<!-- voice-check: disable structure.bold_headers -->
```

and immediately after that list:

```markdown
<!-- voice-check: enable -->
```

In `plugins/voice-check/references/rules.md`, do the same around the Structural Tells bulleted list. Note that this file's existing suppression range may already cover it; if so, add nothing and say so in your report.

If a run shows the finding persists, the range does not cover the bolded bullets. Widen it to the smallest span that does.

- [ ] **Step 8: Verify the whole repo scans clean**

Run:

```bash
cd /Users/ryan/voice-check
for f in README.md CLAUDE.md plugins/voice-check/references/rules.md \
         docs/superpowers/specs/2026-09-07-signal-quality-design.md \
         docs/superpowers/specs/2026-09-07-structural-detection-design.md; do
  echo "### $f"
  python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low "$f"
done
```

Expected: no output under any heading.

- [ ] **Step 9: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `198 passed` (187 plus 11).

- [ ] **Step 10: Commit**

```bash
git add plugins/voice-check/engine/scanner.py plugins/voice-check/engine/config.py plugins/voice-check/tests/test_analyzers.py README.md plugins/voice-check/references/rules.md
git commit -m "feat(scanner): run computed analyzers as a third pass

Analyzers now reach the output. The scanner converts each entry into a
finding, applying disable, suppression over evidence lines, severity, and
line range filtering, so an analyzer contains no code for any of them.

A failing analyzer warns on stderr and is skipped rather than costing the
rule passes. README and rules.md gain a suppression naming
structure.bold_headers alone, since both are glossary style definition
lists where a bolded term per entry is conventional.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Documentation and version

Bring the prose in line, and record the rhythm result so it is not re-derived.

**Files:**
- Modify: `plugins/voice-check/references/rules.md`, `README.md`, `CLAUDE.md`, `plugins/voice-check/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: everything above. Produces no code interface.

- [ ] **Step 1: Retag the Structural Tells section**

In `plugins/voice-check/references/rules.md`, the Structural Tells heading currently reads `## Structural Tells `[skill only]``. Change it to `## Structural Tells` with no tag, and tag each bullet individually, since the section is now mixed. Mark these five `[engine + skill]`:

- Negative parallelisms and contrast reframes
- False ranges
- Challenges-and-future-prospects
- Bolded inline headers on every bullet
- Balanced-debate framing

Mark these two `[skill only]`, keeping the existing explanation that a regex cannot tell signal from noise:

- Rule of three
- Elegant variation

For uniform sentence rhythm, mark it `[skill only]` and replace its text with the measured reason:

```markdown
- **Uniform sentence rhythm** `[skill only]`: every sentence landing in the
  same length range. Vary it. Some thoughts need three words. Some need a
  full paragraph. The engine does not attempt this. Measuring the coefficient
  of variation of sentence lengths across this repository put a deliberately
  AI sounding sample at 0.48, between two hand written files at 0.40 and
  0.41, so no threshold separates them. Technical reference prose is
  legitimately uniform, and this advice is about narrative writing.
```

- [ ] **Step 2: Document the false range limitation**

Under the False ranges bullet, record the deliberate miss so nobody "fixes" it:

```markdown
  The engine matches lowercase plural to lowercase plural, which is what
  separates a false enumeration ("from startups to enterprises") from an
  ordinary range ("from 9 to 5"). Gerund pairs such as "from onboarding to
  offboarding" are missed on purpose: catching them would also fire on "from
  testing to shipping", which describes a real sequence.
```

- [ ] **Step 3: Update the README**

In `README.md`, add a bullet to the "What it catches" list:

```markdown
- **Structural tells [engine]:** negative parallelism ("not just X, but Y"), contrast reframes, balanced-debate framing, challenges-and-prospects, false ranges, and mechanical bold headers on bullet lists. All low severity, so they collapse to a counted line unless you pass `--min-severity low`.
```

Update the existing "Structural tells [skill]" bullet to name only what remains skill-only: rule of three, elegant variation, and uniform sentence rhythm.

- [ ] **Step 4: Update CLAUDE.md**

In the Architecture section's Python engine paragraph, add `analyzers.py` to the module list:

```markdown
   `analyzers.py` holds rules that compute over a document rather than
   matching against it, for properties like the fraction of bullets opening
   with a bold run that no rule row can express. Its registry entries share
   the rule row contract, so per repo disable, severity, and suppression
   apply to analyzers unchanged.
```

Update the test count to the number from Task 3's final run.

- [ ] **Step 5: Bump the version**

In `plugins/voice-check/.claude-plugin/plugin.json`, change `"version": "2.3.0"` to `"version": "2.4.0"`. A feature release: new rules and a new module, no breaking change.

- [ ] **Step 6: Verify the docs pass their own engine**

Run:

```bash
cd /Users/ryan/voice-check
for f in README.md CLAUDE.md plugins/voice-check/references/rules.md \
         plugins/voice-check/skills/voice-check/SKILL.md \
         plugins/voice-check/skills/writing-guard/SKILL.md; do
  echo "### $f"
  python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low "$f"
done
```

Expected: no output under any heading. Fix any finding in the prose rather than suppressing it, unless it is a mention the masking should have caught, in which case say so in your report.

- [ ] **Step 7: Run the full suite**

Run: `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q`
Expected: `198 passed`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: structural rules retagged, rhythm result recorded, bump to 2.4.0

Five Structural Tells bullets move from skill only to engine plus skill.
Three stay skill only with their reasons recorded: rule of three and elegant
variation need semantics, and uniform rhythm was measured across this
repository and does not discriminate, with the numbers written down so the
decision is not re-derived.

Also records why false ranges deliberately misses gerund pairs.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Verification Checklist

Run after Task 4. Every line must hold.

- [ ] `cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q` reports 198 passing
- [ ] The paragraph from the spec's Context section reports at least three structural findings:
  ```bash
  printf 'Our platform is not just a tool, it is a partner.\nWhile there are tradeoffs, it also has costs.\nDespite its strong adoption, the tool faces challenges ahead.\n' > /tmp/vc-structural.md
  python3 plugins/voice-check/engine/voice_check.py --report-only --min-severity low /tmp/vc-structural.md
  ```
- [ ] Every repo markdown file scans clean, pinned by `test_frames_stay_calibrated_across_the_repo`
- [ ] A document with 100 bullets and 5 bolded stays silent
- [ ] Disabling `structure` removes both the frames and the analyzer; disabling `structure.bold_headers` removes only the analyzer
- [ ] The hook still exits 0 with a deliberately broken `.claude/voice-check.md`
- [ ] Every spec success criterion (1 through 12) has a passing test behind it

## Spec Coverage

| Spec requirement | Task |
| --- | --- |
| Five frames as line-scope rows | 1 |
| Frame calibration pinned by a test | 1 |
| Negative test per frame | 1 |
| Suppression in files that quote the frames | 1 |
| `analyzers.py` and the analyzer contract | 2 |
| `mechanical_bold_headers` with measured thresholds | 2 |
| The case `doc_min` cannot express | 2 |
| Registry entries share the rule row contract | 2 |
| Scanner third pass | 3 |
| Suppression over evidence lines | 3 |
| Diff scoping via evidence lines | 3 |
| Per analyzer error isolation | 3 |
| `KNOWN_IDENTIFIERS` union | 3 |
| Glossary suppressions in README and rules.md | 3 |
| Retag five bullets to engine plus skill | 4 |
| Rhythm negative result recorded | 4 |
| False range limitation recorded | 4 |
| Version bump | 4 |
