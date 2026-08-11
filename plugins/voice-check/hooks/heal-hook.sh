#!/usr/bin/env bash
# voice-check SessionStart healer.
# Repairs this repo's installed pre-commit hook when the engine path baked
# into it stopped resolving (a plugin upgrade moved the cache directory).
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
# BAKED_ENGINE=. Either way, a live path means nothing to heal.
BAKED=$(sed -n 's/^BAKED_ENGINE="\(.*\)"$/\1/p; s/^VOICE_CHECK_ENGINE="\(.*\)"$/\1/p' "$HOOK" | head -1)
[ -n "$BAKED" ] || exit 0
[ -f "$BAKED" ] && exit 0

INSTALLER="${CLAUDE_PLUGIN_ROOT:-}/templates/install-hook.sh"
[ -f "$INSTALLER" ] || exit 0

if bash "$INSTALLER" "$REPO_ROOT" >/dev/null 2>&1; then
  echo "voice-check: healed stale pre-commit hook in $REPO_ROOT"
fi
exit 0
