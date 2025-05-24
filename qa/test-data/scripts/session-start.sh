#!/bin/bash
# Test script for session start hook
# This script is executed when a session starts

echo "Session start hook executed at $(date)"
echo "Event data: $CODEX_EVENT_DATA"
echo "Session ID: $CODEX_SESSION_ID"

# Log to file
echo "$(date): Session start hook executed" >> /workspace/qa/logs/hook-execution.log

# Exit successfully
exit 0
