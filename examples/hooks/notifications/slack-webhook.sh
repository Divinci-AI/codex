#!/bin/bash
# Slack Webhook Notification Hook
# This script sends notifications to Slack when Codex events occur

# Configuration - Set your Slack webhook URL
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "Error: SLACK_WEBHOOK_URL environment variable not set"
    echo "Please set it to your Slack webhook URL"
    exit 1
fi

# Available environment variables:
# CODEX_EVENT_TYPE - The type of lifecycle event
# CODEX_SESSION_ID - Current session ID
# CODEX_TIMESTAMP - Event timestamp
# Additional variables depending on event type

# Format the message based on event type
case "$CODEX_EVENT_TYPE" in
    "session_start")
        ICON=":rocket:"
        COLOR="good"
        TITLE="Codex Session Started"
        MESSAGE="Session \`$CODEX_SESSION_ID\` started with model \`$CODEX_MODEL\`"
        ;;
    "session_end")
        ICON=":checkered_flag:"
        COLOR="good"
        TITLE="Codex Session Ended"
        DURATION_MSG=""
        if [ -n "$CODEX_DURATION" ]; then
            DURATION_SECONDS=$((CODEX_DURATION / 1000))
            DURATION_MSG=" (duration: ${DURATION_SECONDS}s)"
        fi
        MESSAGE="Session \`$CODEX_SESSION_ID\` ended$DURATION_MSG"
        ;;
    "task_start")
        ICON=":gear:"
        COLOR="#439FE0"
        TITLE="Task Started"
        MESSAGE="Task \`$CODEX_TASK_ID\` started: $CODEX_PROMPT"
        ;;
    "task_end")
        if [ "$CODEX_SUCCESS" = "true" ]; then
            ICON=":white_check_mark:"
            COLOR="good"
            TITLE="Task Completed Successfully"
        else
            ICON=":x:"
            COLOR="danger"
            TITLE="Task Failed"
        fi
        MESSAGE="Task \`$CODEX_TASK_ID\` completed"
        ;;
    "command_start")
        ICON=":computer:"
        COLOR="#36a64f"
        TITLE="Command Execution Started"
        MESSAGE="Executing command: \`${CODEX_COMMAND}\`"
        ;;
    "command_end")
        if [ "$CODEX_EXIT_CODE" = "0" ]; then
            ICON=":white_check_mark:"
            COLOR="good"
            TITLE="Command Completed Successfully"
        else
            ICON=":warning:"
            COLOR="warning"
            TITLE="Command Failed"
        fi
        MESSAGE="Command completed with exit code $CODEX_EXIT_CODE"
        ;;
    "error")
        ICON=":exclamation:"
        COLOR="danger"
        TITLE="Error Occurred"
        MESSAGE="Error: $CODEX_ERROR"
        if [ -n "$CODEX_CONTEXT" ]; then
            MESSAGE="$MESSAGE\nContext: $CODEX_CONTEXT"
        fi
        ;;
    *)
        ICON=":information_source:"
        COLOR="#36a64f"
        TITLE="Codex Event"
        MESSAGE="Event type: $CODEX_EVENT_TYPE"
        ;;
esac

# Create JSON payload
PAYLOAD=$(cat <<EOF
{
    "attachments": [
        {
            "color": "$COLOR",
            "title": "$ICON $TITLE",
            "text": "$MESSAGE",
            "footer": "Codex CLI",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

# Send to Slack
if command -v curl >/dev/null 2>&1; then
    curl -X POST -H 'Content-type: application/json' \
         --data "$PAYLOAD" \
         "$SLACK_WEBHOOK_URL" \
         --silent --show-error
    echo "Notification sent to Slack"
else
    echo "Error: curl not found. Please install curl to send Slack notifications."
    exit 1
fi
