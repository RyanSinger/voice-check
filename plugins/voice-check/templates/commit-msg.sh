#!/usr/bin/env bash
# voice-check commit-msg hook (advisory, report-only)
# Installed by: voice-check plugin install-hook.sh
# === voice-check section start ===
# voice-check hook version: 2.5.0

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

# The scratch files live at the checkout's own top level, not /tmp and not
# the git directory, on purpose. The engine discovers a repo's
# .claude/voice-check.md by walking up from the scanned file to the git
# root, so a file in /tmp would silently miss this repo's supplement. And
# git rev-parse --git-common-dir is the wrong root in a linked worktree: it
# resolves to the MAIN repository's .git there, so a scratch file placed
# under it would walk up to the main checkout and apply that repo's
# supplement instead of the worktree's own, while pre-commit.sh scanning a
# real file in the same worktree would apply the worktree's supplement.
# git rev-parse --show-toplevel resolves to the worktree's own root in a
# linked worktree, and to the repo root in a normal checkout, matching what
# pre-commit.sh sees. If --show-toplevel fails or is empty (a bare
# repository, for instance), fall back to --git-common-dir rather than
# giving up entirely.
SCRATCH_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || SCRATCH_ROOT=""
if [ -z "$SCRATCH_ROOT" ]; then
  SCRATCH_ROOT=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
fi
case "$SCRATCH_ROOT" in
  /*) ;;
  *) SCRATCH_ROOT="$(pwd)/$SCRATCH_ROOT" ;;
esac

# A leading dot keeps these inert if a crash ever outlives the trap below:
# they read as an ordinary hidden file rather than a stray voice-check name.
CUT_FILE="$SCRATCH_ROOT/.voice-check-commit-msg.cut"
SCAN_FILE="$SCRATCH_ROOT/.voice-check-commit-msg.scan"
# Every exit path, including the failure paths. A hook that litters on every
# commit is its own defect. The trap itself must never fail: under set -e a
# failing command in an EXIT trap overrides the status the script was
# exiting with, so a stray rm failure (a scratch path that became a
# directory, a permission problem, a read only checkout) would turn a
# correct exit 0 into a nonzero status and block the commit. The
# "|| true" guards against exactly that.
trap 'rm -f "$CUT_FILE" "$SCAN_FILE" 2>/dev/null || true' EXIT

# The message file is not the message. It carries git's instruction comments,
# and under commit.verbose the entire staged diff below a scissors line.
#
# `git stripspace --strip-comments` alone is NOT enough: it strips the
# scissors line itself (a comment) and leaves every diff line beneath it, so
# an em dash in someone else's code would be reported as a finding on this
# commit message. Cut at the scissors marker FIRST, then strip comments.
# A message with no scissors line loses nothing to the cut.
#
# The comment character is configurable (core.commentChar), and the
# scissors line is built from it, so the cut has to read the same setting
# `git stripspace --strip-comments` already honors, rather than hardcode
# "#". Unset and the literal value "auto" both mean git is using "#".
CC=$(git config --get core.commentChar 2>/dev/null) || CC=""
case "$CC" in
  ""|auto) CC="#" ;;
esac

# awk rather than sed for the cut: the comment character can be a regex
# metacharacter (".", "*", and "^" are all legal values), and comparing it
# as a literal string with substr means it never needs escaping.
#
# If either stage fails, fall back to the raw message file. That degrades
# toward reporting more, which is this project's stated principle, and the
# worst case is a finding on a comment line rather than a missed one.
if awk -v cc="$CC" \
     'substr($0,1,1)==cc && index($0,">8")>0 {exit} {print}' \
     "$MSG_FILE" > "$CUT_FILE" 2>/dev/null \
   && git stripspace --strip-comments < "$CUT_FILE" > "$SCAN_FILE" 2>/dev/null; then
  :
else
  cp "$MSG_FILE" "$SCAN_FILE" 2>/dev/null || exit 0
fi

# Empty after stripping means an aborted commit, not a clean one.
if [ ! -s "$SCAN_FILE" ]; then
  exit 0
fi

# --report-only contractually exits 0. A nonzero status means the engine
# never ran (an older cached engine without --surface, a broken $PYTHON),
# not that it found something, so the "|| out=" branch discards whatever
# usage or error text it printed instead of showing it as a finding. This
# still must not trip set -e: "|| out=" keeps the overall status zero.
out=$("$PYTHON" "$ENGINE" --report-only --surface commit "$SCAN_FILE" 2>&1) || out=""

if [ -n "$out" ]; then
  echo "voice-check: commit message findings (advisory only, commit will proceed)"
  echo "$out"
  echo "  to bypass: git commit --no-verify"
fi

exit 0
# === voice-check section end ===
