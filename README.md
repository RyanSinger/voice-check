# voice-check

Two Claude Code skills that catch AI writing tells, em dashes, hedging, puffery, and promotional tone:

- **`voice-check`**: reactive scan that fixes violations after you write
- **`writing-guard`**: proactive guard that loads before drafting and self-censors as you write

Both skills share a single rule list, a Python rules engine, and per-repo supplement support. Includes an advisory git pre-commit hook for the reactive path.

## What it catches

Rules tagged **[engine]** run in the Python pre-commit hook engine. Rules tagged **[skill]** run only in the Claude-loaded skills, because they need context a regex cannot reliably see.

Every engine row carries a stable id of the form `<name>.<slug>`, for example `puffery.crucial`. A supplement can disable one row by id or a whole rule by name, and severities can be reassigned the same way. See "Severity and noise control" below and `references/rules.md` for the full syntax.

- **Hard rules [engine]:** em dashes, en dashes, hyphens used as separators, hedging language ("would like to," "could potentially," "it is worth noting"), copula avoidance ("serves as," "stands as," "acts as," "functions as")
- **AI vocabulary cluster [engine]:** flags when 2+ words from a known LLM-favored vocabulary appear in the same document (pivotal, crucial, leverage, enduring, intricate, tapestry, testament, etc.) <!-- voice-check: ignore puffery, ai_vocab_cluster -->
- **Puffery and significance language [engine]:** "groundbreaking," "renowned," "pivotal," "crucial," "testament," "indelible," "transformative"
- **Promotional tone [engine]:** "boasts," "nestled in the heart of," "vibrant," "showcasing," "commitment to"
- **Dangling participles [engine]:** comma followed by gerund phrases like "...highlighting the importance of," "...ensuring that," "...fostering growth"
- **Vague attributions [engine]:** "experts say," "experts agree," "industry observers note," "sources say," "many believe"
- **Faux-conversational bridges [engine]:** "here's the thing," "at the end of the day," "let's dive in," "we will explore"
- **2026 vocabulary [engine for phrases, skill for bare words]:** "quietly building," "this matters because," "built different," "decisions compound"; bare words (quietly, shift, matters, signal, compound) are judged in context by the skill
- **Markup artifacts [engine]:** leaked citation tokens (contentReference, oaicite, [cite:, grok_card, ppl-ai-file-upload), emoji used as bullet markers <!-- voice-check: ignore markup_artifacts -->
- **Structural tells [engine]:** negative parallelism ("not just X, but Y"), contrast reframes, balanced-debate framing, challenges-and-prospects, and false ranges. All low severity, so they collapse to a counted line unless you pass `--min-severity low`.
- **Mechanical bold headers [engine, opt in]:** ships off, because on 206 measured files it fired on 6.8 percent of them and every hit was an ordinary definition list. Enable it per repo with a `voice-check-enable` block naming `structure.bold_headers`.
- **Structural tells [skill]:** rule of three, elegant variation, uniform sentence rhythm

The full rule list is in `plugins/voice-check/references/rules.md`.

## How it works

Two skills, two timings:

1. **`writing-guard` (proactive).** Loads before Claude produces prose. Reads the rules and self-censors as it drafts. No file required.
2. **`voice-check` (reactive).** Scans an existing file. Two modes:
   - Manual `/voice-check <file>`: auto-fixes in place
   - Git pre-commit hook: fast Python rules engine, report-only, advisory

The Python engine handles deterministic rules (dashes, vocabulary cluster, puffery, promotional tone, hedging, copula avoidance, dangling participles, vague attributions, bridge phrases, 2026 vocabulary phrases, markup artifacts, five structural frames, mechanical bold headers) at hook speed via a single data-driven rule table plus a small set of document-level analyzers. The Claude-loaded skill handles the remaining context-sensitive patterns (rule of three, elegant variation, uniform sentence rhythm) when invoked manually.

## Layered rules: per-repo supplements

You can drop a `.claude/voice-check.md` file at the root of any repo to add repo-specific rules on top of the universal ones. The skill walks up from the target file to the git root, finds the supplement at the first match, and applies it in addition to the global rules.

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
blockquotes, and double quoted spans under seven words. Writing about a banned
word in quotes no longer trips the rule that bans it.

Single quotes never mask, because apostrophes make them ambiguous.

## Only what you changed

The pre-commit hook derives changed line ranges from `git diff --cached -U0`
and reports only on those lines. Editing one line of an old document does not
surface that document's whole history. A vocabulary cluster is reported when
at least one of its occurrences falls on a changed line.

## Install

### Install the marketplace and plugin

```bash
claude plugin marketplace add RyanSinger/voice-check
claude plugin install voice-check@voice-check
```

After install, both `voice-check` and `writing-guard` are available in your Claude Code session.

To update later:

```bash
claude plugin marketplace update voice-check
```

Installed hooks self-heal after upgrades: the hook re-resolves the engine from the plugin cache at commit time, and a SessionStart healer repairs hooks installed by versions before 2.2.1 the first time you start a Claude Code session in that repo. Repos where you never open Claude Code keep the old advisory nag until you run `install-hook.sh` there once. Both the installer and the healer also work from linked git worktrees; the hook lands in the shared hooks directory of the main checkout.

### Install the git pre-commit hook in a repo

```bash
cd /path/to/your/repo
bash "$(ls ~/.claude/plugins/cache/voice-check/voice-check/*/templates/install-hook.sh | sort -V | tail -1)"
```

The installer is idempotent. If a pre-commit hook already exists, it appends a marked voice-check section rather than overwriting. To uninstall, delete the section between `# === voice-check section start ===` and `# === voice-check section end ===` from `.git/hooks/pre-commit`.

The hook is **advisory only**, it never blocks commits. Findings print to stderr and the commit proceeds.

## Run the tests

The Python engine has a pytest suite. To run it:

```bash
cd ~/.claude/plugins/cache/voice-check/voice-check/*
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -v
```

Requires Python 3.11+. The runtime engine itself uses only the standard library; pytest is only needed for the test suite.

## Customize the rules

The single source of truth is `plugins/voice-check/references/rules.md`. Edit that file to change rules; both skills get the update.

The deterministic rules used by the Python engine live in `plugins/voice-check/engine/rules.py` (word lists, regex patterns, detection thresholds). Editing the Python rules requires updating the engine. Editing the markdown rules in `references/rules.md` updates both skills' Claude-loaded behavior immediately.

## Repository layout

```
.claude-plugin/
  marketplace.json              Marketplace catalog
plugins/
  voice-check/                  The plugin
    .claude-plugin/
      plugin.json               Plugin manifest
    skills/
      voice-check/
        SKILL.md                Reactive scan skill (thin shell)
      writing-guard/
        SKILL.md                Proactive guard skill (thin shell)
    references/
      rules.md                  Single source of truth for the rules
      wikipedia-signs.md        Wikipedia article on AI writing tells
      examples.md               Before/after examples for each rule category
    engine/
      voice_check.py            Python entry point and CLI
      document.py               Masking, prose text, suppression directives
      config.py                 Per-repo supplement discovery and parsing
      rules.py                  Rule table: ids, severities, patterns
      scanner.py                Runs rules against a masked Document
    templates/
      pre-commit.sh             Git hook template (with placeholder)
      install-hook.sh           Per-repo hook installer
    tests/
      test_engine.py, test_document.py, test_config.py, test_scanner.py,
      test_hook_pipeline.py, test_skill_paths.py, test_regressions.py
      fixtures/                 Sample clean and dirty markdown files
README.md
LICENSE
```

## Migrating from v1 (direct-clone)

If you installed v1 by cloning to `~/.claude/skills/voice-check/`:

```bash
rm -rf ~/.claude/skills/voice-check
claude plugin marketplace add RyanSinger/voice-check
claude plugin install voice-check@voice-check
```

Hooks installed by 2.2.1 or later need nothing after upgrades; older hooks are repaired automatically the first time a Claude Code session starts in that repo.

## License

MIT
