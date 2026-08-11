# Voice Check Plugin Upgrade: Skill Best Practices and 2026 Rules Refresh

Date: 2026-08-11
Status: approved

## Goal

Bring the two skills in line with Anthropic's published skill authoring best practices, and refresh the writing rules for the AI tells documented since the April 2026 snapshot. Two tracks, one release.

Primary sources: Anthropic skill authoring best practices (platform.claude.com), Wikipedia "Signs of AI writing" (live article, August 2026), Forbes "15 New Giveaway Signs of AI Writing" (May 2026).

## Scope

In scope: both SKILL.md files, `references/rules.md`, `references/wikipedia-signs.md`, `references/examples.md`, `engine/rules.py`, `tests/test_engine.py`, README (only if it enumerates rule categories).

Out of scope: hook installation flow, marketplace metadata, engine scanner architecture, standalone skill packaging (the plugin-root `../../references/` layout stays; it is a documented repo convention and this plugin targets Claude Code only).

## Track 1: Skill structure

### voice-check SKILL.md

Restructured around an engine-as-validator feedback loop with a copyable progress checklist:

```
Voice Check Progress:
- [ ] Step 1: Locate target file and any .claude/voice-check.md supplement
- [ ] Step 2: Run the engine (report-only) to get deterministic findings
- [ ] Step 3: Fix every engine finding
- [ ] Step 4: Re-run the engine until it reports zero findings
- [ ] Step 5: Manual pass for skill-only rules
- [ ] Step 6: Report changes by category
```

Details:

- Step 2 runs `python3 <plugin>/engine/voice_check.py --report-only <target>`. The instruction states execution intent explicitly: run the script, do not read it as reference.
- Steps 2 through 4 form the validator loop. Exit to step 5 only on a clean engine pass.
- Fallback: if `python3` is unavailable, do a full manual scan covering the engine-tagged rules as well.
- Step 5 covers the `[skill only]` rules: structural tells, sentence rhythm, elegant variation, contrast reframes, balanced-debate framing.
- Report-only mode (pre-commit hook path) keeps current behavior: print findings, never modify the file.

### writing-guard SKILL.md

Keeps its proactive shape. Changes:

- Self-check process becomes numbered workflow steps.
- New final verification step: if the draft was written to a file and `python3` exists, run the engine on that file before declaring the draft done.

### Frontmatter descriptions

Both rewritten in third person with concrete trigger terms, per the discovery guidance. Example for voice-check: "Scans a document for AI writing tells: em dashes, hedging, puffery, AI vocabulary, promotional tone. Use when reviewing or editing prose, before committing documents, or when the user mentions AI-sounding writing, voice, or tone." Writing-guard gets the same treatment for the proactive case.

## Track 2: Rules refresh

### rules.md additions

1. **2026 vocabulary cluster.** Bare words are `[skill only]`: quietly, shift, matters, shape, land, actually, real, earn, hold, pull, compound, signal, plus the phrase "the work". Too common for word-boundary regex. The skill judges them in context with the existing clustering logic: two or more in a document is a pattern. Phrase-level forms are `[engine + skill]`: "quietly building", "this matters because", "the pull of", "built different", "do the work", "send a signal", "decisions compound".
2. **Faux-conversational bridges** `[engine + skill]`: "here's the thing", "but here's the truth", "at the end of the day", "don't get me wrong", "let's dive in", "let's delve into", "in this section we will", "we will explore", "let's examine".
3. **Markup artifacts** `[engine + skill]`: leaked model citation tokens (contentReference, oaicite, turn0search, `[cite:`, grok_card, ppl-ai-file-upload, attached_file) and emoji used as bullet markers.
4. **Amendments to Structural Tells** `[skill only]`: contrast reframes ("It's not about X, it's about Y" manufacturing insight from false opposition), overuse of "X rather than Y", balanced-debate framing ("While X has advantages, it also has disadvantages"), uniform sentence rhythm (every sentence landing in the same length range).

The existing AI vocabulary cluster list stays untouched. Old tells still catch older AI text; removing them weakens the hook with no gain.

### wikipedia-signs.md

Replace the April snapshot with the current article content. Add a table of contents at the top (the file exceeds the 100-line threshold where partial reads lose context). Head the file with "snapshot as of 2026-08-11" so the dating is absolute.

### examples.md

Add before/after pairs for the three new rule categories, matching the existing format.

## Engine changes

New rows in the `RULES` table in `engine/rules.py`. No scanner changes.

1. `bridge_phrases`: kind `phrase`, line scope, the bridge list above.
2. `vocab_2026`: kind `phrase` or `regex`, line scope, phrase-level 2026 patterns only. Bare words stay out of the engine.
3. `markup_artifacts`: kind `regex`, line scope, citation tokens and emoji bullets. Fence-skipping behavior stays as is; an artifact inside a real code fence is plausibly intentional quoting.

## Tests

New cases in `tests/test_engine.py` per new category:

- Positive match per category.
- Negative controls: "the end of the day shift" must not fire the bridge rule; emoji inside a code fence must not fire markup_artifacts.
- Existing 15 cases keep passing. Supplement interaction tests stay as is.

Skill-level verification (manual, post-implementation): run the voice-check skill end to end on a seeded fixture containing old tells, 2026 tells, markup artifacts, and one planted skill-only violation. Verify the engine loop converges to zero findings and the manual pass catches the planted violation.

## Sync obligations

`references/rules.md` and `engine/rules.py` change in the same commit, per the repo's dual-authority rule (markdown authoritative for the skill path, rules.py authoritative for the hook path). Check README for a rule-category listing and update it if present.

## Risks

- New phrase rules can false-positive in legitimate prose ("at the end of the day" as a literal time reference). Accepted: the hook is advisory and exits 0 by design; the skill applies judgment before rewriting.
- Common-word tells stay out of the engine entirely, so hook coverage of the 2026 cluster is partial by design. The skill path covers the rest.
