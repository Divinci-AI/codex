#!/bin/bash
# Basic Hook Script Template
# This script receives Codex lifecycle events via environment variables

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================
# The following environment variables are available in all hooks:
#
# CODEX_EVENT_TYPE    - The type of lifecycle event (e.g., "session_start")
# CODEX_SESSION_ID    - Current session ID (unique identifier)
# CODEX_TIMESTAMP     - Event timestamp in ISO format
#
# Event-specific variables:
#
# Session Start:
#   CODEX_MODEL       - The model being used (e.g., "gpt-4")
#   CODEX_PROVIDER    - The provider (e.g., "openai", "azure")
#
# Session End:
#   CODEX_DURATION    - Session duration in milliseconds
#
# Task Start:
#   CODEX_TASK_ID     - Unique task identifier
#   CODEX_PROMPT      - User prompt/request
#
# Task End:
#   CODEX_TASK_ID     - Unique task identifier
#   CODEX_SUCCESS     - "true" or "false"
#   CODEX_DURATION    - Task duration in milliseconds
#
# Command Start:
#   CODEX_COMMAND     - Command array as JSON (e.g., '["ls", "-la"]')
#   CODEX_WORKDIR     - Working directory
#
# Command End:
#   CODEX_COMMAND     - Command array as JSON
#   CODEX_EXIT_CODE   - Command exit code
#   CODEX_DURATION    - Execution duration in milliseconds
#
# Error:
#   CODEX_ERROR       - Error message
#   CODEX_CONTEXT     - Error context (optional)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Set default values for optional variables
EVENT_TYPE="${CODEX_EVENT_TYPE:-unknown}"
SESSION_ID="${CODEX_SESSION_ID:-unknown}"
TIMESTAMP="${CODEX_TIMESTAMP:-$(date -Iseconds)}"

# Log file location (customize as needed)
LOG_FILE="${HOME}/.codex/hooks.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Log a message with timestamp
log_message() {
    local level="$1"
    local message="$2"
    echo "[$TIMESTAMP] [$level] $message" | tee -a "$LOG_FILE"
}

# Log info message
log_info() {
    log_message "INFO" "$1"
}

# Log warning message
log_warning() {
    log_message "WARN" "$1"
}

# Log error message
log_error() {
    log_message "ERROR" "$1"
}

# Parse JSON command array (if available)
parse_command() {
    if [ -n "$CODEX_COMMAND" ]; then
        # Try to parse as JSON array, fallback to string
        if command -v jq >/dev/null 2>&1; then
            echo "$CODEX_COMMAND" | jq -r 'join(" ")' 2>/dev/null || echo "$CODEX_COMMAND"
        else
            echo "$CODEX_COMMAND"
        fi
    else
        echo "N/A"
    fi
}

# Send desktop notification (if available)
send_notification() {
    local title="$1"
    local message="$2"
    
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "$title" "$message"
    elif command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$message\" with title \"$title\""
    fi
}

# =============================================================================
# EVENT HANDLERS
# =============================================================================

handle_session_start() {
    local model="${CODEX_MODEL:-unknown}"
    local provider="${CODEX_PROVIDER:-openai}"
    
    log_info "Session started: $SESSION_ID with model $model (provider: $provider)"
    send_notification "Codex Session Started" "Session $SESSION_ID with model $model"
    
    # Add your custom logic here
    # Examples:
    # - Initialize session-specific resources
    # - Send notifications to external systems
    # - Create session directories
    # - Start monitoring processes
}

handle_session_end() {
    local duration="${CODEX_DURATION:-0}"
    local duration_seconds=$((duration / 1000))
    
    log_info "Session ended: $SESSION_ID (duration: ${duration_seconds}s)"
    send_notification "Codex Session Ended" "Session $SESSION_ID ended (${duration_seconds}s)"
    
    # Add your custom logic here
    # Examples:
    # - Clean up session resources
    # - Generate session reports
    # - Archive session data
    # - Stop monitoring processes
}

handle_task_start() {
    local task_id="${CODEX_TASK_ID:-unknown}"
    local prompt="${CODEX_PROMPT:-N/A}"
    
    log_info "Task started: $task_id - $prompt"
    
    # Add your custom logic here
    # Examples:
    # - Log task details
    # - Start task-specific monitoring
    # - Validate task parameters
    # - Initialize task resources
}

handle_task_end() {
    local task_id="${CODEX_TASK_ID:-unknown}"
    local success="${CODEX_SUCCESS:-false}"
    local duration="${CODEX_DURATION:-0}"
    local duration_seconds=$((duration / 1000))
    
    log_info "Task completed: $task_id (success: $success, duration: ${duration_seconds}s)"
    
    # Add your custom logic here
    # Examples:
    # - Log task results
    # - Clean up task resources
    # - Generate task reports
    # - Update task databases
}

handle_command_start() {
    local command=$(parse_command)
    local workdir="${CODEX_WORKDIR:-$(pwd)}"
    
    log_info "Command starting: $command (workdir: $workdir)"
    
    # Add your custom logic here
    # Examples:
    # - Validate command safety
    # - Log command execution
    # - Start command monitoring
    # - Check permissions
}

handle_command_end() {
    local command=$(parse_command)
    local exit_code="${CODEX_EXIT_CODE:-0}"
    local duration="${CODEX_DURATION:-0}"
    local duration_ms="${duration}ms"
    
    if [ "$exit_code" -eq 0 ]; then
        log_info "Command completed successfully: $command (duration: $duration_ms)"
    else
        log_warning "Command failed: $command (exit code: $exit_code, duration: $duration_ms)"
    fi
    
    # Add your custom logic here
    # Examples:
    # - Log command results
    # - Handle command failures
    # - Update command statistics
    # - Clean up command resources
}

handle_error() {
    local error="${CODEX_ERROR:-Unknown error}"
    local context="${CODEX_CONTEXT:-N/A}"
    
    log_error "Error occurred: $error (context: $context)"
    send_notification "Codex Error" "$error"
    
    # Add your custom logic here
    # Examples:
    # - Send error alerts
    # - Log detailed error information
    # - Trigger error recovery procedures
    # - Update error statistics
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log_info "Hook script started for event: $EVENT_TYPE"
    
    # Route to appropriate handler based on event type
    case "$EVENT_TYPE" in
        "session_start")
            handle_session_start
            ;;
        "session_end")
            handle_session_end
            ;;
        "task_start")
            handle_task_start
            ;;
        "task_end")
            handle_task_end
            ;;
        "command_start")
            handle_command_start
            ;;
        "command_end")
            handle_command_end
            ;;
        "error")
            handle_error
            ;;
        *)
            log_warning "Unknown event type: $EVENT_TYPE"
            ;;
    esac
    
    log_info "Hook script completed for event: $EVENT_TYPE"
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

# Exit on any error (uncomment if you want strict error handling)
# set -e

# Trap errors and log them
trap 'log_error "Script failed at line $LINENO"' ERR

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Run main function
main "$@"

# Exit successfully
exit 0
