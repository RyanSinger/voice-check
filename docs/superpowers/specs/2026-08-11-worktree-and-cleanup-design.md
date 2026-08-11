# Worktree Support and Parked Cleanups

Date: 2026-08-11
Status: approved

## Problem

Three items parked during the hook self-healing review, plus one doc staleness found while scoping:

1. The installer requires a literal `.git` directory, so linked worktrees cannot install or heal from their own checkout (hooks are shared with the main checkout, which is the only healing path today).
2. `templates/install-hook.sh` line 103 has a pre-existing em dash in a comment, in the repo that bans them.
3. README's install instruction uses a bare glob (`.../voice-check/*/templates/install-hook.sh`); with two or more cached plugin versions it expands to multiple words and the second path becomes the installer's repo argument, which errors.
4. README's repo layout section says the test suite has 15 tests; it has 52.

## Design

### Installer resolves the hooks directory via git (Approach A)

In `templates/install-hook.sh`:

- Replace the `[ ! -d "$REPO_DIR/.git" ]` guard with a git query: `GIT_COMMON=$(git -C "$REPO_DIR" rev-parse --git-common-dir)`. If the query fails, keep the existing "not a git repo" error and exit 1.
- `HOOK_DIR` becomes `<GIT_COMMON>/hooks` (made absolute; `--git-common-dir` may return a relative path such as `.git`, resolved against `REPO_DIR`).
- Everything else (marker logic, idempotent replace, engine resolution) is unchanged.

Effect: installing from a linked worktree writes to the shared hooks file in the main checkout, which is where git actually runs hooks for every worktree.

### Healer follows

In `hooks/heal-hook.sh`, drop the `[ -d "$REPO_ROOT/.git" ]` guard. The healer already requires `git rev-parse --show-toplevel` to succeed; the hook file it inspects becomes `<git-common-dir>/hooks/pre-commit` resolved the same way as the installer. All exit-0 guarantees unchanged. The marker requirement is unchanged: the healer still never installs into repos that have not opted in.

### Text fixes

- `templates/install-hook.sh` line 103 comment: em dash becomes a colon ("Otherwise there's other content: append fresh section after the stripped file").
- README install command becomes deterministic under multiple cached versions:

  ```bash
  cd /path/to/your/repo
  bash "$(ls ~/.claude/plugins/cache/voice-check/voice-check/*/templates/install-hook.sh | sort -V | tail -1)"
  ```

- README repo layout line drops the test count: "pytest suite" with no number.

### Version

Bump `plugin.json` to 2.2.2.

## Testing

Two new pytest cases (subprocess, same helpers as the existing healer tests):

1. Installer from a worktree: create a repo, `git worktree add` a linked worktree, run the installer with the worktree path as the argument (fake HOME cache providing the engine), assert the voice-check section lands in the MAIN checkout's `.git/hooks/pre-commit` and is executable.
2. Healer from a worktree: main checkout has a stale old-style voice-check hook section; run the healer with cwd inside the linked worktree (`CLAUDE_PLUGIN_ROOT` at the plugin source, fake HOME cache); assert the shared hook now contains `resolve_engine` and the healer printed its healed line.

Existing 52 tests stay green. The existing healer no-op tests still pass because dropping the `.git`-directory guard does not change behavior for normal checkouts.

## Out of scope

- No engine, rules, or skill changes.
- Detached or bare-repo exotica: `rev-parse --git-common-dir` handles them or fails into the existing error path.
