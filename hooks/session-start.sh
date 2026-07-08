#!/usr/bin/env bash
# JTECH Session Start Hook
# Runs when a JTECH session starts.
# Usage: ./session-start.sh [session_id]

set -euo pipefail

SESSION_ID="${1:-default}"
DATA_DIR="${JTECH_DATA_DIR:-./data}"
WORKSPACE_DIR="${JTECH_WORKSPACE_ROOT:-./workspace}"

# Ensure directories exist
mkdir -p "$DATA_DIR"
mkdir -p "$WORKSPACE_DIR"

# Verify environment
if [ -z "${NVIDIA_API_KEY:-}" ] && [ -z "${NVIDIA_API_KEY_1:-}" ]; then
    echo "⚠️  Warning: No NVIDIA API key configured. Set NVIDIA_API_KEY in .env"
fi

echo "✅ Session $SESSION_ID started"
exit 0
