#!/usr/bin/env bash
# Install the voice-check pre-commit hook into the current git repo.
# Usage: install-hook.sh [/path/to/repo]
# If no path given, uses the current directory.

set -e

REPO_DIR="${1:-$(pwd)}"
TEMPLATE="$HOME/.claude/skills/voice-check/templates/pre-commit.sh"
HOOK_DIR="$REPO_DIR/.git/hooks"
HOOK="$HOOK_DIR/pre-commit"
MARKER_START="# === voice-check section start ==="
MARKER_END="# === voice-check section end ==="

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "error: $REPO_DIR is not a git repo"
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "error: template not found at $TEMPLATE"
  exit 1
fi

mkdir -p "$HOOK_DIR"

if [ ! -f "$HOOK" ]; then
  # No existing hook, install fresh
  cp "$TEMPLATE" "$HOOK"
  chmod +x "$HOOK"
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
  # Append the fresh voice-check section from the template
  echo "" >> "$HOOK.tmp"
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    $0 ~ start { in_section=1 }
    in_section { print }
    $0 ~ end { in_section=0 }
  ' "$TEMPLATE" >> "$HOOK.tmp"
  mv "$HOOK.tmp" "$HOOK"
  chmod +x "$HOOK"
  echo "installed: $HOOK (replaced existing voice-check section)"
else
  # Append voice-check section to the end of the existing hook
  echo "" >> "$HOOK"
  awk -v start="$MARKER_START" -v end="$MARKER_END" '
    $0 ~ start { in_section=1 }
    in_section { print }
    $0 ~ end { in_section=0 }
  ' "$TEMPLATE" >> "$HOOK"
  chmod +x "$HOOK"
  echo "installed: $HOOK (appended to existing hook)"
fi
