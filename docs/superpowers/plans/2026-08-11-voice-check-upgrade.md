# Voice Check Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit both skills with Anthropic's skill authoring best practices (engine-as-validator loop, checklists, third-person descriptions) and refresh the rules for the 2026 generation of AI writing tells.

**Architecture:** The Python engine (`engine/rules.py`) is a single data-driven rule table; new rule categories are new rows, no scanner changes. Skills are thin Markdown shells reading `references/rules.md`. Spec: `docs/superpowers/specs/2026-08-11-voice-check-upgrade-design.md`.

**Tech Stack:** Python 3.11+ stdlib (engine), pytest (tests only), Markdown (skills, references).

## Global Constraints

- No em dashes, en dashes, or spaced hyphens in ANY written output: docs, comments, commit messages, plan prose. Compound-word hyphens ("report-only") are fine.
- Engine stays stdlib-only. `--report-only` always exits 0 (advisory hook contract).
- Any commit adding engine rules updates `references/rules.md` in the SAME commit (dual-authority rule).
- Skill files reference rules via `../../references/rules.md` (plugin root, two levels up from the skill dir). Do not move references.
- Run tests from `plugins/voice-check/`: `.venv/bin/python -m pytest tests/test_engine.py -v`
- All ~30 existing tests must stay green after every task.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 0: Baseline

**Files:** none modified.

- [ ] **Step 1: Ensure venv exists and run the suite**

```bash
cd plugins/voice-check
[ -d .venv ] || (python3 -m venv .venv && .venv/bin/pip install pytest)
.venv/bin/python -m pytest tests/test_engine.py -v
```

Expected: all tests PASS (~30 cases). If any fail, STOP and report; do not build on a red baseline.

---

### Task 1: Engine + rules.md, faux-conversational bridges

**Files:**
- Modify: `plugins/voice-check/engine/rules.py` (append rows to `RULES` before the closing `]`, after the `ai_vocab_cluster` block)
- Modify: `plugins/voice-check/references/rules.md` (new section before "Per-repo supplements")
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Produces: findings with `rule == "bridge_phrases"` from `voice_check.scan(path)`. Tasks 6 and 8 rely on this rule name.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`)

```python
# ---------------------------------------------------------------------------
# 2026 refresh: faux-conversational bridges
# ---------------------------------------------------------------------------

def test_bridge_phrase_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Here's the thing, the rollout slipped because staging was down.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert len(bridges) >= 1


def test_bridge_section_opener_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("In this section, we will explore the deployment pipeline.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert len(bridges) >= 1


def test_bridge_phrase_not_flagged_on_similar_words(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("He got me wrong. The day shift ends at five.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert bridges == []
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k bridge -v`
Expected: 2 FAIL (positive cases), 1 PASS (negative control passes vacuously).

- [ ] **Step 3: Add the rule rows** (in `engine/rules.py`, inside `RULES`, after the `ai_vocab_cluster` list comprehension block)

```python
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
            "at the end of the day",
            "don't get me wrong",
            "let's dive in",
            "let's delve into",
            "we will explore",
            "let's examine",
        ]
    ],
    {
        "name": "bridge_phrases",
        "category": "bridge_phrases",
        "kind": "regex",
        "pattern": r"\bin this section,?\s+we\b",
        "message": "Faux-conversational bridge: 'in this section we'. Cut the meta commentary.",
        "scope": "line",
    },
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS, including all pre-existing tests.

- [ ] **Step 5: Add the rules.md section** (in `references/rules.md`, insert before the "## Per-repo supplements" heading)

```markdown
## Faux-conversational Bridges `[engine + skill]`

Flag and cut: "here's the thing," "but here's the truth," "at the end of the day," "don't get me wrong," "let's dive in," "let's delve into," "let's examine," "we will explore," "in this section we will."

These bridges simulate spoken candor or announce structure instead of delivering content. State the point directly.
```

- [ ] **Step 6: Commit**

```bash
git add engine/rules.py references/rules.md tests/test_engine.py
git commit -m "feat(engine): flag faux-conversational bridge phrases

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Engine + rules.md, 2026 vocabulary cluster

**Files:**
- Modify: `plugins/voice-check/engine/rules.py` (append rows after Task 1's rows)
- Modify: `plugins/voice-check/references/rules.md` (new section after the Task 1 section)
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Produces: findings with `rule == "vocab_2026"`. The existing `ai_vocab_cluster` rule and word list stay untouched.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`)

```python
# ---------------------------------------------------------------------------
# 2026 refresh: new vocabulary generation (phrase-level only in the engine)
# ---------------------------------------------------------------------------

def test_vocab_2026_phrase_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Great founders are built different, and their decisions compound.\n")
    findings = voice_check.scan(f)
    vocab = [x for x in findings if x["rule"] == "vocab_2026"]
    assert len(vocab) >= 1


def test_vocab_2026_quietly_gerund_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("The team is quietly building a replacement for the old stack.\n")
    findings = voice_check.scan(f)
    vocab = [x for x in findings if x["rule"] == "vocab_2026"]
    assert len(vocab) >= 1


def test_vocab_2026_send_signal_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Shipping on Friday sends a signal to the whole org.\n")
    findings = voice_check.scan(f)
    vocab = [x for x in findings if x["rule"] == "vocab_2026"]
    assert len(vocab) >= 1


def test_vocab_2026_not_flagged_on_plain_use(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("She spoke quietly during the review. Interest compounds monthly.\n")
    findings = voice_check.scan(f)
    vocab = [x for x in findings if x["rule"] == "vocab_2026"]
    assert vocab == []
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k vocab_2026 -v`
Expected: 3 FAIL, 1 PASS (negative control).

- [ ] **Step 3: Add the rule rows** (in `engine/rules.py`, after the Task 1 rows, still inside `RULES`)

```python
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
        "category": "vocab_2026",
        "kind": "regex",
        # Stop list keeps non-gerund "ing" words (during, morning...) from firing.
        "pattern": r"\bquietly\s+(?!(?:during|morning|evening|something|anything|everything|nothing)\b)\w+ing\b",
        "message": "2026 AI vocabulary: 'quietly [verb]ing'. Name the action plainly.",
        "scope": "line",
    },
    {
        "name": "vocab_2026",
        "category": "vocab_2026",
        "kind": "regex",
        "pattern": r"\bsends?\s+(?:a|the)\s+signal\b",
        "message": "2026 AI vocabulary: 'send a signal'. Say what actually happens.",
        "scope": "line",
    },
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Add the rules.md section** (insert after the Faux-conversational Bridges section)

```markdown
## 2026 Vocabulary Cluster

The vocabulary generation turned over in 2025/2026. Current model output leaks abstract fillers and unearned intensifiers with a LinkedIn flavor.

Bare words `[skill only]` (flag when 2+ appear in the same document, same clustering logic as the AI Vocabulary Cluster above): quietly, shift (as default word for any change), matters, shape (as vague influence verb), land (for message reception), actually, real (as intensifier), earn (attached to abstractions), hold (metaphorical), pull (unnamed forces), compound (as growth default), signal (abstract substitute), the work (vague reverence).

These are common English words; judge them in context. "She spoke quietly" is fine. "Quietly building an empire" is the tell.

Phrase forms `[engine + skill]`: "quietly [verb]ing," "this matters because," "the pull of," "built different," "do the work," "send a signal," "decisions compound."
```

- [ ] **Step 6: Commit**

```bash
git add engine/rules.py references/rules.md tests/test_engine.py
git commit -m "feat(engine): flag 2026 vocabulary phrases, document skill-only word cluster

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Engine + rules.md, markup artifacts

**Files:**
- Modify: `plugins/voice-check/engine/rules.py` (append rows after Task 2's rows)
- Modify: `plugins/voice-check/references/rules.md` (new section after the Task 2 section)
- Test: `plugins/voice-check/tests/test_engine.py` (append)

**Interfaces:**
- Produces: findings with `rule == "markup_artifacts"`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_engine.py`)

```python
# ---------------------------------------------------------------------------
# 2026 refresh: leaked model markup artifacts
# ---------------------------------------------------------------------------

def test_markup_artifact_token_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("The study backs this claim. :contentReference[oaicite:0]{index=0}\n")
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert len(artifacts) >= 1


def test_markup_artifact_gemini_cite_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Revenue grew 40 percent last year. [cite: 3]\n")
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert len(artifacts) >= 1


def test_markup_artifact_in_code_fence_not_flagged(tmp_path):
    f = tmp_path / "quoting.md"
    f.write_text(
        "Example of a leaked token:\n"
        "\n"
        "```\n"
        ":contentReference[oaicite:0]{index=0}\n"
        "```\n"
    )
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert artifacts == []


def test_emoji_bullet_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("\U0001F680 Ship the feature\n")
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert len(artifacts) >= 1


def test_emoji_midline_not_flagged(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("We shipped the feature \U0001F680 and moved on.\n")
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert artifacts == []
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_engine.py -k "markup or emoji" -v`
Expected: 3 FAIL (positives), 2 PASS (negative controls).

- [ ] **Step 3: Add the rule rows** (in `engine/rules.py`, after the Task 2 rows, still inside `RULES`)

```python
    # -- leaked model markup artifacts --------------------------------------
    {
        "name": "markup_artifacts",
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
        "category": "markup_artifacts",
        "kind": "regex",
        "pattern": r"^\s*[☀-➿\U0001F300-\U0001FAFF]️?\s+",
        "message": "Emoji used as a bullet marker. Use standard list markers.",
        "scope": "line",
    },
```

Note: fenced code blocks are already skipped by the scanner, which is the intended behavior (an artifact inside a fence is plausibly intentional quoting). Do not change the scanner.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Add the rules.md section** (insert after the 2026 Vocabulary Cluster section)

```markdown
## Markup Artifacts `[engine + skill]`

Leaked model citation tokens are proof of unedited AI output. Flag and delete: `contentReference`, `oaicite`, `turn0search` style tokens, `[cite:` fragments, `[span_0]` fragments, `grok_card`, `grok_render`, `ppl-ai-file-upload`, `attached_file`.

Emoji used as bullet markers (an emoji starting a line as if it were a list marker) is also flagged. Use standard list markers. Artifacts quoted inside fenced code blocks are not flagged.
```

- [ ] **Step 6: Commit**

```bash
git add engine/rules.py references/rules.md tests/test_engine.py
git commit -m "feat(engine): flag leaked model markup artifacts and emoji bullets

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: rules.md structural amendments + examples.md

**Files:**
- Modify: `plugins/voice-check/references/rules.md` (edit the "## Structural Tells `[skill only]`" section)
- Modify: `plugins/voice-check/references/examples.md` (append sections)

**Interfaces:**
- Produces: rule text consumed at runtime by both skills (no code interface).

- [ ] **Step 1: Amend the Structural Tells section**

In `references/rules.md`, inside "## Structural Tells `[skill only]`", replace this bullet:

```markdown
- **Negative parallelisms**: "Not just X, but Y" and "It's not about X, it's about Y." Overused. Rewrite.
```

with:

```markdown
- **Negative parallelisms and contrast reframes**: "Not just X, but Y" and "It's not about X, it's about Y." The reframe manufactures insight by setting up a false opposition and resolving it in one move. Also flag overuse of "X rather than Y." Rewrite as a direct claim.
```

and add these bullets at the end of the same bullet list (before the closing paragraph "These are context-sensitive patterns..."):

```markdown
- **Balanced-debate framing**: "While X has its advantages, it also has some disadvantages." Presenting every topic as a two-sided debate is a tell. Take a position or report the facts.
- **Uniform sentence rhythm**: every sentence landing in the same length range. Vary it. Some thoughts need three words. Some need a full paragraph.
```

- [ ] **Step 2: Append examples** (at the end of `references/examples.md`)

```markdown
## Faux-conversational bridges

- BEFORE: "Here's the thing, at the end of the day the migration was worth it."
- AFTER: "The migration was worth it. Query time dropped 80 percent."

## 2026 vocabulary

- BEFORE: "We're quietly building something that actually matters, and the gains compound."
- AFTER: "We're building a billing system. It cut invoice errors from 40 a month to 2."

## Markup artifacts

- BEFORE: "The study confirms the trend. :contentReference[oaicite:0]{index=0}"
- AFTER: "The study confirms the trend (Smith et al., 2025)."

## Contrast reframes

- BEFORE: "It's not about the tooling, it's about the culture."
- AFTER: "Culture drove the change. The tooling stayed the same."

## Balanced-debate framing

- BEFORE: "While microservices offer flexibility, they also introduce complexity."
- AFTER: "Microservices cost us two weeks of debugging distributed traces. We went back to the monolith."
```

- [ ] **Step 3: Run the suite to confirm nothing broke**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS (these are markdown-only edits).

- [ ] **Step 4: Commit**

```bash
git add references/rules.md references/examples.md
git commit -m "docs(rules): add contrast reframes, balanced-debate framing, rhythm; new examples

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Refresh wikipedia-signs.md

**Files:**
- Modify: `plugins/voice-check/references/wikipedia-signs.md` (full rewrite)

**Interfaces:**
- Produces: reference doc loaded on demand by the voice-check skill.

- [ ] **Step 1: Fetch the current article**

Fetch https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing (WebFetch or equivalent). If fetching fails, keep the existing body and only apply Steps 2 and 3 plus the "Model-specific signatures" and "Era-dependent vocabulary" sections below from this plan's summary.

- [ ] **Step 2: Rewrite the file with this structure**

Required header (first lines of the file):

```markdown
# Wikipedia: Signs of AI Writing (condensed)

Snapshot as of 2026-08-11 of https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing, condensed for skill use.

## Contents

- Content-level indicators
- Language patterns
- Era-dependent vocabulary
- Formatting and markup tells
- Citation red flags
- Stylistic quirks
- Model-specific signatures
- False positives to avoid
```

Body requirements: one `##` section per Contents entry, condensed from the fetched article. Must include (a) era-dependent vocabulary lists (2023 to mid-2024: delve, intricate, pivotal, testament; mid-2024 to mid-2025: align with, enhance, fostering, showcasing; mid-2025 onward: the quietly/shift/matters/signal/compound cluster), (b) model-specific signatures (Grok overusing causal, empirical, correlate, underscore; leaked artifact tokens per model: ChatGPT contentReference/oaicite/turn0search, Gemini [cite:/[span_, Grok grok_card, Perplexity ppl-ai-file-upload/attached_file), (c) contrast reframes and tailing clauses, (d) the false-positives caveat section. No em dashes anywhere in the rewritten file, including quoted material (paraphrase around them).

- [ ] **Step 3: Verify no dashes leaked in**

Run: `grep -n $'—\|–' references/wikipedia-signs.md`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add references/wikipedia-signs.md
git commit -m "docs(references): refresh wikipedia signs snapshot to 2026-08-11, add table of contents

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Rewrite voice-check SKILL.md

**Files:**
- Modify: `plugins/voice-check/skills/voice-check/SKILL.md` (full replacement)

**Interfaces:**
- Consumes: `python3 <plugin-root>/engine/voice_check.py --report-only <target>` (CLI, exit 0 always, findings on stdout/stderr) and rule names from Tasks 1 through 3.

- [ ] **Step 1: Replace the file with exactly this content**

````markdown
---
name: voice-check
description: Scans a document for AI writing tells, including em dashes, hedging, puffery, AI vocabulary clusters, promotional tone, bridge phrases, and leaked markup artifacts. Use when reviewing or editing prose, before committing any document, when invoked via /voice-check, or when the user mentions AI-sounding writing, voice, or tone. Layers global rules with per-repo supplements found at .claude/voice-check.md walking up from the target file.
---

# Voice Check (reactive scan)

Scans a file for AI writing patterns and tone violations, fixes every issue found, then reports what changed. The deterministic rules are verified by the bundled Python engine; context-sensitive rules get a manual pass.

## Process

Copy this checklist and check off items as you complete them:

```
Voice Check Progress:
- [ ] Step 1: Read the rules, locate the target file and any supplement
- [ ] Step 2: Run the engine (report-only)
- [ ] Step 3: Fix every engine finding
- [ ] Step 4: Re-run the engine until it reports zero findings
- [ ] Step 5: Manual pass for skill-only rules
- [ ] Step 6: Report changes by category
```

**Step 1: Read the rules, locate the target and supplement.**
Read `../../references/rules.md` (the file lives at the plugin root, two levels up from this skill directory, NOT inside the skill dir). Determine the target file path. Walk up from the target file to the git root, looking for `.claude/voice-check.md` at each level. Stop at the first one found; do not aggregate across levels. Load the supplement if found.

**Step 2: Run the engine.**
Run this script (execute it, do not read it as reference):

```bash
python3 ../../engine/voice_check.py --report-only <target-file>
```

The path is relative to this skill directory; resolve it against the installed plugin location. The engine covers every rule tagged `[engine + skill]` plus supplement rules, and always exits 0. If `python3` is unavailable, skip to Step 5 and cover the engine-tagged rules manually as well.

**Step 3: Fix every engine finding.**
Rewrite the target file to resolve each finding. Preserve meaning; change only the flagged constructions and their immediate context.

**Step 4: Re-run the engine.**
Repeat Steps 2 and 3 until the engine reports zero findings. Do not proceed to Step 5 with open engine findings.

**Step 5: Manual pass for skill-only rules.**
The engine cannot see these; scan for them yourself using `../../references/rules.md`:

- Structural tells: rule of three, negative parallelisms and contrast reframes, false ranges, challenges-and-future-prospects, balanced-debate framing, uniform sentence rhythm, mechanical bold headers, elegant variation
- 2026 bare-word cluster in context (quietly, shift, matters, signal, compound, and the rest; two or more in a document is a pattern)
- Nuanced copula avoidance ("represents," "marks")

**Step 6: Report a summary of changes by category.**

## Modes

- **Auto-fix (default for /voice-check):** the full process above; rewrite the file in place.
- **Report-only (pre-commit hook path):** print findings, do not modify the file. The hook calls the engine directly; if this skill is invoked in a report-only context, run Steps 1, 2, and 5 and print findings without editing.

## References

All reference files live at the plugin root, two levels up from this skill directory:

- `../../references/rules.md`: the rule list (single source of truth). Read it in Step 1.
- `../../references/examples.md`: before/after examples per rule category. Read when unsure how to rewrite a finding.
- `../../references/wikipedia-signs.md`: condensed Wikipedia signs of AI writing. Read only for deep dives on unfamiliar patterns.
````

- [ ] **Step 2: Verify the skill file passes its own engine**

Run: `python3 engine/voice_check.py --report-only skills/voice-check/SKILL.md`
Expected: exit 0. Findings about quoted rule names (e.g. the word "signal" appearing twice) are acceptable ONLY if they come from lines quoting the rule lists; there should be no dash findings. If dash findings appear, fix them.

- [ ] **Step 3: Commit**

```bash
git add skills/voice-check/SKILL.md
git commit -m "feat(skills): voice-check engine validator loop, checklist, third-person description

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Rewrite writing-guard SKILL.md

**Files:**
- Modify: `plugins/voice-check/skills/writing-guard/SKILL.md` (full replacement)

**Interfaces:**
- Consumes: same engine CLI as Task 6.

- [ ] **Step 1: Replace the file with exactly this content**

````markdown
---
name: writing-guard
description: Loads the writing rules before drafting prose and self-censors AI tells, em dashes, hedging, puffery, and promotional tone in real time while drafting. Use before writing any prose for the user, including emails, log entries, documents, summaries, messages, status updates, and reports. Proactive complement to voice-check.
---

# Writing Guard (proactive)

Internalize the rules first and self-edit while drafting, not after.

## Why this skill exists

The `voice-check` skill cleans up AI writing tells AFTER they appear in a file. `writing-guard` prevents them from appearing in the first place. Both skills use the same rule list. The difference is timing: guard fires before and during writing, voice-check fires after.

## Process

1. Read `../../references/rules.md` in full before writing anything (the file lives at the plugin root, two levels up from this skill directory, NOT inside the skill dir).
2. If the target context has a per-repo supplement at `.claude/voice-check.md` (walking up to the git root, first match wins), load those rules too.
3. As you draft, self-check each sentence against the rules. If a sentence triggers any rule, rewrite it before continuing. Do not finish the draft and clean up later.
4. After completing the draft, do one final pass against the rules.
5. If the draft was written to a file and `python3` is available, verify it: run `python3 ../../engine/voice_check.py --report-only <file>` (execute the script, do not read it), fix any findings, and re-run until it reports zero. The path is relative to this skill directory; resolve it against the installed plugin location.
6. If you cannot express something without violating a rule, prefer the rule over the original phrasing.

## When NOT to use this skill

- When transcribing the user's exact words (the rules are about generated prose, not user quotes)
- When writing code, code comments, or commit messages where dashes and technical jargon are appropriate
- When explicitly asked to mimic a specific style that conflicts with the rules

## References

- `../../references/rules.md`: the rule list (shared with voice-check, lives at the plugin root). Read it in step 1.
````

- [ ] **Step 2: Verify the skill file passes the engine**

Run: `python3 engine/voice_check.py --report-only skills/writing-guard/SKILL.md`
Expected: exit 0, no dash findings.

- [ ] **Step 3: Commit**

```bash
git add skills/writing-guard/SKILL.md
git commit -m "feat(skills): writing-guard numbered workflow, engine verification step, third-person description

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: README, full suite, end-to-end fixture verification

**Files:**
- Modify: `README.md` (rule category listing, engine category sentence, one em dash fix)
- Create: nothing permanent (scratch fixture only, not committed)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Update the README rule listing**

In `README.md`, in the bullet list around lines 14 through 20, add these bullets after the existing category bullets (match the existing bullet style):

```markdown
- **Faux-conversational bridges [engine]:** "here's the thing," "at the end of the day," "let's dive in," "we will explore"
- **2026 vocabulary [engine for phrases, skill for bare words]:** "quietly building," "this matters because," "built different," "decisions compound"; bare words (quietly, shift, matters, signal, compound) are judged in context by the skill
- **Markup artifacts [engine]:** leaked citation tokens (contentReference, oaicite, [cite:, grok_card, ppl-ai-file-upload), emoji used as bullet markers
```

Update the sentence at line 33 that enumerates engine categories: append "bridge phrases, 2026 vocabulary phrases, markup artifacts" to its parenthetical list.

Fix the em dash at line 31: change "Git pre-commit hook — fast Python rules engine, report-only, advisory" to "Git pre-commit hook: fast Python rules engine, report-only, advisory".

- [ ] **Step 2: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: ALL PASS (~42 cases).

- [ ] **Step 3: End-to-end engine loop verification with a seeded fixture**

Write a scratch file (scratchpad or /tmp equivalent, NOT in the repo) containing old tells, 2026 tells, and artifacts:

```markdown
Here's the thing, this pivotal shift is a testament to our vision.

The team is quietly building something that sends a signal to the market. :contentReference[oaicite:0]{index=0}

🚀 It's not about the product, it's about the journey.
```

Run: `python3 plugins/voice-check/engine/voice_check.py --report-only <scratch-file>`

Expected findings, at minimum: `bridge_phrases` (here's the thing), `ai_vocab_cluster` (pivotal and testament, 2+ old-cluster words), `puffery` (pivotal, testament), `vocab_2026` (quietly building, sends a signal), `markup_artifacts` (oaicite token, emoji bullet). The contrast reframe on the last line must NOT appear in engine output (it is skill-only). Then rewrite the scratch file to fix every engine finding, re-run, and confirm zero findings. This validates the exact loop Task 6's skill prescribes.

- [ ] **Step 4: Verify README and engine agree**

Run: `grep -c "bridge_phrases\|vocab_2026\|markup_artifacts" engine/rules.py`
Expected: nonzero. Confirm the three category names in README, rules.md, and rules.py all match.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): list new rule categories, fix em dash

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Post-implementation (manual, not a task)

Skill-level verification per the spec: invoke `/voice-check` on a seeded fixture in a real session and confirm the checklist flow runs the engine loop to zero findings and the manual pass catches a planted skill-only violation (e.g. a contrast reframe). This needs a live skill session and cannot be scripted here.
