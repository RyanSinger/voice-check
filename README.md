# voice-check

A Claude Code skill that scans markdown documents for AI writing tells, em dashes, hedging, puffery, and other patterns that signal LLM-generated prose.

## What it catches

- **Hard rules:** em dashes, en dashes, hyphens used as separators, hedging language ("would like to," "could potentially"), copula avoidance ("serves as" instead of "is")
- **AI vocabulary cluster:** flags when 2+ words from a known LLM-favored vocabulary appear in the same document (pivotal, crucial, leverage, enduring, intricate, tapestry, testament, etc.)
- **Puffery and significance language:** "groundbreaking," "renowned," "pivotal moment," "indelible mark"
- **Promotional tone:** "boasts," "nestled in the heart of," "vibrant," "showcasing"
- **Dangling participles:** "...highlighting the importance of," "...ensuring that," "...fostering"
- **Structural tells:** rule of three, negative parallelism, false ranges, challenges-and-future-prospects, elegant variation
- **Vague attributions:** "experts say," "industry observers note"

## How it works

Two paths:

1. **Manual `/voice-check <file>`** in Claude Code. Claude loads the skill, scans the file, fixes violations in place, reports what changed.
2. **Git pre-commit hook.** A fast Python rules engine catches the deterministic stuff (dashes, vocabulary cluster, puffery, promotional tone) at every commit. Advisory only, never blocks.

The Python engine handles deterministic rules at git-hook speed. The Claude-loaded skill handles nuanced rules (tone, voice, dangling-participle context) when you invoke it manually.

## Layered rules

You can drop a `.claude/voice-check.md` file at the root of any repo to add repo-specific rules on top of the universal ones. The skill walks up from the target file to the git root looking for a supplement; it stops at the first one found and applies it in addition to the global rules.

Example supplement contents:

```markdown
# voice-check supplement for my-project

## Additional rules

### No marketing language for our product
Don't describe our system as "innovative," "leading," or "best-in-class."

### Cite sources, don't paraphrase
When invoking external research, cite it. Don't paraphrase.
```

Universal rules live in this repo. Repo-specific supplements live in your repos.

## Install

### Install the skill

```bash
git clone https://github.com/ryansinger/voice-check.git ~/.claude/skills/voice-check
```

That's it. Claude Code picks up skills under `~/.claude/skills/` automatically. After cloning, `/voice-check <file>` will work in any session.

If you want to use the pre-commit hook, set up the venv for the Python rules engine:

```bash
cd ~/.claude/skills/voice-check
python3 -m venv .venv
.venv/bin/pip install pytest
```

(pytest is optional. The engine itself uses only the standard library; pytest is only needed if you want to run the test suite.)

### Install the git pre-commit hook in a repo

```bash
cd /path/to/your/repo
~/.claude/skills/voice-check/templates/install-hook.sh
```

The installer is idempotent. If a pre-commit hook already exists in the repo, the installer appends a marked voice-check section rather than overwriting.

To uninstall, delete the section between `# === voice-check section start ===` and `# === voice-check section end ===` from `.git/hooks/pre-commit`.

## Run the tests

```bash
cd ~/.claude/skills/voice-check
.venv/bin/python -m pytest tests/test_engine.py -v
```

15 unit tests covering dash detection, AI vocabulary cluster, puffery, promotional tone, and supplement file discovery. Requires Python 3.11+ and pytest.

## Customize the rules

The deterministic rules live in `engine/rules.py`. Word lists, regex patterns, and detection thresholds are all editable. The non-deterministic rules (the things only Claude can catch) live in `SKILL.md` as natural-language instructions for the model.

## Repository layout

```
SKILL.md                    Active rules + scan protocol (loaded by Claude)
references/
  wikipedia-signs.md        Reference material on AI writing tells
  examples.md               Before/after examples for each rule category
engine/
  voice_check.py            Python entry point and CLI
  rules.py                  Deterministic rule definitions
  supplement.py             Per-repo supplement file discovery
templates/
  pre-commit.sh             Git hook template
  install-hook.sh           Per-repo hook installer (idempotent)
tests/
  test_engine.py            pytest suite (15 tests)
  fixtures/                 Sample clean and dirty markdown files
```

## License

MIT
