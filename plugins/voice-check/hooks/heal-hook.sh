#!/usr/bin/env bash
# voice-check SessionStart healer.
# Repairs this repo's installed pre-commit hook in two cases: the engine
# path baked into it stopped resolving (a plugin upgrade moved the cache
# directory), or the hook body itself is stale (a plugin upgrade changed
# what pre-commit.sh does, without necessarily moving the cache directory,
# so the dead path check alone would never catch it).
# Exits 0 in every case; a session must never break because of this hook.

set -u

MARKER="# === voice-check section start ==="

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac
HOOK="$GIT_COMMON/hooks/pre-commit"
[ -f "$HOOK" ] || exit 0
grep -qF "$MARKER" "$HOOK" || exit 0

# Old installs bake VOICE_CHECK_ENGINE=; the self-healing template bakes
# BAKED_ENGINE=. Either way, a live path alone means nothing to heal, but
# the version stamp check below can still trigger a reinstall.
BAKED=$(sed -n 's/^BAKED_ENGINE="\(.*\)"$/\1/p; s/^VOICE_CHECK_ENGINE="\(.*\)"$/\1/p' "$HOOK" | head -1)
[ -n "$BAKED" ] || exit 0

NEEDS_HEAL=0
[ -f "$BAKED" ] || NEEDS_HEAL=1

# The dead path check above catches an engine that moved. It does not catch
# a hook body that is simply outdated (for example, missing diff scoping
# added in a later release) while its baked path still happens to resolve.
# Compare the hook's own version stamp against the plugin's current
# version and reinstall on any mismatch, absent or not. A plain string
# inequality is enough here: we only need to know the stamp is not current,
# not order it against every past version.
PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT:-}/.claude-plugin/plugin.json"
if [ "$NEEDS_HEAL" = "0" ] && [ -f "$PLUGIN_JSON" ]; then
  PLUGIN_VERSION=$(sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" | head -1)
  STAMP=$(sed -n 's/^# voice-check hook version: \(.*\)$/\1/p' "$HOOK" | head -1)
  if [ -n "$PLUGIN_VERSION" ] && [ "$STAMP" != "$PLUGIN_VERSION" ]; then
    NEEDS_HEAL=1
  fi
fi

[ "$NEEDS_HEAL" = "1" ] || exit 0

INSTALLER="${CLAUDE_PLUGIN_ROOT:-}/templates/install-hook.sh"
[ -f "$INSTALLER" ] || exit 0

if bash "$INSTALLER" "$REPO_ROOT" >/dev/null 2>&1; then
  echo "voice-check: healed stale pre-commit hook in $REPO_ROOT"
fi
exit 0
