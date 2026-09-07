"""Tests for voice-check rules engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

import voice_check  # noqa: E402


def test_scan_clean_file_returns_no_findings(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("The plan is simple. Ship the MVP. Iterate based on real usage.\n")
    findings = voice_check.scan(f)
    assert findings == []


def test_em_dash_detected(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("The plan is simple \u2014 ship the MVP first.\n")
    findings = voice_check.scan(f)
    assert len(findings) == 1
    assert findings[0]["rule"] == "no_dashes"
    assert findings[0]["line"] == 1
    assert "\u2014" in findings[0]["snippet"]


def test_en_dash_detected(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Pages 10\u201315 cover this.\n")
    findings = voice_check.scan(f)
    assert len(findings) == 1
    assert findings[0]["rule"] == "no_dashes"


def test_hyphen_as_separator_detected(tmp_path):
    f = tmp_path / "dirty.md"
    # spaced hyphen used as a sentence break
    f.write_text("The plan is simple - ship fast.\n")
    findings = voice_check.scan(f)
    assert len(findings) == 1
    assert findings[0]["rule"] == "no_dashes"


def test_compound_word_hyphen_not_flagged(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("The voice-check skill uses first-person voice.\n")
    findings = voice_check.scan(f)
    assert findings == []


def test_single_ai_vocab_word_not_flagged(tmp_path):
    f = tmp_path / "ok.md"
    f.write_text("This is a crucial meeting tomorrow.\n")
    findings = voice_check.scan(f)
    # One word from the cluster is OK
    cluster_findings = [f for f in findings if f["rule"] == "ai_vocab_cluster"]
    assert cluster_findings == []


def test_two_ai_vocab_words_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("The pivotal moment arrived. This is a crucial decision.\n")
    findings = voice_check.scan(f)
    cluster_findings = [f for f in findings if f["rule"] == "ai_vocab_cluster"]
    assert len(cluster_findings) == 1
    assert "pivotal" in cluster_findings[0]["message"].lower() or "crucial" in cluster_findings[0]["message"].lower()


def test_three_ai_vocab_words_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("This pivotal shift represents a crucial moment, leveraging enduring patterns.\n")
    findings = voice_check.scan(f)
    cluster_findings = [f for f in findings if f["rule"] == "ai_vocab_cluster"]
    assert len(cluster_findings) == 1


def test_additionally_fires_only_when_sentence_initial(tmp_path):
    """rules.md documents this member as "Additionally (starting
    sentences)," not a bare word. A bullet list item is one of the most
    common places a sentence starts, and mask_line reduces its marker to a
    single leading space, so that case must fire too. "pivotal" is the
    second cluster word each case needs to clear doc_min=2.
    """
    f = tmp_path / "dirty.md"
    f.write_text("- Additionally, this shift is pivotal.\n")
    findings = voice_check.scan(f)
    cluster_findings = [x for x in findings if x["rule"] == "ai_vocab_cluster"]
    assert len(cluster_findings) == 1

    g = tmp_path / "ok.md"
    g.write_text("We should additionally consider this pivotal detail.\n")
    findings = voice_check.scan(g)
    cluster_findings = [x for x in findings if x["rule"] == "ai_vocab_cluster"]
    assert cluster_findings == []


def test_align_with_fires_only_as_adjacent_phrase(tmp_path):
    """rules.md documents this member as "align with," not bare "align."
    "pivotal" is the second cluster word each case needs to clear
    doc_min=2, so each result isolates whether "align" itself counted.
    """
    f = tmp_path / "dirty.md"
    f.write_text("Align with the schema before shipping; this detail is pivotal.\n")
    findings = voice_check.scan(f)
    cluster_findings = [x for x in findings if x["rule"] == "ai_vocab_cluster"]
    assert len(cluster_findings) == 1

    g = tmp_path / "ok.md"
    g.write_text("Align the config with the schema; this detail is pivotal.\n")
    findings = voice_check.scan(g)
    cluster_findings = [x for x in findings if x["rule"] == "ai_vocab_cluster"]
    assert cluster_findings == []


def test_puffery_word_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("This is a groundbreaking system.\n")
    findings = voice_check.scan(f)
    puffery = [f for f in findings if f["rule"] == "puffery"]
    assert len(puffery) >= 1


def test_promotional_phrase_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Nestled in the heart of the city, our office boasts amazing views.\n")
    findings = voice_check.scan(f)
    promo = [f for f in findings if f["rule"] == "promotional_tone"]
    assert len(promo) >= 1


import subprocess
import sys


def test_cli_clean_file_returns_zero():
    result = subprocess.run(
        [sys.executable,
         "engine/voice_check.py", "--report-only", "tests/fixtures/clean.md"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_cli_dirty_file_reports_findings():
    result = subprocess.run(
        [sys.executable,
         "engine/voice_check.py", "--report-only", "tests/fixtures/dirty-universal.md"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    # Report-only should always exit 0 (advisory)
    assert result.returncode == 0
    assert "no_dashes" in result.stdout or "ai_vocab" in result.stdout or "puffery" in result.stdout
    assert len(result.stdout) > 0


# ---------------------------------------------------------------------------
# New rule categories (variant B, data-driven table)
# ---------------------------------------------------------------------------

def test_hedging_phrase_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("I would like to help with the rollout.\n")
    findings = voice_check.scan(f)
    hedging = [x for x in findings if x["rule"] == "hedging"]
    assert len(hedging) >= 1


def test_hedging_not_flagged_on_neutral_sentence(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("I own the rollout. Ready to ship Friday.\n")
    findings = voice_check.scan(f)
    hedging = [x for x in findings if x["rule"] == "hedging"]
    assert hedging == []


def test_copula_avoidance_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("The platform serves as a foundation for growth.\n")
    findings = voice_check.scan(f)
    copula = [x for x in findings if x["rule"] == "copula_avoidance"]
    assert len(copula) >= 1


def test_copula_avoidance_not_flagged_on_is(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("The platform is the foundation.\n")
    findings = voice_check.scan(f)
    copula = [x for x in findings if x["rule"] == "copula_avoidance"]
    assert copula == []


def test_dangling_participle_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("We shipped the feature, highlighting the importance of speed.\n")
    findings = voice_check.scan(f)
    dangling = [x for x in findings if x["rule"] == "dangling_participle"]
    assert len(dangling) >= 1


def test_dangling_participle_not_flagged_on_plain_sentence(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("We shipped the feature on Tuesday.\n")
    findings = voice_check.scan(f)
    dangling = [x for x in findings if x["rule"] == "dangling_participle"]
    assert dangling == []


def test_vague_attribution_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Experts say the trend will continue into next year.\n")
    findings = voice_check.scan(f)
    vague = [x for x in findings if x["rule"] == "vague_attribution"]
    assert len(vague) >= 1


def test_vague_attribution_not_flagged_with_named_source(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("Per the 2025 Stack Overflow survey, the trend will continue.\n")
    findings = voice_check.scan(f)
    vague = [x for x in findings if x["rule"] == "vague_attribution"]
    assert vague == []


def test_supplement_rule_applied_from_fenced_block(tmp_path):
    # Create a fake repo with a supplement that bans "flagship"
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "voice-check.md").write_text(
        "# supplement\n\n"
        "```voice-check-words\n"
        "flagship\n"
        "```\n"
    )
    doc = tmp_path / "doc.md"
    doc.write_text("Our flagship product launches Monday.\n")
    findings = voice_check.scan(doc)
    sup = [x for x in findings if x["rule"].startswith("supplement:")]
    assert len(sup) >= 1
    assert any("flagship" in x["message"].lower() for x in sup)


def test_supplement_phrase_block_applied(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "voice-check.md").write_text(
        "```voice-check-phrases\n"
        "best in class\n"
        "```\n"
    )
    doc = tmp_path / "doc.md"
    doc.write_text("We deliver best in class support.\n")
    findings = voice_check.scan(doc)
    sup = [x for x in findings if x["rule"].startswith("supplement:")]
    assert len(sup) >= 1


# ---------------------------------------------------------------------------
# Markdown structural safety (gen 3, criterion 8)
# ---------------------------------------------------------------------------

def test_nested_bullet_list_not_flagged_as_hyphen_separator(tmp_path):
    f = tmp_path / "bullets.md"
    f.write_text(
        "# Heading\n"
        "\n"
        "- Top level item\n"
        "  - Nested bullet one\n"
        "    - Even deeper bullet\n"
        "* Star bullet item\n"
        "+ Plus bullet item\n"
    )
    findings = voice_check.scan(f)
    dashes = [x for x in findings if x["rule"] == "no_dashes"]
    assert dashes == [], f"expected no dash findings, got: {dashes}"


def test_fenced_code_block_contents_not_scanned(tmp_path):
    f = tmp_path / "code.md"
    f.write_text(
        "Prose line above.\n"
        "\n"
        "```bash\n"
        "ls -la\n"
        "grep -r foo .\n"
        "echo \"crucial pivotal testament\"\n"
        "```\n"
        "\n"
        "Prose line below.\n"
    )
    findings = voice_check.scan(f)
    # The hyphen separators inside the code block must not fire.
    dashes = [x for x in findings if x["rule"] == "no_dashes"]
    assert dashes == [], f"expected no dash findings, got: {dashes}"
    # The ai_vocab cluster words inside the code block must not fire either.
    cluster = [x for x in findings if x["rule"] == "ai_vocab_cluster"]
    assert cluster == [], f"expected no cluster findings, got: {cluster}"
    # Puffery word inside the code block must not fire.
    puffery = [x for x in findings if x["rule"] == "puffery"]
    assert puffery == [], f"expected no puffery findings, got: {puffery}"


def test_inline_code_span_not_scanned(tmp_path):
    f = tmp_path / "inline.md"
    f.write_text(
        "Run `ls -la` to list files and use `foo-bar` as the identifier.\n"
    )
    findings = voice_check.scan(f)
    dashes = [x for x in findings if x["rule"] == "no_dashes"]
    assert dashes == [], f"expected no dash findings, got: {dashes}"


def test_clean_fixture_structural_cases_pass(tmp_path):
    # Point directly at the shipped clean.md fixture to ensure the expanded
    # structural cases (heading, nested list, fenced code, inline code, table)
    # all remain clean after the bug fix.
    fixture = Path(__file__).parent / "fixtures" / "clean.md"
    findings = voice_check.scan(fixture)
    assert findings == [], f"clean fixture produced findings: {findings}"


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
    f.write_text("In this section, we cover the deployment pipeline.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert len(bridges) >= 1


def test_bridge_phrase_not_flagged_on_similar_words(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("He got me wrong. The day shift ends at five.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert bridges == []


def test_bridge_phrase_curly_apostrophe_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("Here’s the thing, the rollout slipped.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert len(bridges) >= 1


def test_bridge_end_of_day_shift_not_flagged(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("We clock out at the end of the day shift.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert bridges == []


def test_bridge_end_of_the_day_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("At the end of the day, the migration was worth it.\n")
    findings = voice_check.scan(f)
    bridges = [x for x in findings if x["rule"] == "bridge_phrases"]
    assert len(bridges) >= 1


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


def test_star_emoji_bullet_flagged(tmp_path):
    f = tmp_path / "dirty.md"
    f.write_text("⭐ Ship the feature\n")
    findings = voice_check.scan(f)
    artifacts = [x for x in findings if x["rule"] == "markup_artifacts"]
    assert len(artifacts) >= 1


# ---------------------------------------------------------------------------
# Hook self-healing: template runtime resolution + SessionStart healer
# ---------------------------------------------------------------------------

import os
import stat

PLUGIN_ROOT = Path(__file__).parent.parent
HOOK_TEMPLATE = PLUGIN_ROOT / "templates" / "pre-commit.sh"
HEALER_SCRIPT = PLUGIN_ROOT / "hooks" / "heal-hook.sh"
ENGINE_SRC_DIR = PLUGIN_ROOT / "engine"


def _make_fake_home(tmp_path, versions):
    """Build a fake HOME containing a plugin cache with the given versions."""
    home = tmp_path / "home"
    for v in versions:
        dst = (home / ".claude" / "plugins" / "cache" / "voice-check"
               / "voice-check" / v / "engine")
        dst.mkdir(parents=True)
        for f in ENGINE_SRC_DIR.glob("*.py"):
            (dst / f.name).write_text(f.read_text())
    home.mkdir(exist_ok=True)
    return home


def _make_repo(tmp_path, hook_text=None):
    """Init a git repo; optionally install pre-commit hook content."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if hook_text is not None:
        hooks_dir = repo / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook = hooks_dir / "pre-commit"
        hook.write_text(hook_text)
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    return repo


def _render_hook(engine_path):
    return HOOK_TEMPLATE.read_text().replace(
        "__VOICE_CHECK_ENGINE__", str(engine_path))


def _run_hook(repo, home):
    return subprocess.run(
        ["bash", str(repo / ".git" / "hooks" / "pre-commit")],
        cwd=str(repo), capture_output=True, text=True,
        env={**os.environ, "HOME": str(home)},
    )


def _stage_dirty_md(repo):
    doc = repo / "dirty.md"
    doc.write_text("The plan is simple \u2014 ship it.\n")
    subprocess.run(["git", "-C", str(repo), "add", "dirty.md"], check=True)


def test_hook_resolves_newest_cache_when_baked_path_dead(tmp_path):
    home = _make_fake_home(tmp_path, ["2.1.0", "2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, _render_hook(dead))
    _stage_dirty_md(repo)
    result = _run_hook(repo, home)
    assert result.returncode == 0
    assert "no_dashes" in result.stdout
    assert "engine not found" not in result.stdout


def test_hook_advisory_when_no_engine_anywhere(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, _render_hook(dead))
    _stage_dirty_md(repo)
    result = _run_hook(repo, home)
    assert result.returncode == 0
    assert "engine not found" in result.stdout


# ---------------------------------------------------------------------------
# SessionStart healer tests
# ---------------------------------------------------------------------------

OLD_STYLE_HOOK = """#!/usr/bin/env bash
# === voice-check section start ===
VOICE_CHECK_ENGINE="{engine}"
if [ ! -f "$VOICE_CHECK_ENGINE" ]; then
  echo "voice-check: engine not found at $VOICE_CHECK_ENGINE"
  exit 0
fi
exit 0
# === voice-check section end ===
"""


def _run_healer(cwd, home):
    return subprocess.run(
        ["bash", str(HEALER_SCRIPT)],
        cwd=str(cwd), capture_output=True, text=True,
        env={**os.environ, "HOME": str(home),
             "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)},
    )


def test_healer_replaces_stale_section(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=dead))
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    hook = repo / ".git" / "hooks" / "pre-commit"
    text = hook.read_text()
    assert "resolve_engine" in text
    assert os.access(hook, os.X_OK)


def test_healer_noop_when_baked_path_healthy(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    live = (home / ".claude" / "plugins" / "cache" / "voice-check"
            / "voice-check" / "2.2.0" / "engine" / "voice_check.py")
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=live))
    before = (repo / ".git" / "hooks" / "pre-commit").read_bytes()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert "healed" not in result.stdout
    assert (repo / ".git" / "hooks" / "pre-commit").read_bytes() == before


def test_healer_noop_without_marker(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    repo = _make_repo(tmp_path, "#!/bin/sh\nexit 0\n")
    before = (repo / ".git" / "hooks" / "pre-commit").read_bytes()
    result = _run_healer(repo, home)
    assert result.returncode == 0
    assert (repo / ".git" / "hooks" / "pre-commit").read_bytes() == before


def test_healer_noop_outside_git_repo(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    plain = tmp_path / "plain"
    plain.mkdir()
    result = _run_healer(plain, home)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Worktree support: installer and healer resolve the shared hooks dir
# ---------------------------------------------------------------------------

_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.invalid",
}


def _add_worktree(repo, tmp_path):
    """Commit once (worktree add needs a HEAD), then add a linked worktree."""
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init", "-q"],
        check=True, env={**os.environ, **_GIT_IDENTITY},
    )
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", str(wt)],
        check=True, env={**os.environ, **_GIT_IDENTITY},
    )
    return wt


def test_installer_from_worktree_writes_shared_hook(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    repo = _make_repo(tmp_path)
    wt = _add_worktree(repo, tmp_path)
    installer = PLUGIN_ROOT / "templates" / "install-hook.sh"
    result = subprocess.run(
        ["bash", str(installer), str(wt)],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(home)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    hook = repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert "voice-check section start" in hook.read_text()
    assert os.access(hook, os.X_OK)


def test_healer_heals_from_worktree(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=dead))
    wt = _add_worktree(repo, tmp_path)
    result = _run_healer(wt, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    text = (repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "resolve_engine" in text


def test_healer_heals_from_main_checkout_subdir(tmp_path):
    home = _make_fake_home(tmp_path, ["2.2.0"])
    dead = tmp_path / "gone" / "voice_check.py"
    repo = _make_repo(tmp_path, OLD_STYLE_HOOK.format(engine=dead))
    sub = repo / "docs"
    sub.mkdir()
    result = _run_healer(sub, home)
    assert result.returncode == 0
    assert "healed" in result.stdout
    text = (repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "resolve_engine" in text


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
