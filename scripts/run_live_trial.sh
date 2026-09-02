#!/bin/zsh
# Day 1 live trial: Hy3 through terminus-2 on one cheap gate-passing task.
# Requires ~/termscope-work/hy3-creds.env with:
#   OPENAI_API_KEY=<hy3 key>
#   OPENAI_BASE_URL=https://tokenhub.tencentmaas.com/v1
set -e
export PATH="$HOME/.local/bin:$PATH"
CREDS="$HOME/termscope-work/hy3-creds.env"
if [[ ! -s "$CREDS" ]]; then
  echo "missing $CREDS — create it first (never printed, only passed to harbor)" >&2
  exit 1
fi
TASK="${1:-fix-git}"
harbor run \
  -d terminal-bench@2.0 \
  -a terminus-2 \
  -m openai/hy3 \
  --env-file "$CREDS" \
  -i "$TASK" \
  -o "$HOME/termscope-work/jobs" \
  --job-name "day1-live-terminus-$TASK" \
  -n 1 -q -y
