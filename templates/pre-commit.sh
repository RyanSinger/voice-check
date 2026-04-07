#!/usr/bin/env bash
# voice-check pre-commit hook (advisory, report-only)
# Installed by: ~/.claude/skills/voice-check/templates/install-hook.sh
# === voice-check section start ===

set -e

VOICE_CHECK_ENGINE="$HOME/.claude/skills/voice-check/engine/voice_check.py"
VOICE_CHECK_VENV="$HOME/.claude/skills/voice-check/.venv/bin/python"

if [ -x "$VOICE_CHECK_VENV" ]; then
  PYTHON="$VOICE_CHECK_VENV"
else
  PYTHON="${VOICE_CHECK_PYTHON:-python3}"
fi

if [ ! -f "$VOICE_CHECK_ENGINE" ]; then
  echo "voice-check: engine not found at $VOICE_CHECK_ENGINE (skipping)"
  exit 0
fi

staged_md=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$' || true)

if [ -z "$staged_md" ]; then
  exit 0
fi

count=$(echo "$staged_md" | wc -l | tr -d ' ')
echo "voice-check: scanning $count staged markdown file(s)"

findings_total=0
while IFS= read -r f; do
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    continue
  fi
  out=$("$PYTHON" "$VOICE_CHECK_ENGINE" --report-only "$f" 2>&1 || true)
  if [ -n "$out" ]; then
    echo "--- $f ---"
    echo "$out"
    findings_total=$((findings_total + 1))
  fi
done <<< "$staged_md"

if [ "$findings_total" -gt 0 ]; then
  echo ""
  echo "voice-check: $findings_total file(s) with findings (advisory only, commit will proceed)"
  echo "  to fix:    /voice-check <file>"
  echo "  to bypass: git commit --no-verify"
fi

# === voice-check section end ===
exit 0
