# Lifecycle Hooks

Lifecycle hooks allow you to execute custom scripts at different stages of the Codex CLI agent task cycle. This enables powerful integrations with external systems, custom workflows, and automation.

## Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Hook Types](#hook-types)
- [Hook Script Interface](#hook-script-interface)
- [Filtering](#filtering)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Lifecycle hooks are user-defined scripts that execute at specific points during Codex agent execution:

- **Task-level hooks**: Execute when tasks start, complete, or encounter errors
- **Command-level hooks**: Execute before and after individual command execution
- **Code-level hooks**: Execute when code patches are applied
- **Agent-level hooks**: Execute when the agent sends messages or provides reasoning

Hooks receive context data via environment variables and STDIN, allowing them to make decisions and take actions based on the current state.

## Configuration

Add lifecycle hooks to your Codex configuration file (`~/.codex/config.yaml`):

```yaml
lifecycleHooks:
  enabled: true
  timeout: 30000  # Default timeout in milliseconds
  workingDirectory: "."  # Relative to project root
  
  # Global environment variables for all hooks
  environment:
    PROJECT_NAME: "${PWD##*/}"
    TEAM_WEBHOOK: "${SLACK_WEBHOOK_URL}"
  
  hooks:
    onTaskStart:
      script: "./hooks/task-start.sh"
      async: false
      
    onTaskComplete:
      script: "./hooks/task-complete.sh"
      async: true
      
    onCommandStart:
      script: "./hooks/command-start.sh"
      filter:
        commands: ["git", "npm", "docker"]
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `enabled` | boolean | Whether lifecycle hooks are enabled |
| `timeout` | number | Default timeout in milliseconds (default: 30000) |
| `workingDirectory` | string | Working directory for hook execution |
| `environment` | object | Global environment variables for all hooks |
| `hooks` | object | Individual hook configurations |

### Hook Configuration

Each hook can be configured with:

| Option | Type | Description |
|--------|------|-------------|
| `script` | string | Path to the script to execute |
| `async` | boolean | Whether to execute asynchronously (default: false) |
| `timeout` | number | Hook-specific timeout (overrides global) |
| `filter` | object | Filtering criteria for when to execute |
| `environment` | object | Hook-specific environment variables |

## Hook Types

### Task-Level Hooks

- **`onTaskStart`**: Executed when an agent task begins
- **`onTaskComplete`**: Executed when an agent task completes successfully
- **`onTaskError`**: Executed when an agent task encounters an error

### Command-Level Hooks

- **`onCommandStart`**: Executed before each command runs
- **`onCommandComplete`**: Executed after each command completes

### Code-Level Hooks

- **`onPatchApply`**: Executed when code patches are applied

### Agent-Level Hooks

- **`onAgentMessage`**: Executed when the agent sends a message
- **`onAgentReasoning`**: Executed when the agent provides reasoning
- **`onMcpToolCall`**: Executed when MCP tools are called

## Hook Script Interface

### Environment Variables

All hooks receive standard environment variables:

| Variable | Description |
|----------|-------------|
| `CODEX_EVENT_TYPE` | Type of event that triggered the hook |
| `CODEX_SESSION_ID` | Unique session identifier |
| `CODEX_MODEL` | AI model being used |
| `CODEX_WORKING_DIR` | Current working directory |
| `CODEX_TIMEOUT` | Hook execution timeout |

Command-specific variables:

| Variable | Description |
|----------|-------------|
| `CODEX_COMMAND` | Command being executed (for command hooks) |
| `CODEX_EXIT_CODE` | Command exit code (for completion hooks) |
| `CODEX_CALL_ID` | Unique call identifier |

### STDIN Data

Hooks receive detailed event data via STDIN as JSON:

```json
{
  "command": ["git", "status"],
  "workdir": "/path/to/project",
  "exitCode": 0,
  "durationMs": 1234,
  "success": true
}
```

### Exit Codes

Hook scripts should use these exit codes:

- **0**: Success, continue normally
- **1**: Warning, log but continue
- **2**: Error, abort current operation (use sparingly)

### Example Hook Script

```bash
#!/bin/bash

# Read event data from STDIN
EVENT_DATA=$(cat)

# Access environment variables
echo "Hook: $CODEX_EVENT_TYPE"
echo "Session: $CODEX_SESSION_ID"
echo "Command: $CODEX_COMMAND"

# Process event data
COMMAND=$(echo "$EVENT_DATA" | jq -r '.command | join(" ")')
EXIT_CODE=$(echo "$EVENT_DATA" | jq -r '.exitCode // 0')

# Take action based on data
if [ "$EXIT_CODE" = "0" ]; then
    echo "Command succeeded: $COMMAND"
else
    echo "Command failed: $COMMAND (exit code: $EXIT_CODE)"
fi

exit 0
```

## Filtering

Hooks can be filtered to execute only under specific conditions:

### Basic Filters

```yaml
filter:
  commands: ["git", "npm"]           # Command name patterns
  exitCodes: [0]                     # Specific exit codes
  messageTypes: ["response"]         # Agent message types
  workingDirectories: ["**/src/**"]  # Directory patterns
```

### Advanced Filters

```yaml
filter:
  fileExtensions: ["ts", "js"]       # File extensions (for patch hooks)
  durationRange:                     # Execution duration
    min: 1000
    max: 10000
  timeRange:                         # Time-based filtering
    start: "09:00"
    end: "17:00"
    daysOfWeek: [1, 2, 3, 4, 5]     # Monday-Friday
  environment:                       # Environment variable matching
    NODE_ENV: "production"
  customExpression: "exitCode === 0 && command.includes('deploy')"
```

### Custom Expressions

Custom expressions provide powerful filtering using JavaScript:

```yaml
filter:
  customExpression: |
    exitCode === 0 && 
    command.join(' ').includes('test') && 
    workingDirectory.includes('critical')
```

Available variables in expressions:
- `context`: Full hook context
- `eventData`: Event-specific data
- `command`: Command array
- `exitCode`: Command exit code
- `workingDirectory`: Current directory
- `sessionId`: Session identifier
- `model`: AI model name
- `env`: Environment variables

## Examples

### Git Integration

Auto-commit changes after successful tasks:

```bash
#!/bin/bash
# hooks/auto-commit.sh

if [ "$CODEX_EVENT_TYPE" = "task_complete" ]; then
    EVENT_DATA=$(cat)
    SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false')
    
    if [ "$SUCCESS" = "true" ] && git rev-parse --git-dir > /dev/null 2>&1; then
        git add .
        git commit -m "Codex: Automated changes from session $CODEX_SESSION_ID"
    fi
fi
```

### Slack Notifications

Send notifications for deployment commands:

```bash
#!/bin/bash
# hooks/slack-notify.sh

if [[ "$CODEX_COMMAND" =~ ^(docker|kubectl|helm) ]]; then
    EVENT_DATA=$(cat)
    SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false')
    
    if [ "$SUCCESS" = "true" ]; then
        MESSAGE="✅ Deployment successful: $CODEX_COMMAND"
    else
        MESSAGE="❌ Deployment failed: $CODEX_COMMAND"
    fi
    
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"$MESSAGE\"}"
fi
```

### Code Quality Checks

Run linting after code changes:

```python
#!/usr/bin/env python3
# hooks/quality-check.py

import json
import sys
import subprocess
import os

# Read event data
event_data = json.load(sys.stdin)

if os.environ.get('CODEX_EVENT_TYPE') == 'patch_apply':
    files = event_data.get('files', [])
    
    # Check if any TypeScript/JavaScript files were modified
    js_files = [f for f in files if f.endswith(('.ts', '.tsx', '.js', '.jsx'))]
    
    if js_files:
        print("Running ESLint on modified files...")
        result = subprocess.run(['npx', 'eslint'] + js_files, 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Linting failed:")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
        else:
            print("Linting passed!")

sys.exit(0)
```

## Best Practices

### Security

1. **Validate inputs**: Always validate data from STDIN and environment variables
2. **Use absolute paths**: Avoid relative paths in hook scripts
3. **Limit permissions**: Run hooks with minimal required permissions
4. **Sanitize commands**: Be careful when executing commands with user data

### Performance

1. **Use async hooks**: For non-critical operations, use `async: true`
2. **Set appropriate timeouts**: Prevent hanging with reasonable timeouts
3. **Filter effectively**: Use filters to avoid unnecessary hook executions
4. **Cache results**: Cache expensive operations when possible

### Reliability

1. **Handle errors gracefully**: Don't let hook failures break Codex
2. **Log appropriately**: Use structured logging for debugging
3. **Test thoroughly**: Test hooks with various scenarios
4. **Monitor execution**: Track hook performance and failures

## Troubleshooting

### Common Issues

#### Hook Not Executing

1. Check if hooks are enabled: `lifecycleHooks.enabled: true`
2. Verify script path is correct and file exists
3. Ensure script has execute permissions: `chmod +x script.sh`
4. Check filters - they might be excluding your use case

#### Hook Timing Out

1. Increase timeout in configuration
2. Optimize hook script performance
3. Use async execution for long-running operations
4. Check for infinite loops or blocking operations

#### Permission Errors

1. Verify script file permissions
2. Check working directory permissions
3. Ensure required tools are installed and accessible
4. Review environment variable access

For more examples and advanced configurations, see the `examples/hooks/` directory.
