#!/usr/bin/env bash
# Install the voice-check pre-commit hook into a git repo.
# Resolves the absolute path to the voice-check engine in the plugin cache
# at install time and embeds it into the per-repo hook. Re-run after
# upgrading the voice-check plugin so the hook picks up the new version path.
#
# Usage: install-hook.sh [/path/to/repo]
# If no path given, uses the current directory.

set -e

REPO_DIR="${1:-$(pwd)}"
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$TEMPLATE_DIR/pre-commit.sh"
HOOK_DIR="$REPO_DIR/.git/hooks"
HOOK="$HOOK_DIR/pre-commit"
MARKER_START="# === voice-check section start ==="
MARKER_END="# === voice-check section end ==="

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "error: $REPO_DIR is not a git repo"
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "error: hook template not found at $TEMPLATE"
  exit 1
fi

# Resolve the engine path. Prefer the plugin cache (marketplace install).
# Fall back to the legacy direct-clone location for users on v1.
ENGINE=""

# 1. Look in the plugin cache (marketplace install)
PLUGIN_CACHE_HIT=$(find "$HOME/.claude/plugins/cache" -path "*plugins/voice-check/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
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

# Render the template with the resolved engine path
RENDERED=$(mktemp)
sed "s|__VOICE_CHECK_ENGINE__|$ENGINE|" "$TEMPLATE" > "$RENDERED"

if [ ! -f "$HOOK" ]; then
  # No existing hook, install fresh
  cp "$RENDERED" "$HOOK"
  chmod +x "$HOOK"
  rm "$RENDERED"
  echo "installed: $HOOK (fresh)"
  exit 0
fi

# Existing hook present
if grep -q "$MARKER_START" "$HOOK"; then
  # voice-check section already present, replace it in place
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    $0 ~ start { skip=1; next }
    $0 ~ end { skip=0; next }
    !skip
  ' "$HOOK" > "$HOOK.tmp"
  echo "" >> "$HOOK.tmp"
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    $0 ~ start { in_section=1 }
    in_section { print }
    $0 ~ end { in_section=0 }
  ' "$RENDERED" >> "$HOOK.tmp"
  mv "$HOOK.tmp" "$HOOK"
  chmod +x "$HOOK"
  rm "$RENDERED"
  echo "installed: $HOOK (replaced existing voice-check section)"
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
