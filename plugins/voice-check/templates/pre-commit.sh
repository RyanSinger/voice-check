#!/usr/bin/env bash
# voice-check pre-commit hook (advisory, report-only)
# Installed by: voice-check plugin install-hook.sh
# === voice-check section start ===
# voice-check hook version: 2.4.0

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

# Extract the added-line ranges for one staged file from its diff hunks.
# Prints "12-18,40-41" or nothing. Falls back to nothing on any failure, and
# an empty result means the whole file is scanned.
#
# Safe under "set -e" with no explicit "|| true" on the assignment below.
# Not because testing the result later exempts the assignment, it does not,
# but because this pipeline has no "pipefail": its exit status is sed's, and
# sed exits 0 on essentially any input, including empty input or a failed
# git diff upstream. If the final stage ever stops being sed, re-check that
# this still holds or add "|| true" to the assignment explicitly.
changed_ranges() {
  git diff --cached -U0 -- "$1" 2>/dev/null | awk '
    /^@@/ {
      if (match($0, /\+[0-9]+(,[0-9]+)?/)) {
        spec = substr($0, RSTART + 1, RLENGTH - 1)
        split(spec, a, ",")
        start = a[1]
        len = (a[2] == "" ? 1 : a[2])
        if (len > 0) printf "%s-%s,", start, start + len - 1
      }
    }
  ' | sed 's/,$//'
}

while IFS= read -r f; do
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    continue
  fi

  ranges=$(changed_ranges "$f")

  # changed_ranges reports line numbers in the STAGED (index) blob, but the
  # engine reads the file from the WORKING TREE. Those line numbers only
  # line up when the two copies match. If a file was staged with `git add
  # -p` and then edited further, or staged and then edited again without
  # re-staging, the working tree has diverged from the index and the range
  # would point at the wrong lines. Clear it so the existing empty-ranges
  # branch below falls back to a whole file scan: this degrades toward
  # reporting more, which is this project's stated principle.
  if [ -n "$ranges" ] && ! git diff --quiet -- "$f"; then
    ranges=""
  fi

  if [ -n "$ranges" ]; then
    out=$("$PYTHON" "$ENGINE" --report-only --lines "$ranges" "$f" 2>&1 || true)
  else
    out=$("$PYTHON" "$ENGINE" --report-only "$f" 2>&1 || true)
  fi

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
