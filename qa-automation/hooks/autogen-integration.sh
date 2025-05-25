#!/bin/bash
# Codex Lifecycle Hook - AutoGen Integration
# This hook sends lifecycle events to the AutoGen server for QA processing

set -euo pipefail

# Configuration
AUTOGEN_SERVER_URL="${AUTOGEN_SERVER_URL:-http://localhost:5000}"
WEBHOOK_ENDPOINT="/webhook/codex"
TIMEOUT="${AUTOGEN_TIMEOUT:-30}"

# Logging
LOG_FILE="${CODEX_LOG_DIR:-/tmp}/autogen_hook.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Read event data from stdin
EVENT_DATA=$(cat)

# Build webhook payload
PAYLOAD=$(jq -n \
  --arg eventType "${CODEX_EVENT_TYPE:-unknown}" \
  --arg sessionId "${CODEX_SESSION_ID:-$(uuidgen)}" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg model "${CODEX_MODEL:-unknown}" \
  --arg workingDir "${CODEX_WORKING_DIR:-$(pwd)}" \
  --argjson eventData "$EVENT_DATA" \
  '{
    eventType: $eventType,
    sessionId: $sessionId,
    timestamp: $timestamp,
    context: {
      model: $model,
      workingDirectory: $workingDir,
      eventData: $eventData
    }
  }'
)

log "Sending event to AutoGen server: ${CODEX_EVENT_TYPE:-unknown}"

# Send webhook
RESPONSE=$(curl -s \
  --max-time "$TIMEOUT" \
  --header "Content-Type: application/json" \
  --data "$PAYLOAD" \
  "${AUTOGEN_SERVER_URL}${WEBHOOK_ENDPOINT}")

log "AutoGen server response: $RESPONSE"

exit 0
