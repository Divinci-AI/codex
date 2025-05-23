#!/bin/bash

# Example onTaskStart hook script
# This script is executed when a Codex task begins

echo "🚀 Codex task started!"
echo "Session ID: $CODEX_SESSION_ID"
echo "Model: $CODEX_MODEL"
echo "Event Type: $CODEX_EVENT_TYPE"
echo "Working Directory: $CODEX_WORKING_DIR"
echo "Timestamp: $(date)"

# Read event data from stdin
EVENT_DATA=$(cat)
echo "Event Data: $EVENT_DATA"

# Example: Log to a file
echo "$(date): Task started with session $CODEX_SESSION_ID" >> ~/.codex/task-log.txt

# Example: Send notification (uncomment if you have a webhook)
# curl -X POST "$SLACK_WEBHOOK_URL" \
#   -H 'Content-Type: application/json' \
#   -d "{\"text\":\"🚀 Codex task started in $(pwd)\"}"

exit 0
