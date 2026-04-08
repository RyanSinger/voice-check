"""Tests for SKILL.md reference path integrity.

Criterion 9: every relative path mentioned inside skills/*/SKILL.md must
resolve to a file that actually exists. This catches the class of bug where a
reference file is moved, renamed, or deleted without updating the skill prose.

Stdlib only. cwd-independent: plugin root is computed from __file__.
"""
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"

# Matches relative paths starting with ../ that end in .md.
# Covers paths in prose, code spans, and bare text.
# Backtick is excluded from the character class so code-span delimiters do not
# bleed into the captured path.
_REL_PATH_RE = re.compile(r"\.\./[^\s`)\]]*\.md")


def _collect_skill_files():
    """Return sorted list of SKILL.md paths under the skills directory."""
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def test_skill_file_discovery():
    """At least two SKILL.md files must exist: voice-check and writing-guard."""
    found = _collect_skill_files()
    assert len(found) >= 2, (
        f"expected at least 2 SKILL.md files under {SKILLS_DIR}, "
        f"found {len(found)}: {[str(p) for p in found]}"
    )


def test_skill_relative_paths_resolve():
    """Every relative .md path inside each SKILL.md must point to a real file."""
    skill_files = _collect_skill_files()
    assert skill_files, f"no SKILL.md files found under {SKILLS_DIR}"

    broken = []
    for skill_file in skill_files:
        skill_dir = skill_file.parent
        text = skill_file.read_text(encoding="utf-8")
        raw_paths = _REL_PATH_RE.findall(text)
        seen = set()
        for raw in raw_paths:
            if raw in seen:
                continue
            seen.add(raw)
            resolved = (skill_dir / raw).resolve()
            if not resolved.is_file():
                broken.append(
                    f"{skill_file.relative_to(PLUGIN_ROOT)}: "
                    f"broken path '{raw}' -> {resolved}"
                )

    assert not broken, (
        "The following reference paths in SKILL.md files do not resolve to "
        "existing files:\n" + "\n".join(broken)
    )


def test_skill_files_reference_rules_md():
    """Every SKILL.md must mention ../../references/rules.md.

    This is the one path the plugin genuinely depends on at skill-load time.
    If a skill stops referencing it, the rules list is no longer loaded and
    the skill silently loses all enforcement.
    """
    skill_files = _collect_skill_files()
    assert skill_files, f"no SKILL.md files found under {SKILLS_DIR}"

    missing = []
    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        if "../../references/rules.md" not in text:
            missing.append(str(skill_file.relative_to(PLUGIN_ROOT)))

    assert not missing, (
        "The following SKILL.md files do not mention "
        "'../../references/rules.md':\n" + "\n".join(missing)
    )
