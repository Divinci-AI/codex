# Codex Lifecycle Hooks

Codex supports lifecycle hooks that allow you to execute custom scripts, webhooks, or tools at specific points during Codex operations. This enables powerful automation, monitoring, and integration capabilities.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [Hook Types](#hook-types)
- [Hook Events](#hook-events)
- [Examples](#examples)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Advanced Usage](#advanced-usage)

## Overview

Lifecycle hooks provide a way to extend Codex functionality by executing custom code at key points in the Codex workflow. Hooks can be used for:

- **Logging and Auditing**: Track session activity and command execution
- **Security Monitoring**: Scan commands for potential security issues
- **External Integrations**: Send notifications to Slack, email, or other services
- **Automation**: Backup files, run tests, or trigger CI/CD pipelines
- **Analytics**: Collect usage metrics and performance data

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Codex CLI     │───▶│   Hook Manager   │───▶│   Hook Scripts  │
│                 │    │   (Rust Core)    │    │   Webhooks      │
│ - Session Start │    │                  │    │   MCP Tools     │
│ - Task Start    │    │ - Event Routing  │    │                 │
│ - Command Exec  │    │ - Execution      │    │ - Log Files     │
│ - Errors        │    │ - Error Handling │    │ - Notifications │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Enable Hooks

Add hooks configuration to your Codex config (`~/.codex/config.json`):

```json
{
  "hooks": {
    "enabled": true,
    "configPath": "./hooks.toml"
  }
}
```

Or use CLI flags:
```bash
codex --enable-hooks --hooks-config ./hooks.toml "Hello, world!"
```

### 2. Create Configuration

Copy the example configuration:
```bash
cp examples/hooks.toml ./hooks.toml
```

### 3. Test Your Setup

Run a simple command to test hooks:
```bash
codex "echo 'Testing hooks'"
```

Check the log files:
```bash
cat ~/.codex/session.log
cat ~/.codex/hooks.log
```

## Configuration Reference

Hooks are configured using a TOML file. Here's the complete configuration reference:

### Global Configuration

```toml
[hooks]
# Enable or disable the entire hook system
enabled = true

# Default timeout for hook execution (in seconds)
timeout_seconds = 30

# Enable parallel execution of hooks (default: true)
parallel_execution = true

# Enable debug logging for hook execution
debug = false
```

### Hook Definition

Each hook is defined as a table array under the appropriate event category:

```toml
[[hooks.session]]
event = "session_start"           # Event to trigger on
type = "script"                   # Hook type: script, webhook, mcp_tool
command = ["./my-hook.sh"]        # Command to execute
description = "My custom hook"    # Human-readable description
enabled = true                    # Enable/disable this hook
required = false                  # If true, failure stops execution
timeout = 10                      # Hook-specific timeout (seconds)
mode = "async"                    # Execution mode: async, sync
priority = "normal"               # Priority: low, normal, high

# Optional: Environment variables
[hooks.session.environment]
MY_VAR = "value"
API_KEY = "${API_KEY}"           # Use environment variable

# Optional: Conditions for execution
[hooks.session.conditions]
user_type = "admin"              # Only run for admin users
environment = "production"       # Only run in production
```

### Event Categories

Hooks are organized by event categories:

- `hooks.session` - Session lifecycle events
- `hooks.task` - Task lifecycle events  
- `hooks.exec` - Command execution events
- `hooks.patch` - Patch application events
- `hooks.mcp` - MCP tool events
- `hooks.agent` - Agent lifecycle events
- `hooks.error` - Error handling events
- `hooks.integration` - Integration events

## Hook Types

### Script Hooks

Execute shell scripts or commands:

```toml
[[hooks.session]]
event = "session_start"
type = "script"
command = ["./scripts/log-session.sh"]
timeout = 10

# Optional: Custom working directory
cwd = "/path/to/working/dir"

# Optional: Environment variables
[hooks.session.environment]
LOG_LEVEL = "info"
SESSION_TYPE = "interactive"
```

**Environment Variables Available:**
- `CODEX_EVENT_TYPE` - Event type (e.g., "session_start")
- `CODEX_SESSION_ID` - Current session ID
- `CODEX_TIMESTAMP` - Event timestamp (ISO format)
- Event-specific variables (see [Hook Events](#hook-events))

### Webhook Hooks

Send HTTP requests to external services:

```toml
[[hooks.task]]
event = "task_complete"
type = "webhook"
url = "https://api.example.com/codex/webhook"
method = "POST"
timeout = 15
retry_count = 3

# HTTP headers
[hooks.task.headers]
"Authorization" = "Bearer ${API_TOKEN}"
"Content-Type" = "application/json"
"X-Codex-Event" = "task_complete"
```

**Payload Format:**
```json
{
  "event": {
    "type": "task_complete",
    "sessionId": "session_123",
    "timestamp": "2024-01-01T12:00:00Z",
    "taskId": "task_456",
    "success": true,
    "duration": 5000
  },
  "context": {
    "model": "gpt-4",
    "provider": "openai"
  }
}
```

### MCP Tool Hooks

Call Model Context Protocol (MCP) tools:

```toml
[[hooks.exec]]
event = "exec.before"
type = "mcp_tool"
server = "security_scanner"
tool = "scan_command"
timeout = 20

# Tool arguments
[hooks.exec.arguments]
command = "${command}"
severity = "high"
```

## Hook Events

### Session Events

| Event | Description | Available Variables |
|-------|-------------|-------------------|
| `session_start` | Session begins | `CODEX_MODEL`, `CODEX_PROVIDER` |
| `session_end` | Session ends | `CODEX_DURATION` |

### Task Events

| Event | Description | Available Variables |
|-------|-------------|-------------------|
| `task_start` | Task begins | `CODEX_TASK_ID`, `CODEX_PROMPT` |
| `task_complete` | Task completes | `CODEX_TASK_ID`, `CODEX_SUCCESS`, `CODEX_DURATION` |

### Command Events

| Event | Description | Available Variables |
|-------|-------------|-------------------|
| `exec.before` | Before command execution | `CODEX_COMMAND`, `CODEX_WORKDIR` |
| `exec.after` | After command execution | `CODEX_COMMAND`, `CODEX_EXIT_CODE`, `CODEX_DURATION` |

### Patch Events

| Event | Description | Available Variables |
|-------|-------------|-------------------|
| `patch.before` | Before applying patch | `CODEX_PATCH_FILE`, `CODEX_TARGET_FILE` |
| `patch.after` | After applying patch | `CODEX_PATCH_FILE`, `CODEX_SUCCESS` |

### Error Events

| Event | Description | Available Variables |
|-------|-------------|-------------------|
| `error.occurred` | When an error occurs | `CODEX_ERROR`, `CODEX_CONTEXT` |

## Examples

### Basic Session Logging

```toml
[hooks]
enabled = true

[[hooks.session]]
event = "session_start"
type = "script"
command = ["./examples/hooks/session-logging/log-session-start.sh"]
description = "Log session start"

[[hooks.session]]
event = "session_end"
type = "script"
command = ["./examples/hooks/session-logging/log-session-end.sh"]
description = "Log session end"
```

### Security Monitoring

```toml
[[hooks.exec]]
event = "exec.before"
type = "script"
command = ["python3", "./examples/hooks/security/scan-commands.py"]
description = "Scan commands for security issues"
required = false  # Don't block execution on failure
```

### Slack Notifications

```toml
[[hooks.error]]
event = "error.occurred"
type = "script"
command = ["./examples/hooks/notifications/slack-webhook.sh"]
description = "Send error notifications to Slack"

[hooks.error.environment]
SLACK_WEBHOOK_URL = "${SLACK_WEBHOOK_URL}"
```

### Webhook Integration

```toml
[[hooks.task]]
event = "task_complete"
type = "webhook"
url = "https://api.example.com/codex/task-complete"
method = "POST"
description = "Report task completion to external API"

[hooks.task.headers]
"Authorization" = "Bearer ${API_TOKEN}"
"Content-Type" = "application/json"
```

### Performance Analytics

```toml
[[hooks.session]]
event = "session_end"
type = "script"
command = ["node", "./examples/hooks/analytics/track-usage.js"]
description = "Track session usage analytics"

[[hooks.exec]]
event = "exec.after"
type = "script"
command = ["python3", "./examples/hooks/analytics/performance-metrics.py"]
description = "Collect command performance metrics"
```

## Security Considerations

### Input Validation

Always validate inputs in your hook scripts:

```bash
#!/bin/bash
# Validate required environment variables
if [ -z "$CODEX_SESSION_ID" ]; then
    echo "Error: CODEX_SESSION_ID not set" >&2
    exit 1
fi

# Sanitize inputs
SESSION_ID=$(echo "$CODEX_SESSION_ID" | tr -cd '[:alnum:]-_')
```

### Environment Variables

Use environment variables for sensitive data:

```toml
[hooks.task.environment]
API_KEY = "${API_KEY}"           # Read from environment
DATABASE_URL = "${DATABASE_URL}" # Don't hardcode secrets
```

### File Permissions

Set appropriate permissions on hook scripts:

```bash
# Make scripts executable by owner only
chmod 700 examples/hooks/**/*.sh

# Protect configuration files
chmod 600 hooks.toml
```

### Sandboxing

Consider running hooks in restricted environments:

```bash
# Example: Run hook with limited permissions
sudo -u nobody timeout 30s ./my-hook.sh
```

### Network Security

For webhook hooks, use HTTPS and validate certificates:

```toml
[[hooks.task]]
type = "webhook"
url = "https://secure-api.example.com/webhook"  # Always use HTTPS
```

## Troubleshooting

### Common Issues

#### Hooks Not Executing

1. **Check if hooks are enabled:**
   ```bash
   # Verify configuration
   grep -A 5 '"hooks"' ~/.codex/config.json
   ```

2. **Verify hook configuration:**
   ```bash
   # Check TOML syntax
   cat hooks.toml
   ```

3. **Check file permissions:**
   ```bash
   # Make scripts executable
   chmod +x examples/hooks/**/*.sh
   ```

#### Permission Errors

```bash
# Fix common permission issues
chmod +x examples/hooks/**/*.sh
chmod +x examples/hooks/**/*.py
chmod +x examples/hooks/**/*.js

# Check directory permissions
ls -la examples/hooks/
```

#### Missing Dependencies

```bash
# Install Python dependencies
pip install psutil

# Check Node.js installation
node --version

# Install jq for JSON parsing
sudo apt-get install jq  # Ubuntu/Debian
brew install jq          # macOS
```

### Debug Mode

Enable debug logging in your configuration:

```toml
[hooks]
enabled = true
debug = true
```

Or use CLI flag:
```bash
codex --enable-hooks --hooks-config ./hooks.toml "test command"
```

### Log Files

Check these locations for hook activity:

- `~/.codex/session.log` - Session logging
- `~/.codex/hooks.log` - General hook logs
- `~/.codex/security.log` - Security scan results
- `~/.codex/analytics/` - Analytics data

### Testing Hooks

Test individual hooks manually:

```bash
# Set environment variables
export CODEX_EVENT_TYPE="session_start"
export CODEX_SESSION_ID="test_session"
export CODEX_TIMESTAMP="$(date -Iseconds)"

# Run hook script
./examples/hooks/session-logging/log-session-start.sh
```

## API Reference

### Environment Variables

All hooks receive these standard environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `CODEX_EVENT_TYPE` | Type of lifecycle event | `"session_start"` |
| `CODEX_SESSION_ID` | Current session identifier | `"session_abc123"` |
| `CODEX_TIMESTAMP` | Event timestamp (ISO 8601) | `"2024-01-01T12:00:00Z"` |

### Event-Specific Variables

#### Session Events
- `CODEX_MODEL` - Model name (e.g., `"gpt-4"`)
- `CODEX_PROVIDER` - Provider name (e.g., `"openai"`)
- `CODEX_DURATION` - Session duration in milliseconds

#### Task Events
- `CODEX_TASK_ID` - Unique task identifier
- `CODEX_PROMPT` - User prompt/request
- `CODEX_SUCCESS` - Task success (`"true"` or `"false"`)
- `CODEX_DURATION` - Task duration in milliseconds

#### Command Events
- `CODEX_COMMAND` - Command as JSON array (e.g., `'["ls", "-la"]'`)
- `CODEX_WORKDIR` - Working directory
- `CODEX_EXIT_CODE` - Command exit code
- `CODEX_DURATION` - Execution duration in milliseconds

#### Error Events
- `CODEX_ERROR` - Error message
- `CODEX_CONTEXT` - Error context (optional)

### Hook Script Template

Use this template for creating custom hooks:

```bash
#!/bin/bash
# Custom Hook Template

# Configuration
LOG_FILE="${HOME}/.codex/hooks.log"
TIMESTAMP="${CODEX_TIMESTAMP:-$(date -Iseconds)}"

# Utility functions
log_info() {
    echo "[$TIMESTAMP] [INFO] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$TIMESTAMP] [ERROR] $1" | tee -a "$LOG_FILE"
}

# Main logic
main() {
    log_info "Hook executed for event: $CODEX_EVENT_TYPE"
    
    # Add your custom logic here
    case "$CODEX_EVENT_TYPE" in
        "session_start")
            # Handle session start
            ;;
        "task_complete")
            # Handle task completion
            ;;
        *)
            log_error "Unknown event type: $CODEX_EVENT_TYPE"
            ;;
    esac
}

# Execute
main "$@"
```

## Advanced Usage

### Hook Priorities

Control execution order with priorities:

```toml
[[hooks.session]]
event = "session_start"
priority = "high"      # Executes first
command = ["./critical-setup.sh"]

[[hooks.session]]
event = "session_start"
priority = "normal"    # Executes second
command = ["./normal-setup.sh"]

[[hooks.session]]
event = "session_start"
priority = "low"       # Executes last
command = ["./cleanup.sh"]
```

### Conditional Execution

Use conditions to control when hooks run:

```toml
[[hooks.exec]]
event = "exec.before"
command = ["./security-scan.sh"]

# Only run in production environment
[hooks.exec.conditions]
environment = "production"
user_type = "admin"
```

### Error Handling

Configure how hook failures are handled:

```toml
[[hooks.task]]
event = "task_start"
command = ["./critical-hook.sh"]
required = true        # Failure stops execution

[[hooks.task]]
event = "task_start"
command = ["./optional-hook.sh"]
required = false       # Failure is logged but doesn't stop execution
```

### Timeout Management

Set appropriate timeouts for different hook types:

```toml
[hooks]
timeout_seconds = 30   # Global default

[[hooks.exec]]
event = "exec.before"
command = ["./quick-check.sh"]
timeout = 5            # Override for fast operations

[[hooks.session]]
event = "session_start"
command = ["./slow-setup.sh"]
timeout = 120          # Override for slow operations
```

### Multi-Environment Configuration

Use different configurations for different environments:

```bash
# Development
cp hooks.dev.toml hooks.toml

# Staging
cp hooks.staging.toml hooks.toml

# Production
cp hooks.prod.toml hooks.toml
```

### Integration with CI/CD

Integrate hooks with continuous integration:

```toml
[[hooks.session]]
event = "session_end"
type = "webhook"
url = "https://ci.example.com/codex-session-complete"
method = "POST"

[hooks.session.headers]
"Authorization" = "Bearer ${CI_API_TOKEN}"
"X-Environment" = "${ENVIRONMENT}"
```

### Custom Hook Development

1. **Start with the template** in `examples/hooks/templates/basic-script.sh`
2. **Add your custom logic** in the appropriate event handlers
3. **Test thoroughly** in development environments
4. **Document dependencies** and setup requirements
5. **Add to version control** with your hook configurations

### Performance Optimization

- **Keep hooks lightweight** - avoid long-running operations
- **Use appropriate timeouts** - prevent hanging hooks
- **Enable parallel execution** for independent hooks
- **Monitor execution times** and optimize slow hooks

### Monitoring and Alerting

Set up monitoring for hook health:

```toml
[[hooks.error]]
event = "error.occurred"
type = "webhook"
url = "https://monitoring.example.com/alert"
description = "Send alerts for hook failures"
```

## Best Practices

1. **Start Simple**: Begin with basic logging hooks, then add complexity
2. **Test Thoroughly**: Test hooks in development before production
3. **Monitor Performance**: Track hook execution times and success rates
4. **Handle Errors Gracefully**: Use appropriate error handling and timeouts
5. **Document Everything**: Document custom hooks and their requirements
6. **Version Control**: Keep hook configurations in version control
7. **Security First**: Validate inputs and use secure communication
8. **Regular Maintenance**: Review and update hooks regularly

## Support and Resources

- **Examples**: [examples/hooks/README.md](../examples/hooks/README.md)
- **Templates**: [examples/hooks/templates/](../examples/hooks/templates/)
- **Configuration**: [examples/hooks.toml](../examples/hooks.toml)
- **Testing**: [codex-cli/HOOKS_E2E_TESTING.md](../codex-cli/HOOKS_E2E_TESTING.md)
- **Backend Testing**: [codex-rs/core/src/hooks/TEST_README.md](../codex-rs/core/src/hooks/TEST_README.md)

For additional help:
1. Check the troubleshooting section above
2. Review example configurations and scripts
3. Enable debug mode for detailed logging
4. Test with minimal configurations first
