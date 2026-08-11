#!/usr/bin/env bash
# voice-check pre-commit hook (advisory, report-only)
# Installed by: voice-check plugin install-hook.sh
# === voice-check section start ===

set -e

# Baked at install time; fast path while it remains valid. If a plugin
# upgrade moves the cache directory, resolve_engine falls back to the
# newest installed version at commit time, so the hook self-heals.
BAKED_ENGINE="__VOICE_CHECK_ENGINE__"

resolve_engine() {
  if [ -n "${VOICE_CHECK_ENGINE:-}" ] && [ -f "${VOICE_CHECK_ENGINE:-}" ]; then
    echo "$VOICE_CHECK_ENGINE"
    return
  fi
  if [ -f "$BAKED_ENGINE" ]; then
    echo "$BAKED_ENGINE"
    return
  fi
  newest=$(find "$HOME/.claude/plugins/cache/voice-check" -path "*/engine/voice_check.py" 2>/dev/null | sort -V | tail -1)
  if [ -n "$newest" ]; then
    echo "$newest"
    return
  fi
  if [ -f "$HOME/.claude/skills/voice-check/engine/voice_check.py" ]; then
    echo "$HOME/.claude/skills/voice-check/engine/voice_check.py"
    return
  fi
  true
}

ENGINE="$(resolve_engine)"

if [ -z "$ENGINE" ]; then
  echo "voice-check: engine not found (is the voice-check plugin installed?), skipping scan"
  exit 0
fi

PYTHON="${VOICE_CHECK_PYTHON:-python3}"

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
  out=$("$PYTHON" "$ENGINE" --report-only "$f" 2>&1 || true)
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

exit 0
# === voice-check section end ===
