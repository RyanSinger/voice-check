#!/usr/bin/env bash
# voice-check SessionStart healer.
# Repairs this repo's installed voice-check git hooks in two cases: the
# engine path baked into one stopped resolving (a plugin upgrade moved the
# cache directory), or a hook body itself is stale (a plugin upgrade changed
# what a template does, without necessarily moving the cache directory, so
# the dead path check alone would never catch it).
# Exits 0 in every case; a session must never break because of this hook.

set -u

MARKER="# === voice-check section start ==="

# Every hook this plugin installs. templates/install-hook.sh keeps its own
# copy of this list; the two must agree.
HOOK_NAMES="pre-commit commit-msg"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac

PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT:-}/.claude-plugin/plugin.json"
PLUGIN_VERSION=""
if [ -f "$PLUGIN_JSON" ]; then
  PLUGIN_VERSION=$(sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$PLUGIN_JSON" | head -1)
fi

# FOUND records whether this repo ever opted in to voice-check hooks. A repo
# with no marked hook at all is not one we install into: the installer is the
# opt in, and healing must never become a back door for it. That also means a
# commit-msg hook a user deliberately deleted stays deleted, but only until
# the next version bump: once the pre-commit stamp falls behind plugin.json,
# NEEDS_HEAL trips and one heal writes both hooks again. Every install in the
# field is stamped 2.4.0 or older, so the version bump that ships this makes
# them stale right away and one heal writes both hooks anyway.
FOUND=0
NEEDS_HEAL=0

for name in $HOOK_NAMES; do
  HOOK="$GIT_COMMON/hooks/$name"
  [ -f "$HOOK" ] || continue
  grep -qF "$MARKER" "$HOOK" || continue
  FOUND=1

  # Old installs bake VOICE_CHECK_ENGINE=; the self-healing template bakes
  # BAKED_ENGINE=. Either way, a live path alone means nothing to heal, but
  # the version stamp check below can still trigger a reinstall.
  BAKED=$(sed -n 's/^BAKED_ENGINE="\(.*\)"$/\1/p; s/^VOICE_CHECK_ENGINE="\(.*\)"$/\1/p' "$HOOK" | head -1)
  [ -n "$BAKED" ] || continue
  [ -f "$BAKED" ] || NEEDS_HEAL=1

  # The dead path check above catches an engine that moved. It does not catch
  # a hook body that is simply outdated (for example, missing diff scoping
  # added in a later release) while its baked path still happens to resolve.
  # Compare the hook's own version stamp against the plugin's current
  # version and reinstall on any mismatch, absent or not. A plain string
  # inequality is enough here: we only need to know the stamp is not current,
  # not order it against every past version.
  if [ -n "$PLUGIN_VERSION" ]; then
    STAMP=$(sed -n 's/^# voice-check hook version: \(.*\)$/\1/p' "$HOOK" | head -1)
    if [ "$STAMP" != "$PLUGIN_VERSION" ]; then
      NEEDS_HEAL=1
    fi
  fi
done

[ "$FOUND" = "1" ] || exit 0
[ "$NEEDS_HEAL" = "1" ] || exit 0

INSTALLER="${CLAUDE_PLUGIN_ROOT:-}/templates/install-hook.sh"
[ -f "$INSTALLER" ] || exit 0

# The installer writes every hook in its list, so one run repairs the pair.
# A half healed install, where one hook is current and the other is stale,
# is worse than an unhealed one because nothing surfaces the mismatch.
if bash "$INSTALLER" "$REPO_ROOT" >/dev/null 2>&1; then
  echo "voice-check: healed stale git hooks in $REPO_ROOT"
fi
exit 0
