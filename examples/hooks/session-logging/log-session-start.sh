#!/bin/bash
# Session Start Logging Hook
# This script logs when a Codex session starts

# Available environment variables:
# CODEX_EVENT_TYPE - The type of lifecycle event (session_start)
# CODEX_SESSION_ID - Current session ID
# CODEX_TIMESTAMP - Event timestamp
# CODEX_MODEL - The model being used
# CODEX_PROVIDER - The provider (e.g., openai, azure)

LOG_FILE="${HOME}/.codex/session.log"
TIMESTAMP="${CODEX_TIMESTAMP:-$(date -Iseconds)}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Log session start
echo "[$TIMESTAMP] SESSION_START: Session $CODEX_SESSION_ID started with model $CODEX_MODEL (provider: ${CODEX_PROVIDER:-openai})" >> "$LOG_FILE"

# Optional: Send notification (requires notify-send on Linux or osascript on macOS)
if command -v notify-send >/dev/null 2>&1; then
    notify-send "Codex Session Started" "Session $CODEX_SESSION_ID with model $CODEX_MODEL"
elif command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"Session $CODEX_SESSION_ID with model $CODEX_MODEL\" with title \"Codex Session Started\""
fi

echo "Session start logged to $LOG_FILE"
