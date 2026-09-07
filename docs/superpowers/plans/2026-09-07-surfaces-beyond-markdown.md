# Surfaces Beyond Markdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the voice-check engine see commit messages and plain text files, running a restricted rule set on commit messages because a commit message cannot carry a suppression comment.

**Architecture:** A `surface` parameter threads from the CLI through `scanner.scan` into both the rule pass and the analyzer pass. A single allowlist constant, `rules.COMMIT_SURFACE`, names the rule families safe to run without an escape hatch. A new `commit-msg` hook strips git's comments and verbose diff from the message file, then scans what remains with `--surface commit`. The installer and healer generalise over a list of hook names instead of hardcoding `pre-commit`.

**Tech Stack:** Python 3.11+ standard library only, pytest for tests, bash for hooks.

**Spec:** `docs/superpowers/specs/2026-09-07-surfaces-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- The engine stays Python standard library only. Adding a dependency is a plan failure.
- Python 3.11 or later. CI runs 3.11, 3.12, 3.13, and 3.14.
- Both hooks are advisory and MUST exit 0 in every case, including when the engine is missing, the message is empty, or the scan raises.
- The `# === voice-check section start ===` and `# === voice-check section end ===` markers are preserved exactly in both hook templates.
- **No dashes in any written output, anywhere.** Commit messages, code comments, docs, and Markdown prose use commas, colons, periods, or parentheses instead of em dashes, en dashes, or spaced hyphens. Compound word hyphens with no surrounding spaces are allowed. This applies to every commit message you write while executing this plan.
- Existing public behavior does not change: `scanner.scan` and `voice_check.scan` keep working for every current caller without passing a surface.
- Run the full suite from `plugins/voice-check` with `.venv/bin/python -m pytest tests/ -v`. If `.venv` does not exist, create it: `python3 -m venv .venv && .venv/bin/pip install pytest`.

---

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `plugins/voice-check/engine/rules.py` | Add `COMMIT_SURFACE`, the allowlist of rule names safe on commit messages | 1 |
| `plugins/voice-check/engine/scanner.py` | Thread `surface` through row selection and the analyzer pass | 1 |
| `plugins/voice-check/engine/voice_check.py` | `--surface` CLI flag, `surface` parameter on `scan` | 1 |
| `plugins/voice-check/tests/test_surfaces.py` | New. Surface filtering, the allowlist pin, the CLI flag | 1 |
| `plugins/voice-check/templates/commit-msg.sh` | New. The commit-msg hook template | 2 |
| `plugins/voice-check/templates/install-hook.sh` | Install every hook in a list, not just `pre-commit` | 3 |
| `plugins/voice-check/hooks/heal-hook.sh` | Heal every hook in a list, not just `pre-commit` | 3 |
| `plugins/voice-check/templates/pre-commit.sh` | Widen the staged file filter past markdown | 4 |
| `plugins/voice-check/tests/test_hook_pipeline.py` | Extend the existing harness for both hooks | 2, 3, 4 |
| `plugins/voice-check/skills/writing-guard/SKILL.md` | Remove the commit message exemption | 5 |
| `README.md`, `CLAUDE.md`, `plugins/voice-check/.claude-plugin/plugin.json` | Docs and version bump to 2.5.0 | 5 |

---

## Task 1: The surface concept in the engine

**Files:**
- Modify: `plugins/voice-check/engine/rules.py` (add a constant after `_SEVERITY_BY_NAME`, around line 37)
- Modify: `plugins/voice-check/engine/scanner.py:29-31` (`_select_rows`), `scanner.py:34` (`scan` signature), `scanner.py:119-120` (analyzer loop)
- Modify: `plugins/voice-check/engine/voice_check.py:84-91` (`scan`), `voice_check.py:138-147` (argument parser), `voice_check.py:168` (call site)
- Create: `plugins/voice-check/tests/test_surfaces.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `rules.COMMIT_SURFACE: frozenset[str]`, exactly `{"no_dashes", "markup_artifacts"}`
  - `scanner.scan(doc, cfg, rel_path="", line_ranges=None, surface="file") -> List[dict]`
  - `voice_check.scan(file_path, line_ranges=None, cfg=None, surface="file") -> List[dict]`
  - CLI flag `--surface {file,commit}` on `voice_check.py`, default `file`. Task 2's hook invokes `--report-only --surface commit <file>`.

**Context:** `_select_rows` is the single place row selection happens, so the filter belongs there. The analyzer pass at `scanner.py:119` iterates `analyzers.ANALYZERS` separately and needs the same filter, otherwise the `markup_artifacts.embedded_tokens` analyzer would be excluded from commit messages by accident and `structure.bold_headers` would be included by accident. Both loops call one shared helper so the rule lives in exactly one place.

- [ ] **Step 1: Write the failing tests**

Create `plugins/voice-check/tests/test_surfaces.py`:

<!-- voice-check: disable markup_artifacts -->

```python
"""Tests for the surface concept: which rules run on which kind of text.

A commit message cannot carry a `<!-- voice-check: ignore -->` comment, and
once written it is in history. The commit surface therefore runs an
allowlist rather than everything, and these tests pin that allowlist.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import analyzers  # noqa: E402
import config  # noqa: E402
import document  # noqa: E402
import rules  # noqa: E402
import scanner  # noqa: E402
import voice_check  # noqa: E402

ENGINE = Path(__file__).parent.parent / "engine" / "voice_check.py"


def _scan(text, surface="file", rel_path="a.md"):
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, config.Config.empty(), rel_path, None, surface)


# ---------------------------------------------------------------------------
# The allowlist pin
# ---------------------------------------------------------------------------

def test_commit_surface_is_pinned_exactly():
    """Adding a rule family without deciding about commit messages must fail
    here rather than start nagging on every commit in the field."""
    assert rules.COMMIT_SURFACE == frozenset({"no_dashes", "markup_artifacts"})


def test_every_commit_surface_name_is_a_real_rule_name():
    known = ({r["name"] for r in rules.RULES}
             | {a["name"] for a in analyzers.ANALYZERS})
    assert rules.COMMIT_SURFACE <= known


# ---------------------------------------------------------------------------
# The allowlist actually restricts
# ---------------------------------------------------------------------------

def test_commit_surface_keeps_dashes_and_drops_everything_else():
    """This single test pins the whole feature. Without it the surface filter
    could be a no op and nothing else would notice."""
    text = "Fix the thing - properly\n\nThis is a groundbreaking change.\n"

    on_files = {f["rule"] for f in _scan(text, surface="file")}
    assert on_files == {"no_dashes", "puffery", "promotional_tone"}

    on_commits = {f["rule"] for f in _scan(text, surface="commit")}
    assert on_commits == {"no_dashes"}


def test_commit_surface_reports_leaked_tokens():
    text = "Add the docs\n\nSee contentReference for details.\n"
    assert {f["rule"] for f in _scan(text, surface="commit")} == {"markup_artifacts"}


def test_file_surface_is_the_default_and_unchanged():
    text = "This is a groundbreaking change.\n"
    doc = document.Document.from_markdown(text)
    without = scanner.scan(doc, config.Config.empty(), "a.md")
    with_default = _scan(text, surface="file")
    assert {f["rule"] for f in without} == {f["rule"] for f in with_default}
    assert "puffery" in {f["rule"] for f in without}


def test_supplement_rules_never_reach_commit_messages():
    """A repo's custom word cannot be suppressed in a commit message any more
    than a built in can, so it does not run there."""
    cfg = config.Config.empty()
    cfg.extra_rows.append({
        "name": "supplement:word", "id": "supplement.word.synergy",
        "category": "supplement", "kind": "word", "pattern": "synergy",
        "message": "Supplement rule (word): 'synergy'.",
        "scope": "line", "severity": "medium",
    })
    doc = document.Document.from_markdown("We need more synergy here.\n")

    on_files = scanner.scan(doc, cfg, "a.md", None, "file")
    assert {f["rule"] for f in on_files} == {"supplement:word"}

    on_commits = scanner.scan(doc, cfg, "a.md", None, "commit")
    assert on_commits == []


# ---------------------------------------------------------------------------
# Analyzers obey the surface too
# ---------------------------------------------------------------------------

def test_embedded_token_analyzer_runs_on_commit_messages():
    text = "Add link\n\nSee https://example.com/a?utm_source=chatgpt.com now.\n"
    hits = {f["rule_id"] for f in _scan(text, surface="commit")}
    assert "markup_artifacts.embedded_tokens" in hits


def test_bold_header_analyzer_never_runs_on_commit_messages():
    """structure ships off by default, so enable it and confirm the surface
    filter still keeps it away from commit messages."""
    cfg = config.Config.empty()
    cfg.enabled.append(("structure.bold_headers", None))
    text = (
        "Summary\n\n"
        "- **One**: first thing\n"
        "- **Two**: second thing\n"
        "- **Three**: third thing\n"
        "- **Four**: fourth thing\n"
    )
    doc = document.Document.from_markdown(text)

    on_files = scanner.scan(doc, cfg, "a.md", None, "file")
    assert "structure.bold_headers" in {f["rule_id"] for f in on_files}

    on_commits = scanner.scan(doc, cfg, "a.md", None, "commit")
    assert "structure.bold_headers" not in {f["rule_id"] for f in on_commits}


# ---------------------------------------------------------------------------
# The CLI flag
# ---------------------------------------------------------------------------

def test_voice_check_scan_takes_a_surface(tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Fix the thing - properly\n\nA groundbreaking change.\n")
    assert {x["rule"] for x in voice_check.scan(f, surface="commit")} == {"no_dashes"}


def test_cli_surface_commit_reports_only_allowlisted_rules(tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Fix the thing - properly\n\nA groundbreaking change.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--min-severity", "low",
         "--surface", "commit", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "no_dashes" in r.stdout
    assert "puffery" not in r.stdout


def test_cli_defaults_to_the_file_surface(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("A groundbreaking change.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--min-severity", "low", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "puffery" in r.stdout


def test_cli_rejects_an_unknown_surface(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("Anything.\n")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "--report-only", "--surface", "email", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode == 2
```

<!-- voice-check: enable markup_artifacts -->

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_surfaces.py -v
```

Expected: collection succeeds, and every test fails. `test_commit_surface_is_pinned_exactly` fails with `AttributeError: module 'rules' has no attribute 'COMMIT_SURFACE'`; the `_scan` tests fail with `TypeError: scan() takes from 2 to 4 positional arguments but 5 were given`.

- [ ] **Step 3: Add the allowlist to `rules.py`**

Insert directly after the `_SEVERITY_BY_NAME` dict (which ends at line 37, before `def slug`):

```python
# Rule NAMES that may run against a commit message. Names, not ids, so a
# family covers all of its rows and its analyzer together.
#
# This is an allowlist, and the direction is the point. A commit message
# cannot carry a `<!-- voice-check: ignore -->` comment, and once written it
# is in history, so the surface with no escape hatch is the one that stays
# closed by default. A rule added later runs on files and does NOT run on
# commits until someone deliberately adds its name here. A denylist would
# mean every new rule silently starts firing on every commit until someone
# noticed. tests/test_surfaces.py pins this set exactly for the same reason.
COMMIT_SURFACE = frozenset({"no_dashes", "markup_artifacts"})
```

- [ ] **Step 4: Thread the surface through `scanner.py`**

Replace `_select_rows` (lines 29 to 31) with:

```python
def in_surface(row: dict, surface: str) -> bool:
    """True when this row or analyzer entry may run against this surface.

    Rule rows and analyzer registry entries share the "name" key, so one
    helper serves both passes and the allowlist lives in one place.
    """
    if surface != "commit":
        return True
    return row["name"] in rules.COMMIT_SURFACE


def _select_rows(cfg, rel_path: str, surface: str) -> List[dict]:
    rows = list(rules.RULES) + list(cfg.extra_rows)
    return [r for r in rows
            if in_surface(r, surface) and not cfg.is_disabled(r, rel_path)]
```

Change the `scan` signature at line 34 and its docstring:

```python
def scan(doc, cfg, rel_path: str = "", line_ranges=None,
         surface: str = "file") -> List[dict]:
    """Scan a Document and return findings tagged with severity.

    surface is "file" or "commit". The commit surface runs only the rule
    families named in rules.COMMIT_SURFACE, because a commit message cannot
    host a suppression comment. See in_surface above.
    """
```

Change the `_select_rows` call at line 39:

```python
    rows = _select_rows(cfg, rel_path, surface)
```

In the analyzer loop, change lines 119 and 120 from:

```python
    for entry in analyzers.ANALYZERS:
        if cfg.is_disabled(entry, rel_path):
```

to:

```python
    for entry in analyzers.ANALYZERS:
        if not in_surface(entry, surface):
            continue
        if cfg.is_disabled(entry, rel_path):
```

- [ ] **Step 5: Add the flag and parameter to `voice_check.py`**

Change `scan` (lines 84 to 91) to:

```python
def scan(file_path: Path, line_ranges=None, cfg: Optional[config.Config] = None,
         surface: str = "file") -> List[dict]:
    """Scan a file for writing rule violations. Return a list of findings."""
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if cfg is None:
        cfg = load_config(file_path)
    doc = document.Document.from_markdown(text)
    return scanner.scan(doc, cfg, rel_path=_rel_path(file_path),
                        line_ranges=line_ranges, surface=surface)
```

Add this argument after the `--lines` argument (line 146), inside `main`:

```python
    parser.add_argument("--surface", choices=["file", "commit"], default="file",
                        help="What kind of text this is. 'commit' runs only "
                             "the rules that are safe without a suppression "
                             "comment, since a commit message cannot carry one")
```

Change the `scan` call at line 168 to:

```python
        findings = scan(args.file, line_ranges=line_ranges, cfg=cfg,
                        surface=args.surface)
```

- [ ] **Step 6: Run the new tests to verify they pass**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_surfaces.py -v
```

Expected: PASS, all tests.

- [ ] **Step 7: Run the whole suite to verify nothing regressed**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

Expected: PASS, no failures. The existing suite calls `scanner.scan` and `voice_check.scan` without a surface, and both default to `"file"`.

- [ ] **Step 8: Commit**

```bash
git add plugins/voice-check/engine/rules.py plugins/voice-check/engine/scanner.py \
        plugins/voice-check/engine/voice_check.py plugins/voice-check/tests/test_surfaces.py
git commit -m "feat(engine): add the surface concept and the commit allowlist

A commit message cannot carry a suppression comment, so the commit surface
runs an allowlist of rule families rather than everything. The allowlist is
pinned by a test: a rule added later runs on files and stays off commits
until someone deliberately adds its name."
```

---

## Task 2: The commit-msg hook template

**Files:**
- Create: `plugins/voice-check/templates/commit-msg.sh`
- Modify: `plugins/voice-check/tests/test_hook_pipeline.py` (append a new section at the end of the file)

**Interfaces:**
- Consumes: the `--surface commit` CLI flag from Task 1.
- Produces: `templates/commit-msg.sh`, a hook template with the `__VOICE_CHECK_ENGINE__` placeholder, the `# === voice-check section start ===` and `# === voice-check section end ===` markers, and a `# voice-check hook version:` stamp. Task 3's installer renders and installs it. Its hook name is `commit-msg`.

**Context an implementer cannot know:**

Git passes the commit-msg hook one argument: the path to the message file. That file is NOT the message. It carries git's instruction comments, and under `commit.verbose` the entire staged diff below a scissors line (`# ------------------------ >8 ------------------------`).

`git stripspace --strip-comments` alone is NOT enough, and this is the single most likely bug in this task. It removes comment lines, including the scissors line itself, and leaves every diff line below it. Verified: a diff containing an em dash passes straight through and would be reported as a finding on the developer's commit message. The message must be cut at the scissors marker first, then passed through stripspace. Verified that a message with no scissors line loses nothing to the cut.

The scratch file goes inside the git directory rather than `/tmp` on purpose. `config.find_for` discovers a repo's `.claude/voice-check.md` by walking up from the scanned file to the git root, so a file in `/tmp` would silently miss the repo's supplement. A file at `<git common dir>/voice-check-commit-msg.scan` walks up to the repo root and finds it.

`resolve_engine` is copied verbatim from `templates/pre-commit.sh` lines 14 to 33. Copy it exactly; do not improve it. The two hooks resolving the engine differently would be a maintenance trap, and the `VOICE_CHECK_ENGINE` environment override in its first branch is what lets the tests below run the raw unrendered template.

Unlike `pre-commit.sh`, this hook exits silently when no engine resolves. The pre-commit hook already prints that notice on the same commit, and two hooks printing the same line would double the noise.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_hook_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# The commit-msg hook template
# ---------------------------------------------------------------------------

COMMIT_MSG_TEMPLATE = TEMPLATES_DIR / "commit-msg.sh"


def _run_commit_msg_template(repo: Path, message: str) -> subprocess.CompletedProcess:
    """Run the raw (unrendered) commit-msg template against a message file.

    The template's placeholder is not substituted here. resolve_engine's
    first branch reads $VOICE_CHECK_ENGINE, so pointing that at the in-repo
    engine exercises the real template without an install step.
    """
    msg_file = repo / ".git" / "COMMIT_EDITMSG"
    msg_file.parent.mkdir(parents=True, exist_ok=True)
    msg_file.write_text(message)

    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    env["VOICE_CHECK_ENGINE"] = str(ENGINE_FILE)
    return subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE), str(msg_file)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=env,
    )


def test_commit_msg_template_exists_with_markers_and_placeholder():
    assert COMMIT_MSG_TEMPLATE.is_file(), f"missing template: {COMMIT_MSG_TEMPLATE}"
    text = COMMIT_MSG_TEMPLATE.read_text()
    assert MARKER_START in text
    assert MARKER_END in text
    assert "__VOICE_CHECK_ENGINE__" in text
    assert "# voice-check hook version: " in text


def test_commit_msg_reports_an_em_dash(fresh_repo):
    r = _run_commit_msg_template(fresh_repo, "Fix the parser — nested quotes\n")
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" in combined


def test_commit_msg_stays_silent_on_a_clean_message(fresh_repo):
    r = _run_commit_msg_template(
        fresh_repo,
        "fix(engine): thread surface through the scanner\n"
        "\n"
        "Commit messages now run a restricted rule set.\n",
    )
    assert r.returncode == 0
    assert (r.stdout + r.stderr).strip() == ""


def test_commit_msg_applies_the_allowlist(fresh_repo):
    """Puffery is not on the commit allowlist; a dash is."""
    r = _run_commit_msg_template(
        fresh_repo, "Fix the thing - properly\n\nA groundbreaking change.\n")
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" in combined
    assert "puffery" not in combined


def test_commit_msg_ignores_git_comments_and_the_verbose_diff(fresh_repo):
    """The case most likely to catch a real bug.

    git stripspace --strip-comments removes the scissors line but leaves the
    diff beneath it, so the hook must cut at the scissors marker first.
    Without that cut this message reports an em dash from someone else's code.
    """
    message = (
        "Real message here\n"
        "\n"
        "# Please enter the commit message for your changes.\n"
        "# ------------------------ >8 ------------------------\n"
        "# Do not modify or remove the line above.\n"
        "diff --git a/x.md b/x.md\n"
        "+a line with an em dash — here\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "no_dashes" not in combined, (
        f"verbose diff was scanned:\n{combined}")


def test_commit_msg_keeps_the_body_when_there_is_no_scissors_line(fresh_repo):
    message = (
        "Subject line\n"
        "\n"
        "Body with an em dash — in it.\n"
        "\n"
        "# Please enter the commit message for your changes.\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    assert "no_dashes" in (r.stdout + r.stderr)


def test_commit_msg_is_silent_on_an_aborted_empty_message(fresh_repo):
    message = (
        "\n"
        "# Please enter the commit message for your changes.\n"
        "# Aborting commit due to empty commit message.\n"
    )
    r = _run_commit_msg_template(fresh_repo, message)
    assert r.returncode == 0
    assert (r.stdout + r.stderr).strip() == ""


def test_commit_msg_leaves_no_scratch_files_behind(fresh_repo):
    _run_commit_msg_template(fresh_repo, "Fix the parser — nested quotes\n")
    leftovers = sorted(p.name for p in (fresh_repo / ".git").glob("voice-check-*"))
    assert leftovers == [], f"scratch files left behind: {leftovers}"


def test_commit_msg_exits_zero_when_the_engine_is_missing(fresh_repo):
    msg_file = fresh_repo / ".git" / "COMMIT_EDITMSG"
    msg_file.parent.mkdir(parents=True, exist_ok=True)
    msg_file.write_text("Fix the parser — nested quotes\n")

    env = _git_env()
    env["HOME"] = str(fresh_repo / "empty-home")
    env["VOICE_CHECK_ENGINE"] = str(fresh_repo / "nope" / "voice_check.py")
    r = subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE), str(msg_file)],
        cwd=str(fresh_repo), capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0


def test_commit_msg_exits_zero_when_given_no_argument(fresh_repo):
    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    env["VOICE_CHECK_ENGINE"] = str(ENGINE_FILE)
    r = subprocess.run(
        ["bash", str(COMMIT_MSG_TEMPLATE)],
        cwd=str(fresh_repo), capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -k commit_msg -v
```

Expected: FAIL. `test_commit_msg_template_exists_with_markers_and_placeholder` fails its `is_file` assertion; the rest fail because bash cannot open the missing script.

- [ ] **Step 3: Write the template**

Create `plugins/voice-check/templates/commit-msg.sh`:

```bash
#!/usr/bin/env bash
# voice-check commit-msg hook (advisory, report-only)
# Installed by: voice-check plugin install-hook.sh
# === voice-check section start ===
# voice-check hook version: 2.4.0

set -e

# Baked at install time; fast path while it remains valid. If a plugin
# upgrade moves the cache directory, resolve_engine falls back to the
# newest installed version at commit time, so the hook self-heals.
BAKED_ENGINE="__VOICE_CHECK_ENGINE__"

resolve_engine() {
  if [ -n "${VOICE_CHECK_ENGINE:-}" ] && [ -f "${VOICE_CHECK_ENGINE:-}" ]; then
    echo "$VOICE_CHECK_ENGINE"
    return
  fi
  if [ -f "$BAKED_ENGINE" ]; then
    echo "$BAKED_ENGINE"
    return
  fi
  newest=$(find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
  if [ -n "$newest" ]; then
    echo "$newest"
    return
  fi
  if [ -f "$HOME/.claude/skills/voice-check/engine/voice_check.py" ]; then
    echo "$HOME/.claude/skills/voice-check/engine/voice_check.py"
    return
  fi
  true
}

MSG_FILE="$1"
if [ -z "$MSG_FILE" ] || [ ! -f "$MSG_FILE" ]; then
  exit 0
fi

ENGINE="$(resolve_engine)"

# Silent, unlike pre-commit.sh, which prints an "engine not found" notice.
# Both hooks run on the same commit, so the pre-commit hook already surfaces
# that notice and repeating it here would only double the noise.
if [ -z "$ENGINE" ]; then
  exit 0
fi

PYTHON="${VOICE_CHECK_PYTHON:-python3}"

# The scratch files live in the git directory, not /tmp, on purpose. The
# engine discovers a repo's .claude/voice-check.md by walking up from the
# scanned file to the git root, so a file in /tmp would silently miss this
# repo's supplement. From "<git dir>/voice-check-commit-msg.scan" the walk
# reaches the repo root and finds it.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac

CUT_FILE="$GIT_COMMON/voice-check-commit-msg.cut"
SCAN_FILE="$GIT_COMMON/voice-check-commit-msg.scan"
# Every exit path, including the failure paths. A hook that litters on every
# commit is its own defect.
trap 'rm -f "$CUT_FILE" "$SCAN_FILE"' EXIT

# The message file is not the message. It carries git's instruction comments,
# and under commit.verbose the entire staged diff below a scissors line.
#
# `git stripspace --strip-comments` alone is NOT enough: it strips the
# scissors line itself (a comment) and leaves every diff line beneath it, so
# an em dash in someone else's code would be reported as a finding on this
# commit message. Cut at the scissors marker FIRST, then strip comments.
# A message with no scissors line loses nothing to the cut.
#
# If either stage fails, fall back to the raw message file. That degrades
# toward reporting more, which is this project's stated principle, and the
# worst case is a finding on a comment line rather than a missed one.
if sed '/^#.*>8/,$d' "$MSG_FILE" > "$CUT_FILE" 2>/dev/null \
   && git stripspace --strip-comments < "$CUT_FILE" > "$SCAN_FILE" 2>/dev/null; then
  :
else
  cp "$MSG_FILE" "$SCAN_FILE" 2>/dev/null || exit 0
fi

# Empty after stripping means an aborted commit, not a clean one.
if [ ! -s "$SCAN_FILE" ]; then
  exit 0
fi

out=$("$PYTHON" "$ENGINE" --report-only --surface commit "$SCAN_FILE" 2>&1 || true)

if [ -n "$out" ]; then
  echo "voice-check: commit message findings (advisory only, commit will proceed)"
  echo "$out"
  echo "  to bypass: git commit --no-verify"
fi

exit 0
# === voice-check section end ===
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -k commit_msg -v
```

Expected: PASS, all eleven tests.

- [ ] **Step 5: Run the whole suite**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

Expected: PASS, no failures.

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/templates/commit-msg.sh plugins/voice-check/tests/test_hook_pipeline.py
git commit -m "feat(hooks): add an advisory commit-msg hook template

Cuts the message at git's scissors marker before running stripspace.
stripspace alone strips the scissors line and leaves the verbose diff, so
without the cut the hook would report findings from other people's code."
```

---

## Task 3: Installer and healer cover both hooks

**Files:**
- Modify: `plugins/voice-check/templates/install-hook.sh` (whole file restructure, see below)
- Modify: `plugins/voice-check/hooks/heal-hook.sh:12-59`
- Modify: `plugins/voice-check/tests/test_hook_pipeline.py` (append a new section at the end)

**Interfaces:**
- Consumes: `templates/commit-msg.sh` from Task 2, and the existing `templates/pre-commit.sh`.
- Produces: an installer that writes both `<git common dir>/hooks/pre-commit` and `<git common dir>/hooks/commit-msg`, and a healer that reinstalls when either one is stale.

**Context an implementer cannot know:**

The installer today hardcodes `pre-commit` in three places (`TEMPLATE`, `HOOK`, and nothing else structural) and the healer in four. Neither knows about a second hook. The fix is to extract the existing per hook logic into a function and call it once per name, NOT to duplicate the file.

The existing installer logic must be preserved exactly: the fresh install path, the "wipe v1 leftovers" path that detects a hook whose only meaningful content was voice-check's, the "replace the section, preserve other hooks" path, and the "append to an existing hook" path. Do not simplify any of them. They exist because users have non voice-check hooks.

Healer ruling, decided and recorded here so the implementer does not have to guess: the healer reinstalls when at least one hook carries the voice-check marker AND that hook is stale (dead baked path, or a version stamp that differs from the plugin's). It does NOT install a missing hook into a repo where no voice-check hook exists at all, because that repo never opted in. It also does not reinstall a `commit-msg` hook a user deliberately deleted while `pre-commit` is current. The field converges anyway: every existing install is stamped 2.4.0 or older, the version bump in Task 5 makes it stale, and one reinstall writes both hooks.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_hook_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# The installer and healer cover both hooks
# ---------------------------------------------------------------------------

def _commit_msg_hook_path(repo: Path) -> Path:
    return repo / ".git" / "hooks" / "commit-msg"


def test_installer_installs_both_hooks(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)

    for hook in (_hook_path(fresh_repo), _commit_msg_hook_path(fresh_repo)):
        assert hook.is_file(), f"not installed: {hook}"
        assert hook.stat().st_mode & stat.S_IXUSR, f"not executable: {hook}"
        text = hook.read_text()
        assert MARKER_START in text
        assert MARKER_END in text
        assert "__VOICE_CHECK_ENGINE__" not in text, f"placeholder left in {hook}"
        engine_line = next(
            (ln for ln in text.splitlines() if ln.startswith("BAKED_ENGINE=")), None)
        assert engine_line is not None, f"no BAKED_ENGINE line in {hook}"
        baked = engine_line.split("=", 1)[1].strip().strip('"')
        assert Path(baked).resolve() == ENGINE_FILE.resolve()


def test_installer_is_idempotent_for_both_hooks(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    _run_installer(fresh_repo, fake_home)

    for hook in (_hook_path(fresh_repo), _commit_msg_hook_path(fresh_repo)):
        text = hook.read_text()
        assert text.count(MARKER_START) == 1, f"duplicate section in {hook}"
        assert text.count(MARKER_END) == 1, f"duplicate section in {hook}"


def test_installer_preserves_a_foreign_commit_msg_hook(fresh_repo, fake_home):
    """A user's own commit-msg hook must survive, with our section appended."""
    hooks_dir = fresh_repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    foreign = hooks_dir / "commit-msg"
    foreign.write_text("#!/usr/bin/env bash\necho 'my own hook'\n")
    foreign.chmod(foreign.stat().st_mode | stat.S_IXUSR)

    _run_installer(fresh_repo, fake_home)

    text = foreign.read_text()
    assert "echo 'my own hook'" in text, "foreign commit-msg hook was clobbered"
    assert MARKER_START in text
    assert text.count(MARKER_START) == 1


def test_installed_commit_msg_hook_runs_end_to_end(fresh_repo, fake_home):
    """A real commit with a dashed message reports and still succeeds."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "notes.md", "All clean here.\n")

    env = _git_env()
    env["VOICE_CHECK_PYTHON"] = sys.executable
    r = subprocess.run(
        ["git", "-C", str(fresh_repo), "commit",
         "-m", "Fix the parser — nested quotes"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, f"commit blocked:\n{r.stdout}\n{r.stderr}"
    assert "no_dashes" in (r.stdout + r.stderr)

    log = subprocess.run(
        ["git", "-C", str(fresh_repo), "log", "--oneline"],
        capture_output=True, text=True, env=env)
    assert "Fix the parser" in log.stdout, "commit did not land"


def test_healer_reinstalls_both_hooks_when_pre_commit_is_stale(tmp_path):
    """A repo installed before this release has a stale pre-commit and no
    commit-msg hook at all. One heal must produce both, current."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, "0.0.1"))
    assert not (repo / ".git" / "hooks" / "commit-msg").exists()

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout

    version = _plugin_version()
    for name in ("pre-commit", "commit-msg"):
        text = (repo / ".git" / "hooks" / name).read_text()
        assert f"# voice-check hook version: {version}" in text, f"{name} not current"


def test_healer_reinstalls_when_only_the_commit_msg_hook_is_stale(tmp_path):
    """A half healed install, pre-commit current and commit-msg stale, is
    worse than an unhealed one because nothing surfaces the mismatch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    version = _plugin_version()
    _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, version))

    hooks_dir = repo / ".git" / "hooks"
    stale = hooks_dir / "commit-msg"
    stale.write_text(_hook_with_stamp(ENGINE_FILE, "0.0.1"))
    stale.chmod(stale.stat().st_mode | stat.S_IXUSR)

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    assert f"# voice-check hook version: {version}" in stale.read_text()


def test_healer_noop_when_both_hooks_are_current(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    version = _plugin_version()
    pre = _install_hook_text(repo, _hook_with_stamp(ENGINE_FILE, version))
    msg = repo / ".git" / "hooks" / "commit-msg"
    msg.write_text(_hook_with_stamp(ENGINE_FILE, version))
    msg.chmod(msg.stat().st_mode | stat.S_IXUSR)

    before = (pre.read_bytes(), msg.read_bytes())
    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert (pre.read_bytes(), msg.read_bytes()) == before


def test_healer_does_not_install_into_a_repo_that_never_opted_in(tmp_path):
    """No voice-check marker anywhere means this repo never asked for hooks."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=_git_env())
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n")

    home = tmp_path / "home"
    home.mkdir()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert not (hooks_dir / "commit-msg").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -k "both_hooks or commit_msg_hook or healer or foreign or idempotent" -v
```

Expected: FAIL. `test_installer_installs_both_hooks` fails with `not installed: .../hooks/commit-msg`; the healer tests fail because only `pre-commit` is rewritten.

- [ ] **Step 3: Generalise the installer**

Replace `plugins/voice-check/templates/install-hook.sh` in full:

```bash
#!/usr/bin/env bash
# Install the voice-check git hooks into a repo.
# Resolves the absolute path to the voice-check engine in the plugin cache
# at install time and embeds it as each hook's fast path. Installed hooks
# self-heal: they re-resolve the engine at commit time after upgrades, and
# the plugin's SessionStart healer rewrites stale hook sections.
# Re-running this installer is always safe (idempotent) but no longer
# required after upgrades.
#
# Two hooks are installed: pre-commit scans staged files, commit-msg scans
# the commit message itself with a restricted rule set.
#
# Usage: install-hook.sh [/path/to/repo]
# If no path given, uses the current directory.

set -e

REPO_DIR="${1:-$(pwd)}"
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Every hook this plugin installs. Each name maps to "<name>.sh" in the
# template directory and to "<name>" in the repo's hooks directory. Adding a
# hook means adding its name here and its template beside the others; nothing
# below is per hook. hooks/heal-hook.sh keeps its own copy of this list.
HOOK_NAMES="pre-commit commit-msg"

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git -C "$REPO_DIR" rev-parse --git-common-dir 2>/dev/null) || {
  echo "error: $REPO_DIR is not a git repo"
  exit 1
}
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$REPO_DIR/$GIT_COMMON" ;;
esac
HOOK_DIR="$GIT_COMMON/hooks"
MARKER_START="# === voice-check section start ==="
MARKER_END="# === voice-check section end ==="

for name in $HOOK_NAMES; do
  if [ ! -f "$TEMPLATE_DIR/$name.sh" ]; then
    echo "error: hook template not found at $TEMPLATE_DIR/$name.sh"
    exit 1
  fi
done

# Resolve the engine path. Prefer the plugin cache (marketplace install).
# Fall back to the legacy direct-clone location for users on v1.
ENGINE=""

# 1. Look in the plugin cache (marketplace install)
# Layout: ~/.claude/plugins/cache/voice-check/voice-check/<version>/engine/voice_check.py
PLUGIN_CACHE_HIT=$(find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
if [ -n "$PLUGIN_CACHE_HIT" ]; then
  ENGINE="$PLUGIN_CACHE_HIT"
fi

# 2. Fall back to legacy direct-clone path
if [ -z "$ENGINE" ] && [ -f "$HOME/.claude/skills/voice-check/engine/voice_check.py" ]; then
  ENGINE="$HOME/.claude/skills/voice-check/engine/voice_check.py"
fi

# 3. Last resort: walk up from the template's own location
if [ -z "$ENGINE" ]; then
  CANDIDATE="$(cd "$TEMPLATE_DIR/.." && pwd)/engine/voice_check.py"
  if [ -f "$CANDIDATE" ]; then
    ENGINE="$CANDIDATE"
  fi
fi

if [ -z "$ENGINE" ]; then
  echo "error: voice-check engine not found"
  echo "install via: claude plugin marketplace add RyanSinger/voice-check"
  echo "        and: claude plugin install voice-check@voice-check"
  exit 1
fi

echo "resolved engine: $ENGINE"

mkdir -p "$HOOK_DIR"

# Install one hook. $1 is the hook name, which is also its template basename.
# The four paths below (fresh, wiped v1 leftovers, replaced section, appended)
# are the original per hook logic, unchanged.
install_one() {
  name="$1"
  TEMPLATE="$TEMPLATE_DIR/$name.sh"
  HOOK="$HOOK_DIR/$name"

  # Render the template with the resolved engine path
  RENDERED=$(mktemp)
  sed "s|__VOICE_CHECK_ENGINE__|$ENGINE|" "$TEMPLATE" > "$RENDERED"

  if [ ! -f "$HOOK" ]; then
    # No existing hook, install fresh
    cp "$RENDERED" "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (fresh)"
    return 0
  fi

  # Existing hook present
  if grep -q "$MARKER_START" "$HOOK"; then
    # Voice-check section already present. Strip it and check what's left.
    STRIPPED=$(mktemp)
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
      $0 ~ start { skip=1; next }
      $0 ~ end { skip=0; next }
      !skip
    ' "$HOOK" > "$STRIPPED"

    # If the stripped file contains only boilerplate (shebang, comments, blanks,
    # and maybe a bare `exit 0`), the hook was entirely voice-check's. Wipe and
    # reinstall fresh to avoid orphaned exit statements from older templates.
    MEANINGFUL=$(grep -vE '^\s*$|^\s*#|^\s*exit 0\s*$|^#!' "$STRIPPED" | wc -l | tr -d ' ')
    if [ "$MEANINGFUL" = "0" ]; then
      cp "$RENDERED" "$HOOK"
      chmod +x "$HOOK"
      rm "$RENDERED" "$STRIPPED"
      echo "installed: $HOOK (wiped v1 leftovers and installed fresh)"
      return 0
    fi

    # Otherwise there's other content: append fresh section after the stripped file
    echo "" >> "$STRIPPED"
    cat "$RENDERED" >> "$STRIPPED"
    mv "$STRIPPED" "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (replaced voice-check section, preserved other hooks)"
  else
    # Append voice-check section to the end of the existing hook
    echo "" >> "$HOOK"
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
      $0 ~ start { in_section=1 }
      in_section { print }
      $0 ~ end { in_section=0 }
    ' "$RENDERED" >> "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (appended to existing hook)"
  fi
}

for name in $HOOK_NAMES; do
  install_one "$name"
done
```

Note for the implementer: the original script used `exit 0` inside those branches to end the whole program. Inside `install_one` they become `return 0`, which ends only that hook's installation. That change is required for the loop to reach the second hook, and the four transcribed branches are otherwise byte identical to the original.

- [ ] **Step 4: Generalise the healer**

Replace lines 12 to 59 of `plugins/voice-check/hooks/heal-hook.sh` (everything from `MARKER=` to the final `exit 0`) with:

```bash
MARKER="# === voice-check section start ==="

# Every hook this plugin installs. templates/install-hook.sh keeps its own
# copy of this list; the two must agree.
HOOK_NAMES="pre-commit commit-msg"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac

PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT:-}/.claude-plugin/plugin.json"
PLUGIN_VERSION=""
if [ -f "$PLUGIN_JSON" ]; then
  PLUGIN_VERSION=$(sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" | head -1)
fi

# FOUND records whether this repo ever opted in to voice-check hooks. A repo
# with no marked hook at all is not one we install into: the installer is the
# opt in, and healing must never become a back door for it. That also means a
# commit-msg hook a user deliberately deleted stays deleted while their
# pre-commit hook is current. Every install in the field is stamped 2.4.0 or
# older, so the version bump that ships this makes them stale and one heal
# writes both hooks anyway.
FOUND=0
NEEDS_HEAL=0

for name in $HOOK_NAMES; do
  HOOK="$GIT_COMMON/hooks/$name"
  [ -f "$HOOK" ] || continue
  grep -qF "$MARKER" "$HOOK" || continue
  FOUND=1

  # Old installs bake VOICE_CHECK_ENGINE=; the self-healing template bakes
  # BAKED_ENGINE=. Either way, a live path alone means nothing to heal, but
  # the version stamp check below can still trigger a reinstall.
  BAKED=$(sed -n 's/^BAKED_ENGINE="\(.*\)"$/\1/p; s/^VOICE_CHECK_ENGINE="\(.*\)"$/\1/p' "$HOOK" | head -1)
  [ -n "$BAKED" ] || continue
  [ -f "$BAKED" ] || NEEDS_HEAL=1

  # The dead path check above catches an engine that moved. It does not catch
  # a hook body that is simply outdated (for example, missing diff scoping
  # added in a later release) while its baked path still happens to resolve.
  # Compare the hook's own version stamp against the plugin's current
  # version and reinstall on any mismatch, absent or not. A plain string
  # inequality is enough here: we only need to know the stamp is not current,
  # not order it against every past version.
  if [ -n "$PLUGIN_VERSION" ]; then
    STAMP=$(sed -n 's/^# voice-check hook version: \(.*\)$/\1/p' "$HOOK" | head -1)
    if [ "$STAMP" != "$PLUGIN_VERSION" ]; then
      NEEDS_HEAL=1
    fi
  fi
done

[ "$FOUND" = "1" ] || exit 0
[ "$NEEDS_HEAL" = "1" ] || exit 0

INSTALLER="${CLAUDE_PLUGIN_ROOT:-}/templates/install-hook.sh"
[ -f "$INSTALLER" ] || exit 0

# The installer writes every hook in its list, so one run repairs the pair.
# A half healed install, where one hook is current and the other is stale,
# is worse than an unhealed one because nothing surfaces the mismatch.
if bash "$INSTALLER" "$REPO_ROOT" >/dev/null 2>&1; then
  echo "voice-check: healed stale git hooks in $REPO_ROOT"
fi
exit 0
```

Also update the file's header comment (lines 2 to 8) to:

```bash
# voice-check SessionStart healer.
# Repairs this repo's installed voice-check git hooks in two cases: the
# engine path baked into one stopped resolving (a plugin upgrade moved the
# cache directory), or a hook body itself is stale (a plugin upgrade changed
# what a template does, without necessarily moving the cache directory, so
# the dead path check alone would never catch it).
# Exits 0 in every case; a session must never break because of this hook.
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -v
```

Expected: PASS, every test in the module including the pre-existing ones.

Note: `test_healer_reinstalls_when_version_stamp_is_stale` and `test_healer_noop_when_version_stamp_is_current` (the pre-existing pair) still pass. The first now heals both hooks; it only asserts on `pre-commit`, which is still repaired. The second builds only a `pre-commit` hook at the current version, so `FOUND=1` and `NEEDS_HEAL=0`, and nothing is written.

- [ ] **Step 6: Run the whole suite**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

Expected: PASS, no failures.

- [ ] **Step 7: Commit**

```bash
git add plugins/voice-check/templates/install-hook.sh plugins/voice-check/hooks/heal-hook.sh \
        plugins/voice-check/tests/test_hook_pipeline.py
git commit -m "feat(hooks): install and heal both hooks from one list

The installer's four install paths move into a function called once per
hook name. The healer checks every hook and reinstalls when any is stale,
since one current hook beside one stale hook surfaces no mismatch."
```

---

## Task 4: Widen the pre-commit file filter

**Files:**
- Modify: `plugins/voice-check/templates/pre-commit.sh:44` and `:51`
- Modify: `plugins/voice-check/tests/test_hook_pipeline.py` (append a new section at the end)

**Interfaces:**
- Consumes: the installer from Task 3.
- Produces: no new interface. The pre-commit hook scans `.md`, `.markdown`, `.txt`, and `.rst` files.

**Context:** These files can carry `<!-- voice-check: ignore -->` comments, so they get the full rule set with no surface restriction. The extension list is fixed rather than configurable: the supplement already offers `voice-check-exclude` for opting out, and nobody has asked to opt an extension in. `.py` and other source files stay out; docstring extraction is a separate phase.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/voice-check/tests/test_hook_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# The widened file surface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", ["notes.txt", "guide.rst", "readme.markdown"])
def test_pre_commit_scans_the_widened_extensions(fresh_repo, fake_home, rel):
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, rel, "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert f"--- {rel} ---" in combined, f"{rel} was not scanned:\n{combined}"
    assert "no_dashes" in combined


def test_pre_commit_still_scans_markdown(fresh_repo, fake_home):
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "notes.md", "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    assert "--- notes.md ---" in (r.stdout + r.stderr)


def test_pre_commit_does_not_scan_source_files(fresh_repo, fake_home):
    """Docstring extraction is a separate phase. A .py file stays out."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "mod.py", '"""The plan is simple — ship it."""\n')

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    combined = r.stdout + r.stderr
    assert "mod.py" not in combined, f".py file was scanned:\n{combined}"
    assert "no_dashes" not in combined


def test_pre_commit_does_not_match_an_extension_mid_name(fresh_repo, fake_home):
    """`.txt` in the middle of a name is not a text file."""
    _run_installer(fresh_repo, fake_home)
    _stage_file(fresh_repo, "archive.txt.gz", "The plan is simple — ship it.\n")

    r = _run_hook(fresh_repo)
    assert r.returncode == 0
    assert "archive.txt.gz" not in (r.stdout + r.stderr)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -k "widened or source_files or mid_name or still_scans_markdown" -v
```

Expected: the three `widened_extensions` cases FAIL because the hook prints nothing for a non markdown file. `test_pre_commit_still_scans_markdown`, `test_pre_commit_does_not_scan_source_files`, and `test_pre_commit_does_not_match_an_extension_mid_name` PASS already, which is correct: they pin behavior that must survive the change.

- [ ] **Step 3: Widen the filter**

In `plugins/voice-check/templates/pre-commit.sh`, replace line 44:

```bash
staged_md=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$' || true)
```

with:

```bash
# Prose file extensions. Fixed rather than configurable: the supplement
# already offers voice-check-exclude for opting out, and nobody has asked to
# opt an extension in. These files can host suppression comments, so they get
# the full rule set. Source files stay out; docstrings are a separate phase.
staged_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(md|markdown|txt|rst)$' || true)
```

Then rename the variable at its two other uses. Line 46:

```bash
if [ -z "$staged_files" ]; then
```

Line 50 and 51:

```bash
count=$(echo "$staged_files" | wc -l | tr -d ' ')
echo "voice-check: scanning $count staged prose file(s)"
```

And line 109, the loop's input redirect:

```bash
done <<< "$staged_files"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -v
```

Expected: PASS, every test in the module. Verify no stale `staged_md` reference survives:

```bash
grep -n 'staged_md' plugins/voice-check/templates/pre-commit.sh
```

Expected: no output.

- [ ] **Step 5: Run the whole suite**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

Expected: PASS, no failures.

- [ ] **Step 6: Commit**

```bash
git add plugins/voice-check/templates/pre-commit.sh plugins/voice-check/tests/test_hook_pipeline.py
git commit -m "feat(hooks): scan staged txt, rst, and markdown files

These files can host suppression comments, so they get the full rule set.
Source files stay out; docstring extraction is a separate phase."
```

---

## Task 5: Documentation, the skill exemption, and the version bump

**Files:**
- Modify: `plugins/voice-check/skills/writing-guard/SKILL.md:26`
- Modify: `plugins/voice-check/.claude-plugin/plugin.json` (the `version` field)
- Modify: `plugins/voice-check/templates/pre-commit.sh:5` (version stamp)
- Modify: `plugins/voice-check/templates/commit-msg.sh:5` (version stamp)
- Modify: `README.md:119` (uninstall), `README.md:8`, `README.md:38`, `README.md:112`, `README.md:160-172` (structure listing)
- Modify: `CLAUDE.md` (hook installation flow section, engine module description, test count)
- Modify: `plugins/voice-check/tests/test_hook_pipeline.py` (append a version stamp consistency test)

**Interfaces:**
- Consumes: everything from Tasks 1 through 4.
- Produces: no code interface. This task makes the version stamp mechanism correct, which is what lets every existing install in the field pick up the new hooks.

**Context an implementer cannot know:**

The version bump is load bearing, not cosmetic. The healer compares each hook's `# voice-check hook version:` stamp against `plugin.json`'s `version`. If the stamp is not bumped, every existing install stays at 2.4.0, matches the plugin version, and never heals, so nobody in the field gets the commit-msg hook. Bump `plugin.json` and BOTH template stamps to `2.5.0` together.

The `writing-guard` exemption at SKILL.md line 26 currently contradicts `CLAUDE.md`, which states the no dashes rule applies to "commit messages, docs, comments, and Markdown prose". `CLAUDE.md` is authoritative. The exemption narrows to code and code comments only.

Watch the project's own rule while editing prose: no em dashes, no en dashes, no spaced hyphens, in any file you touch here.

- [ ] **Step 1: Write the failing test**

Append to `plugins/voice-check/tests/test_hook_pipeline.py`:

```python
# ---------------------------------------------------------------------------
# Version stamps
# ---------------------------------------------------------------------------

def test_every_hook_template_stamps_the_current_plugin_version():
    """The healer compares each hook's stamp against plugin.json. A template
    left at an older stamp means that hook heals on every session start
    forever; a template ahead of plugin.json means it never heals at all."""
    version = _plugin_version()
    for template in (PRE_COMMIT_TEMPLATE, COMMIT_MSG_TEMPLATE):
        text = template.read_text()
        assert f"# voice-check hook version: {version}" in text, (
            f"{template.name} is not stamped {version}")
```

- [ ] **Step 2: Run the test to verify it fails**

First bump `plugins/voice-check/.claude-plugin/plugin.json` only, changing `"version": "2.4.0"` to `"version": "2.5.0"`, then run:

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -k version_stamp -v
```

Expected: FAIL with `pre-commit.sh is not stamped 2.5.0`. This is the correct failure: it proves the test detects the exact drift that would silently strand every install in the field.

- [ ] **Step 3: Bump both template stamps**

In `plugins/voice-check/templates/pre-commit.sh` line 5 and `plugins/voice-check/templates/commit-msg.sh` line 5, change:

```bash
# voice-check hook version: 2.4.0
```

to:

```bash
# voice-check hook version: 2.5.0
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/test_hook_pipeline.py -v
```

Expected: PASS, every test in the module.

- [ ] **Step 5: Fix the writing-guard exemption**

In `plugins/voice-check/skills/writing-guard/SKILL.md`, replace line 26:

```markdown
- When writing code, code comments, or commit messages where dashes and technical jargon are appropriate
```

with:

```markdown
- When writing code itself, where dashes and technical jargon are part of the syntax or the domain
```

Commit messages and code comments are both covered by the rules, per `CLAUDE.md`. The commit-msg hook now checks the former.

- [ ] **Step 6: Update the README**

Change line 8 from:

```markdown
Both skills share a single rule list, a Python rules engine, and per-repo supplement support. Includes an advisory git pre-commit hook for the reactive path.
```

to:

```markdown
Both skills share a single rule list, a Python rules engine, and per-repo supplement support. Includes advisory git hooks for the reactive path: pre-commit scans staged prose files, commit-msg scans the commit message itself.
```

Change line 38 from:

```markdown
   - Git pre-commit hook: fast Python rules engine, report-only, advisory
```

to:

```markdown
   - Git hooks: fast Python rules engine, report-only, advisory
```

Change line 112 from:

```markdown
### Install the git pre-commit hook in a repo
```

to:

```markdown
### Install the git hooks in a repo
```

Replace line 119 in full:

```markdown
The installer is idempotent, and installs two hooks: `pre-commit` and `commit-msg`. If a hook of either name already exists, it appends a marked voice-check section rather than overwriting. To uninstall, delete the section between `# === voice-check section start ===` and `# === voice-check section end ===` from both `.git/hooks/pre-commit` and `.git/hooks/commit-msg`.

`pre-commit` scans staged `.md`, `.markdown`, `.txt`, and `.rst` files with the full rule set. `commit-msg` scans the commit message with a restricted set: only `no_dashes` and `markup_artifacts`. A commit message cannot carry a `<!-- voice-check: ignore -->` comment, and once written it is in history, so the surface with no escape hatch runs an allowlist. See `COMMIT_SURFACE` in `engine/rules.py`.
```

In the structure listing, change the `templates/` block (lines 167 and 168) to:

```
    templates/
      pre-commit.sh             Staged file hook template (with placeholder)
      commit-msg.sh             Commit message hook template (with placeholder)
      install-hook.sh           Per-repo installer for both hooks
```

And add the new test module to the `tests/` listing:

```
    tests/
      test_engine.py, test_document.py, test_config.py, test_scanner.py,
      test_hook_pipeline.py, test_skill_paths.py, test_regressions.py,
      test_analyzers.py, test_structure.py, test_surfaces.py
      fixtures/                 Sample clean and dirty markdown files
```

- [ ] **Step 7: Update CLAUDE.md**

In the `### Hook installation flow` section, replace the paragraph beginning "`templates/pre-commit.sh` contains a `__VOICE_CHECK_ENGINE__` placeholder" with:

```markdown
`templates/pre-commit.sh` and `templates/commit-msg.sh` each contain a `__VOICE_CHECK_ENGINE__` placeholder and a `# voice-check hook version:` stamp. `templates/install-hook.sh` substitutes the absolute path to `engine/voice_check.py` inside the installed plugin cache and writes a marked section (`# === voice-check section start/end ===`) into each hook in `HOOK_NAMES`. The installer is idempotent and appends rather than overwriting. Installed hooks self-heal across upgrades: each re-resolves the engine from the newest plugin cache version at commit time, and the plugin's SessionStart hook (`hooks/heal-hook.sh`, registered in `hooks/hooks.json`) reinstalls both when either one's stamp falls behind `plugin.json`. `HOOK_NAMES` is duplicated in the installer and the healer; the two must agree. Bumping the plugin version without bumping both template stamps strands every install in the field, so `tests/test_hook_pipeline.py` pins them together.
```

In the numbered architecture list, extend the `scanner.py` description by appending this sentence to item 3:

```markdown
`scanner.scan` takes a `surface` of `"file"` or `"commit"`, and `in_surface` filters both the rule pass and the analyzer pass against `rules.COMMIT_SURFACE`, an allowlist of rule names safe to run on text that cannot carry a suppression comment.
```

Update the test count in the `## Commands` section. Get the real number first:

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```

Then edit the line `Run the engine tests (211 pytest cases across ...)` to state the count that command reports.

- [ ] **Step 8: Verify the engine finds nothing in the docs you edited**

```bash
cd plugins/voice-check && for f in ../../README.md ../../CLAUDE.md skills/writing-guard/SKILL.md; do
  echo "=== $f ==="
  .venv/bin/python engine/voice_check.py --report-only --min-severity low "$f"
done
```

Expected: `README.md` and `CLAUDE.md` may report pre-existing findings on lines you did not touch. Nothing you added may introduce a `no_dashes` finding. If a line you wrote is reported, rewrite it with a comma, colon, or period.

- [ ] **Step 9: Run the whole suite**

```bash
cd plugins/voice-check && .venv/bin/python -m pytest tests/ -q
```

Expected: PASS, no failures.

- [ ] **Step 10: Verify on every supported Python version if available**

```bash
cd plugins/voice-check
for v in 3.11 3.12 3.13 3.14; do
  command -v python$v >/dev/null 2>&1 || { echo "python$v not installed, skipped"; continue; }
  echo "=== python$v ==="
  python$v -m pytest tests/ -q 2>&1 | tail -2
done
```

Expected: PASS on every version present. Any version missing locally is covered by CI's matrix in `.github/workflows/test.yml`. If none beyond the default are installed, say so in the report rather than claiming the matrix passed.

- [ ] **Step 11: Commit**

```bash
git add plugins/voice-check/.claude-plugin/plugin.json \
        plugins/voice-check/templates/pre-commit.sh \
        plugins/voice-check/templates/commit-msg.sh \
        plugins/voice-check/skills/writing-guard/SKILL.md \
        plugins/voice-check/tests/test_hook_pipeline.py \
        README.md CLAUDE.md
git commit -m "docs: cover both hooks, drop the commit message exemption, bump to 2.5.0

The writing-guard skill exempted commit messages, contradicting CLAUDE.md,
which is authoritative. The version bump is load bearing: the healer compares
each hook stamp against plugin.json, so without it no existing install picks
up the commit-msg hook. A test pins the stamps to plugin.json."
```

---

## Deliberately not implemented

The spec's "Merge commits are not special cased" section requires no code and
no task. An auto generated "Merge pull request #7 from ..." message runs the
same allowlist as any other message, which is what happens when nothing
special cases it. If a pull request title carries an em dash, that really does
enter the history and the finding is legitimate. Do not add a merge detection
branch to `commit-msg.sh`.

The spec's "No new constructor" section is likewise a decision not to build
something. `Document.from_markdown` handles commit messages and plain text
correctly, verified by measurement over 89 real commit messages. Do not add a
`from_plain` constructor to `document.py`.

## Success Criteria

Verify each of these before calling the plan done. They come from the spec.

1. A commit message containing an em dash reports one finding and the commit still succeeds. (Task 3, `test_installed_commit_msg_hook_runs_end_to_end`)
2. A commit message containing puffery, hedging, or a structural frame reports nothing. (Task 2, `test_commit_msg_applies_the_allowlist`)
3. A commit message containing a leaked token reports it. (Task 1, `test_commit_surface_reports_leaked_tokens`)
4. Git's instruction comments and a verbose diff in the message file produce no findings. (Task 2, `test_commit_msg_ignores_git_comments_and_the_verbose_diff`)
5. `COMMIT_SURFACE` is pinned by a test. (Task 1, `test_commit_surface_is_pinned_exactly`)
6. A supplement's custom word fires on a markdown file and not on a commit message. (Task 1, `test_supplement_rules_never_reach_commit_messages`)
7. Staged `.txt` and `.rst` files are scanned with the full rule set; a `.py` file is not. (Task 4)
8. One installer run installs both hooks, and the healer repairs both. (Task 3)
9. Both hooks exit 0 in every case, including when the engine is missing entirely. (Task 2 for commit-msg, existing coverage for pre-commit)
10. `skills/writing-guard/SKILL.md` no longer exempts commit messages. (Task 5)
11. The README's uninstall instructions name both hooks. (Task 5)
12. The full suite passes on Python 3.11 through 3.14. (Task 5, Step 10, plus CI)
