# Goal

Improve the voice-check plugin by closing the gap between what the README advertises and what the Python engine actually implements, and by wiring up the existing-but-unused per-repo supplement support in the CLI.

## Context

voice-check is a Claude Code plugin with two skills (`voice-check` reactive scan, `writing-guard` proactive guard) that share a markdown rules list (`plugins/voice-check/references/rules.md`) as the source of truth. A stdlib-only Python engine (`plugins/voice-check/engine/`) runs deterministic rule subsets at pre-commit hook speed. The engine is intentionally a subset of the full skill behavior.

## Scope (this round)

1. **Rule parity with README.** Engine implements the rule categories the README claims but currently lacks: hedging, copula avoidance, dangling participles, vague attributions. Keep or extend the existing categories (dashes, AI vocab cluster, puffery, promotional tone).
2. **Supplement integration.** `engine/voice_check.py` CLI finds and applies per-repo `.claude/voice-check.md` supplements via the existing `supplement.py` module. Supplements should let users add extra banned words or phrases that the engine respects.
3. **Test coverage for new rules.** At least one positive and one negative test per new rule category. All existing tests still pass.
4. **Docs honesty.** `references/rules.md` and README accurately reflect what the engine does vs. what only the skill does.

## Out of scope (this round)

- Deterministic auto-fix (engine remains report-only).
- Rewriting the skills themselves.
- Install/upgrade UX changes.
- New runtime dependencies.

## Constraints

- Engine stays Python stdlib only.
- Pre-commit hook stays advisory (always exits 0).
- No dashes in any prose output, including commit messages and docs.
- Preserve the `# === voice-check section start/end ===` hook contract.
