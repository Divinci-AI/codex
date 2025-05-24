#!/bin/bash
# Session End Logging Hook
# This script logs when a Codex session ends

# Available environment variables:
# CODEX_EVENT_TYPE - The type of lifecycle event (session_end)
# CODEX_SESSION_ID - Current session ID
# CODEX_TIMESTAMP - Event timestamp
# CODEX_DURATION - Session duration in milliseconds (if available)

LOG_FILE="${HOME}/.codex/session.log"
TIMESTAMP="${CODEX_TIMESTAMP:-$(date -Iseconds)}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Format duration if available
DURATION_MSG=""
if [ -n "$CODEX_DURATION" ]; then
    DURATION_SECONDS=$((CODEX_DURATION / 1000))
    DURATION_MSG=" (duration: ${DURATION_SECONDS}s)"
fi

# Log session end
echo "[$TIMESTAMP] SESSION_END: Session $CODEX_SESSION_ID ended$DURATION_MSG" >> "$LOG_FILE"

# Optional: Send notification
if command -v notify-send >/dev/null 2>&1; then
    notify-send "Codex Session Ended" "Session $CODEX_SESSION_ID ended$DURATION_MSG"
elif command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"Session $CODEX_SESSION_ID ended$DURATION_MSG\" with title \"Codex Session Ended\""
fi

echo "Session end logged to $LOG_FILE"
