# Surfaces Beyond Markdown (Phase 3a)

Date: 2026-09-07
Status: approved, ready for implementation planning

## Context

The engine has only ever seen markdown files. The pre-commit hook filters staged paths with `grep '\.md$'`, so a `.txt` file, a `.rst` file, and every commit message pass unexamined.

Commit messages are the gap that matters most. `CLAUDE.md` states the no dashes rule applies to "commit messages, docs, comments, and Markdown prose", and the global rules agree, yet the one surface where that rule is stated explicitly is the one surface never checked.

## A contradiction this phase resolves

`skills/writing-guard/SKILL.md` currently tells the model NOT to apply the rules "when writing code, code comments, or commit messages where dashes and technical jargon are appropriate". That directly contradicts `CLAUDE.md`.

`CLAUDE.md` is authoritative. The skill's exemption narrows to code and code comments only, and commit messages come under the rules. Fixing this is part of this phase, because it decides whether the phase's headline surface should exist at all.

## Scope

Phase 3 as originally sketched covered four surfaces that are not one project:

- **Plain text files and commit messages** share the same document handling and the same hook installer. That is this phase.
- **Source code docstrings** need an extractor that parses Python and pulls prose out of an AST, a concept the engine has never had. Its own phase.
- **Pull request bodies** are not a git hook at all, needing a forge integration or an action. Its own phase.

In scope here:

- A surface concept, so a rule can apply to files without applying to commit messages
- A `commit-msg` hook running a restricted rule set
- Widening the pre-commit file filter beyond markdown
- Correcting the `writing-guard` exemption

Out of scope, with reasons:

- Docstring extraction and PR bodies, per the decomposition above.
- A `from_plain` document constructor. Measured unnecessary: see "No new constructor" below.
- Per repo override of the commit surface. The `voice-check-enable` mechanism could express it, but nobody has asked.
- Any change to the advisory contract.

## Constraints

- The engine stays Python standard library only.
- Both hooks are advisory and always exit 0.
- The `# === voice-check section start/end ===` contract is preserved in both hooks.
- No dashes in any prose output, including commit messages and documentation.
- Python 3.11 or later, tested across 3.11 through 3.14.

## What the measurement showed

Running the current engine over the last 89 commit messages in this repository, with no surface restriction:

| | |
| --- | --- |
| Messages with at least one finding | 9, about 10 percent |
| `no_dashes` findings | 0 |

Every finding was a false positive of the mention versus use kind, because this repository's commit messages discuss the rules themselves:

```
markup_artifacts       "the hyphenated grok-card form"
not_just_but           "evidence lines, not just a raising analyzer"
at_the_end_of_the_day  "the engine's own longest banned phrase, at the end of the day"
puffery.crucial        "(crucial, delve, tapestry) instead of three words"
```

This repository inflates that rate, since a normal project's history does not mention `grok-card`. But the measurement exposed a structural problem that is not self referential.

**A commit message cannot carry a suppression.** Every other surface can host a `<!-- voice-check: ignore -->` comment. A commit message cannot reasonably, and once written it is in history. The escape hatch that makes the rest of the engine tolerable does not exist here.

That is why the commit surface runs a restricted rule set rather than everything.

## Architecture

### The surface concept

One constant in `rules.py`, which is the rule table's home:

```python
COMMIT_SURFACE = frozenset({"no_dashes", "markup_artifacts"})
```

It names rule NAMES, not ids, so it covers `markup_artifacts.citation_tokens`, `markup_artifacts.emoji_bullet`, and the `embedded_tokens` analyzer together without enumerating them.

`_select_rows` gains the filter, since row selection already happens in exactly one place:

```python
def _select_rows(cfg, rel_path, surface="file"):
    rows = list(rules.RULES) + list(cfg.extra_rows)
    if surface == "commit":
        rows = [r for r in rows if r["name"] in rules.COMMIT_SURFACE]
    return [r for r in rows if not cfg.is_disabled(r, rel_path)]
```

`scanner.scan` takes `surface="file"` and threads it to the analyzer pass as well, so `embedded_tokens` reaches commit messages while `bold_headers` cannot. `voice_check.py` gains `--surface {file,commit}` defaulting to `file`, so no existing behavior changes.

### Why an allowlist rather than a denylist

A rule added later runs on files and does NOT run on commits until someone deliberately adds its name.

That direction is the whole point. A false positive in a commit message is permanent and unsuppressable, so the surface without an escape hatch must be the one that stays closed by default. A denylist would mean every new rule silently starts firing on every commit until someone notices.

Supplement rules never run on commits for the same reason: they carry `name: "supplement:word"` and similar, which are not in the allowlist. A repo's custom words cannot be suppressed in a commit message any more than a built in can.

### No new constructor

This phase was expected to need a `from_plain` document constructor. It does not.

`Document.from_markdown` already handles commit messages correctly, which was verified by running the measurement above through it: inline code and bullet markers masked sensibly, because commit messages use markdown conventions in practice. Plain `.txt` is close enough that a separate constructor would duplicate the masking layer to change almost nothing.

This removes the piece expected to be largest.

## The commit-msg hook

A new `templates/commit-msg.sh` receiving the message file as `$1`, following the existing hook's shape: the same marker contract, the same version stamp, the same `resolve_engine` fallback chain, and the same unconditional `exit 0`.

### The message file is not the message

`COMMIT_EDITMSG` carries git's instruction comments, and under `commit.verbose` the entire diff below a scissors line. Scanning it raw would report findings from other people's code.

Two steps are required, and one of them is easy to get wrong. `git stripspace --strip-comments` removes comment lines but does NOT remove the verbose diff: the scissors line itself starts with the comment character and is stripped, while every diff line below it survives. Verified directly, a diff containing an em dash passes straight through.

So the hook cuts at the scissors marker first, then strips comments:

```
sed '/^#.*>8/,$d' "$1" | git stripspace --strip-comments
```

Verified that a message with no scissors line loses nothing. Getting this wrong would report findings from other people's code, which would be the phase's most embarrassing bug, and the first draft of this spec got it wrong.

A trap removes the temp file on every exit path, including failure paths. A hook that litters on every commit is its own defect.

### Merge commits are not special cased

An auto generated "Merge pull request #7 from ..." message runs the same allowlist. It rarely fires, and when it does the finding is legitimate: a pull request title carrying an em dash really does enter the history. Suppressing that would hide a true positive to avoid noise nobody has demonstrated.

### Installer and healer cover a pair

`install-hook.sh` names `pre-commit` in three places and `heal-hook.sh` in four, and neither knows about a second hook. Both generalise over a list of hook names rather than duplicating their logic.

This matters more than it looks. The version stamp healing added in Phase 1 would otherwise apply to one hook and not the other, and a half healed install, where the pre-commit hook is current and the commit-msg hook is stale, is worse than an unhealed one because nothing surfaces the mismatch.

Uninstall documentation names both files. The README currently describes deleting the marked section from `.git/hooks/pre-commit`, which becomes wrong the moment this ships.

## Widening the file surface

The pre-commit filter becomes `\.(md|markdown|txt|rst)$`.

Fixed rather than configurable. The supplement already offers `voice-check-exclude` for opting out, and nobody has asked to opt an extension in. These files can carry suppression comments, so they receive the full rule set; only commit messages are restricted.

## Error handling

Almost everything is inherited: `resolve_engine`, the `|| true` guard around every engine invocation, and the unconditional `exit 0`. Three additions:

| Failure | Behavior |
| --- | --- |
| The scissors cut or `git stripspace` fails | Fall back to scanning the raw message file. Degrades toward reporting more, and the worst case is a finding on a comment line rather than a missed one. |
| Any exit path | A trap removes the temp file. |
| Message empty after stripping | Exit 0 silently. This is an aborted commit, not a clean one. |

## Testing

`tests/test_hook_pipeline.py` already provides the harness: `_init_repo`, `_run_installer`, `_stage_file`, and `_run_hook` with its interpreter pinning. These extend it rather than starting a second one.

**The allowlist actually restricts.** A message containing both an em dash and puffery reports the dash and stays silent on the puffery. This single test pins the entire feature. Without it the surface filter could be a no op and nothing else would notice.

**Comments and the verbose diff are stripped.** A message file carrying git's instruction comments, a scissors line, and a diff full of em dashes must report nothing. This is the case most likely to catch a real bug.

**A new rule cannot leak onto commits.** Assert `COMMIT_SURFACE` equals the expected set exactly, so adding a rule without considering commits fails loudly rather than silently nagging on every commit.

**Both hooks install, and both heal.** The version stamp mechanism covers the pair, since a half healed install is the failure mode that would otherwise go unnoticed.

**The widened extensions scan**, and a `.py` file still does not.

**The advisory contract on the changed path**: a commit with findings still exits 0.

## Known limitation

This repository will still produce occasional unsuppressable false positives on commit messages, precisely because it is a repository about leaked tokens and banned phrases. The allowlist cuts the measured rate sharply, since `no_dashes` fired zero times across 89 commits and both `markup_artifacts` hits were messages describing tokens, but it does not eliminate the class.

That is the cost of a surface with no escape hatch. It was visible before the work started and is recorded here rather than discovered later.

## Alternatives considered

**A `surfaces` field on each rule row.** Every row declares where it applies, defaulting to file only. Declarative and colocated with the rule, and worth revisiting if the surface count grows. Rejected for two surfaces: it means touching the row schema and reasoning about ninety rows to express what one constant says, and it inverts the safe default, since forgetting the field on a new rule is easy and the question becomes "did I remember" rather than "is it on the list".

**The hook passes disables on the command line.** `--disable puffery,hedging,...` from the commit-msg hook, needing no new engine concept. Rejected because the hook would have to name every rule that should not run, so every new rule silently starts firing on commits until someone updates a shell script. That is precisely the failure the allowlist prevents.

## Success criteria

1. A commit message containing an em dash reports one finding and the commit still succeeds.
2. A commit message containing puffery, hedging, or a structural frame reports nothing.
3. A commit message containing a leaked token reports it, since `markup_artifacts` is on the allowlist.
4. Git's instruction comments and a verbose diff in the message file produce no findings.
5. `COMMIT_SURFACE` is pinned by a test, so a new rule cannot join it unnoticed.
6. A supplement's custom word fires on a markdown file and not on a commit message.
7. Staged `.txt` and `.rst` files are scanned with the full rule set; a `.py` file is not scanned.
8. One installer run installs both hooks, and the healer repairs both.
9. Both hooks exit 0 in every case, including when the engine is missing entirely.
10. `skills/writing-guard/SKILL.md` no longer exempts commit messages.
11. The README's uninstall instructions name both hooks.
12. The full suite passes on Python 3.11 through 3.14.
