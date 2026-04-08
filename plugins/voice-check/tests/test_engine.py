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


def test_find_supplement_walks_up_to_git_root(tmp_path):
    # Create a fake git repo with a nested structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "voice-check.md").write_text("# supplement\n")
    nested = tmp_path / "deep" / "nested" / "dir"
    nested.mkdir(parents=True)
    target = nested / "doc.md"
    target.write_text("hello\n")

    sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))
    import supplement
    result = supplement.find_for(target)
    assert result == tmp_path / ".claude" / "voice-check.md"


def test_find_supplement_returns_none_when_absent(tmp_path):
    (tmp_path / ".git").mkdir()
    target = tmp_path / "doc.md"
    target.write_text("hello\n")

    import supplement
    result = supplement.find_for(target)
    assert result is None


import subprocess


def test_cli_clean_file_returns_zero():
    result = subprocess.run(
        [str(Path(__file__).parent.parent / ".venv" / "bin" / "python"),
         "engine/voice_check.py", "--report-only", "tests/fixtures/clean.md"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_cli_dirty_file_reports_findings():
    result = subprocess.run(
        [str(Path(__file__).parent.parent / ".venv" / "bin" / "python"),
         "engine/voice_check.py", "--report-only", "tests/fixtures/dirty-universal.md"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    # Report-only should always exit 0 (advisory)
    assert result.returncode == 0
    assert "no_dashes" in result.stdout or "ai_vocab" in result.stdout or "puffery" in result.stdout
    assert len(result.stdout) > 0


def test_find_supplement_stops_at_git_root(tmp_path):
    # Supplement above the git root should NOT be found
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "voice-check.md").write_text("# outer\n")
    inner_repo = tmp_path / "subrepo"
    inner_repo.mkdir()
    (inner_repo / ".git").mkdir()
    target = inner_repo / "doc.md"
    target.write_text("hello\n")

    import supplement
    result = supplement.find_for(target)
    assert result is None


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


def test_supplement_load_rows_parses_all_kinds(tmp_path):
    p = tmp_path / "voice-check.md"
    p.write_text(
        "```voice-check-words\n"
        "foo\n"
        "```\n"
        "```voice-check-phrases\n"
        "bar baz\n"
        "```\n"
        "```voice-check-regex\n"
        "\\bqux\\d+\\b\n"
        "```\n"
    )
    import supplement
    rows = supplement.load_rows(p)
    kinds = sorted({r["kind"] for r in rows})
    assert kinds == ["phrase", "regex", "word"]
    assert all(r["name"].startswith("supplement:") for r in rows)
