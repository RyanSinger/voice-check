#!/usr/bin/env bash
# voice-check commit-msg hook (advisory, report-only)
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

MSG_FILE="$1"
if [ -z "$MSG_FILE" ] || [ ! -f "$MSG_FILE" ]; then
  exit 0
fi

ENGINE="$(resolve_engine)"

# Silent, unlike pre-commit.sh, which prints an "engine not found" notice.
# Both hooks run on the same commit, so the pre-commit hook already surfaces
# that notice and repeating it here would only double the noise.
if [ -z "$ENGINE" ]; then
  exit 0
fi

PYTHON="${VOICE_CHECK_PYTHON:-python3}"

# The scratch files live in the git directory, not /tmp, on purpose. The
# engine discovers a repo's .claude/voice-check.md by walking up from the
# scanned file to the git root, so a file in /tmp would silently miss this
# repo's supplement. From "<git dir>/voice-check-commit-msg.scan" the walk
# reaches the repo root and finds it.
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
case "$GIT_COMMON" in
  /*) ;;
  *) GIT_COMMON="$(pwd)/$GIT_COMMON" ;;
esac

CUT_FILE="$GIT_COMMON/voice-check-commit-msg.cut"
SCAN_FILE="$GIT_COMMON/voice-check-commit-msg.scan"
# Every exit path, including the failure paths. A hook that litters on every
# commit is its own defect.
trap 'rm -f "$CUT_FILE" "$SCAN_FILE"' EXIT

# The message file is not the message. It carries git's instruction comments,
# and under commit.verbose the entire staged diff below a scissors line.
#
# `git stripspace --strip-comments` alone is NOT enough: it strips the
# scissors line itself (a comment) and leaves every diff line beneath it, so
# an em dash in someone else's code would be reported as a finding on this
# commit message. Cut at the scissors marker FIRST, then strip comments.
# A message with no scissors line loses nothing to the cut.
#
# If either stage fails, fall back to the raw message file. That degrades
# toward reporting more, which is this project's stated principle, and the
# worst case is a finding on a comment line rather than a missed one.
if sed '/^#.*>8/,$d' "$MSG_FILE" > "$CUT_FILE" 2>/dev/null \
   && git stripspace --strip-comments < "$CUT_FILE" > "$SCAN_FILE" 2>/dev/null; then
  :
else
  cp "$MSG_FILE" "$SCAN_FILE" 2>/dev/null || exit 0
fi

# Empty after stripping means an aborted commit, not a clean one.
if [ ! -s "$SCAN_FILE" ]; then
  exit 0
fi

out=$("$PYTHON" "$ENGINE" --report-only --surface commit "$SCAN_FILE" 2>&1 || true)

if [ -n "$out" ]; then
  echo "voice-check: commit message findings (advisory only, commit will proceed)"
  echo "$out"
  echo "  to bypass: git commit --no-verify"
fi

exit 0
# === voice-check section end ===
