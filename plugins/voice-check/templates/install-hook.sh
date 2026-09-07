#!/usr/bin/env bash
# Install the voice-check git hooks into a repo.
# Resolves the absolute path to the voice-check engine in the plugin cache
# at install time and embeds it as each hook's fast path. Installed hooks
# self-heal: they re-resolve the engine at commit time after upgrades, and
# the plugin's SessionStart healer rewrites stale hook sections.
# Re-running this installer is always safe (idempotent) but no longer
# required after upgrades.
#
# Two hooks are installed: pre-commit scans staged files, commit-msg scans
# the commit message itself with a restricted rule set.
#
# Usage: install-hook.sh [/path/to/repo]
# If no path given, uses the current directory.

set -e

REPO_DIR="${1:-$(pwd)}"
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Every hook this plugin installs. Each name maps to "<name>.sh" in the
# template directory and to "<name>" in the repo's hooks directory. Adding a
# hook means adding its name here and its template beside the others; nothing
# below is per hook. hooks/heal-hook.sh keeps its own copy of this list.
HOOK_NAMES="pre-commit commit-msg"

# Hooks live in the common git dir, shared by every linked worktree.
GIT_COMMON=$(git -C "$REPO_DIR" rev-parse --git-common-dir 2>/dev/null) || {
  echo "error: $REPO_DIR is not a git repo"
  exit 1
}
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$REPO_DIR/$GIT_COMMON" ;;
esac
HOOK_DIR="$GIT_COMMON/hooks"
MARKER_START="# === voice-check section start ==="
MARKER_END="# === voice-check section end ==="

for name in $HOOK_NAMES; do
  if [ ! -f "$TEMPLATE_DIR/$name.sh" ]; then
    echo "error: hook template not found at $TEMPLATE_DIR/$name.sh"
    exit 1
  fi
done

# Resolve the engine path. Prefer the plugin cache (marketplace install).
# Fall back to the legacy direct-clone location for users on v1.
ENGINE=""

# 1. Look in the plugin cache (marketplace install)
# Layout: ~/.claude/plugins/cache/voice-check/voice-check/<version>/engine/voice_check.py
PLUGIN_CACHE_HIT=$(find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
if [ -n "$PLUGIN_CACHE_HIT" ]; then
  ENGINE="$PLUGIN_CACHE_HIT"
fi

# 2. Fall back to legacy direct-clone path
if [ -z "$ENGINE" ] && [ -f "$HOME/.claude/skills/voice-check/engine/voice_check.py" ]; then
  ENGINE="$HOME/.claude/skills/voice-check/engine/voice_check.py"
fi

# 3. Last resort: walk up from the template's own location
if [ -z "$ENGINE" ]; then
  CANDIDATE="$(cd "$TEMPLATE_DIR/.." && pwd)/engine/voice_check.py"
  if [ -f "$CANDIDATE" ]; then
    ENGINE="$CANDIDATE"
  fi
fi

if [ -z "$ENGINE" ]; then
  echo "error: voice-check engine not found"
  echo "install via: claude plugin marketplace add RyanSinger/voice-check"
  echo "        and: claude plugin install voice-check@voice-check"
  exit 1
fi

echo "resolved engine: $ENGINE"

mkdir -p "$HOOK_DIR"

# Install one hook. $1 is the hook name, which is also its template basename.
# The four paths below (fresh, wiped v1 leftovers, replaced section, appended)
# are the original per hook logic, unchanged.
install_one() {
  name="$1"
  TEMPLATE="$TEMPLATE_DIR/$name.sh"
  HOOK="$HOOK_DIR/$name"

  # Render the template with the resolved engine path
  RENDERED=$(mktemp)
  sed "s|__VOICE_CHECK_ENGINE__|$ENGINE|" "$TEMPLATE" > "$RENDERED"

  if [ ! -f "$HOOK" ]; then
    # No existing hook, install fresh
    cp "$RENDERED" "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (fresh)"
    return 0
  fi

  # Existing hook present
  if grep -q "$MARKER_START" "$HOOK"; then
    # Voice-check section already present. Strip it and check what's left.
    STRIPPED=$(mktemp)
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
      $0 ~ start { skip=1; next }
      $0 ~ end { skip=0; next }
      !skip
    ' "$HOOK" > "$STRIPPED"

    # If the stripped file contains only boilerplate (shebang, comments, blanks,
    # and maybe a bare `exit 0`), the hook was entirely voice-check's. Wipe and
    # reinstall fresh to avoid orphaned exit statements from older templates.
    MEANINGFUL=$(grep -vE '^\s*$|^\s*#|^\s*exit 0\s*$|^#!' "$STRIPPED" | wc -l | tr -d ' ')
    if [ "$MEANINGFUL" = "0" ]; then
      cp "$RENDERED" "$HOOK"
      chmod +x "$HOOK"
      rm "$RENDERED" "$STRIPPED"
      echo "installed: $HOOK (wiped v1 leftovers and installed fresh)"
      return 0
    fi

    # Otherwise there's other content: append fresh section after the stripped file
    echo "" >> "$STRIPPED"
    cat "$RENDERED" >> "$STRIPPED"
    mv "$STRIPPED" "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (replaced voice-check section, preserved other hooks)"
  else
    # Append voice-check section to the end of the existing hook
    echo "" >> "$HOOK"
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
      $0 ~ start { in_section=1 }
      in_section { print }
      $0 ~ end { in_section=0 }
    ' "$RENDERED" >> "$HOOK"
    chmod +x "$HOOK"
    rm "$RENDERED"
    echo "installed: $HOOK (appended to existing hook)"
  fi
}

for name in $HOOK_NAMES; do
  install_one "$name"
done
