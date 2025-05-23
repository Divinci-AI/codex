#!/bin/bash

# Example onTaskComplete hook script
# This script is executed when a Codex task completes

echo "✅ Codex task completed!"
echo "Session ID: $CODEX_SESSION_ID"
echo "Model: $CODEX_MODEL"
echo "Event Type: $CODEX_EVENT_TYPE"
echo "Working Directory: $CODEX_WORKING_DIR"
echo "Timestamp: $(date)"

# Read event data from stdin
EVENT_DATA=$(cat)
echo "Event Data: $EVENT_DATA"

# Check if task was successful
SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false')
if [ "$SUCCESS" = "true" ]; then
    echo "🎉 Task completed successfully!"
    
    # Example: Auto-commit changes if in a git repo
    if git rev-parse --git-dir > /dev/null 2>&1; then
        echo "📝 Auto-committing changes..."
        git add .
        git commit -m "Codex: Automated changes from session $CODEX_SESSION_ID" || echo "No changes to commit"
    fi
    
    # Example: Send success notification
    # curl -X POST "$SLACK_WEBHOOK_URL" \
    #   -H 'Content-Type: application/json' \
    #   -d "{\"text\":\"✅ Codex task completed successfully in $(pwd)\"}"
else
    echo "⚠️ Task completed with issues"
fi

# Log completion
echo "$(date): Task completed with session $CODEX_SESSION_ID (success: $SUCCESS)" >> ~/.codex/task-log.txt

exit 0
