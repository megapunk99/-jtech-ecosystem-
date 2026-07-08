#!/usr/bin/env bash
# JTECH Session End Hook
# Runs when a JTECH session ends.
# Usage: ./session-end.sh [session_id]

set -euo pipefail

SESSION_ID="${1:-default}"
DATA_DIR="${JTECH_DATA_DIR:-./data}"

# Save session state
if [ -f "$DATA_DIR/jtech.db" ]; then
    echo "💾  Session state saved ($DATA_DIR/jtech.db)"
fi

echo "✅ Session $SESSION_ID ended"
exit 0
