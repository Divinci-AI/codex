#!/bin/bash

# Example onCommandStart hook script
# This script is executed before each command runs

echo "⚡ About to execute command: $CODEX_COMMAND"
echo "Working directory: $CODEX_WORKING_DIR"
echo "Session: $CODEX_SESSION_ID"
echo "Timestamp: $(date)"

# Read event data from stdin
EVENT_DATA=$(cat)

# Extract command details
COMMAND=$(echo "$EVENT_DATA" | jq -r '.command | join(" ")' 2>/dev/null || echo "$CODEX_COMMAND")
WORKDIR=$(echo "$EVENT_DATA" | jq -r '.workdir // "."' 2>/dev/null || echo "$CODEX_WORKING_DIR")

# Log command execution
echo "$(date): Starting command '$COMMAND' in $WORKDIR" >> ~/.codex/command-log.txt

# Example: Send notification for deployment commands
if [[ "$COMMAND" =~ ^(docker|kubectl|helm|npm\ run\ deploy) ]]; then
    echo "🚀 Deployment command detected: $COMMAND"
    
    # Uncomment to send Slack notification
    # curl -X POST "$SLACK_WEBHOOK_URL" \
    #   -H 'Content-Type: application/json' \
    #   -d "{\"text\":\"🚀 Deployment starting: \`$COMMAND\` in $(pwd)\"}"
fi

# Example: Check for dangerous commands
if [[ "$COMMAND" =~ (rm\ -rf|sudo|chmod\ 777) ]]; then
    echo "⚠️  Potentially dangerous command detected: $COMMAND"
    echo "$(date): DANGEROUS COMMAND: $COMMAND" >> ~/.codex/security-log.txt
fi

exit 0
