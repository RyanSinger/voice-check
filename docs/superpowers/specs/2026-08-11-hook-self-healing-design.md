# Hook Self-Healing: Survive Plugin Upgrades Without Reinstalling

Date: 2026-08-11
Status: approved

## Problem

`install-hook.sh` bakes the absolute engine path (which includes the plugin version directory, e.g. `.../cache/voice-check/voice-check/2.1.0/engine/voice_check.py`) into each repo's `.git/hooks/pre-commit`. Every plugin upgrade changes that path, so every installed hook goes stale and prints a nag asking the user to re-run the installer. Requirement: after this release, users never run `install-hook.sh` again for upgrades, and already-broken hooks heal with no user action.

## Design

Two mechanisms, both shipped in plugin version 2.2.1.

### 1. Self-healing git hook template (`templates/pre-commit.sh`)

Replace the static existence check with runtime resolution, tried in order:

1. `$VOICE_CHECK_ENGINE` environment override, if set and the file exists.
2. The baked `__VOICE_CHECK_ENGINE__` path (fast path, valid until the next upgrade).
3. Newest cache hit: `find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1`.
4. Legacy clone path: `$HOME/.claude/skills/voice-check/engine/voice_check.py`.

If nothing resolves: print one advisory line and exit 0. The hook's advisory contract (always exit 0, never block commits) is unchanged. The marker section format (`# === voice-check section start/end ===`) is unchanged so the installer's idempotent replace logic keeps working.

### 2. Automatic migration via plugin SessionStart hook

The plugin gains two files:

- `hooks/hooks.json`: registers a `SessionStart` command hook (matcher `startup|clear|compact`, same shape as the superpowers plugin uses) running `"${CLAUDE_PLUGIN_ROOT}/hooks/heal-hook.sh"` with `shell: bash`, `async: false`.
- `hooks/heal-hook.sh`: silent fast no-op unless ALL of:
  1. The current directory is inside a git work tree (`git rev-parse --git-dir`).
  2. `<git-dir>/hooks/pre-commit` exists and contains the voice-check start marker.
  3. The `VOICE_CHECK_ENGINE="..."` path parsed from that section does not exist on disk.

  When all three hold, it runs `"$CLAUDE_PLUGIN_ROOT/templates/install-hook.sh" <repo-root>`, which re-renders the section with the new self-healing template, and prints one line (`voice-check: healed stale pre-commit hook`). Any failure inside the healer exits 0 silently; a session must never break because of it.

Result: upgrade the plugin, and the first Claude Code session in an affected repo repairs its hook automatically. From then on the git hook resolves the engine itself at commit time, so the healer never fires for that repo again; it stays as a safety net.

### Boundary

The healer only repairs repos that already contain the voice-check marker section. It never installs the hook into new repos. `install-hook.sh` remains the explicit opt-in and its install logic is unchanged (only its header comment changes: the "re-run after upgrading" instruction becomes a note that hooks self-heal).

## Out of scope

- Repos where the user never opens Claude Code cannot be healed by anything; they keep the old nag until a session happens there or the installer is run manually. Documented as a known limitation.
- No changes to the engine, rules, or skills.

## Documentation updates

- CLAUDE.md hook installation section: replace the "must re-run install-hook.sh after upgrading" sentence with the self-healing behavior and the SessionStart healer.
- README: same change wherever re-running is mentioned.

## Version

Bump `plugin.json` to 2.2.1 so the marketplace serves the new template and healer.

## Testing

Pytest cases in the existing suite (subprocess + temp dirs, no new infra):

1. Rendered hook with a dead baked path resolves the newest fake cache version (temp `HOME` with `2.1.0` and `2.2.0` dirs, assert the `2.2.0` engine runs).
2. Rendered hook with no engine anywhere prints the advisory line and exits 0.
3. Healer heals: temp repo whose pre-commit contains a voice-check section with a dead baked path; run `heal-hook.sh` with `CLAUDE_PLUGIN_ROOT` pointing at the plugin source and `HOME` pointing at a temp dir with a fake cache (so the installer resolves the fake cache engine, exercising the same path a real upgrade uses); assert the section now contains the runtime-resolution logic and the hook stays executable.
4. Healer no-ops: (a) healthy baked path, (b) pre-commit without the marker, (c) not a git repo. Assert the hook file is byte-identical afterward (or absent) and exit code 0.

The full existing suite (46 cases) stays green.
