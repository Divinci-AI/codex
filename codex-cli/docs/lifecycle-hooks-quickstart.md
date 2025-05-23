# Lifecycle Hooks Quick Start Guide

Get started with Codex CLI lifecycle hooks in 5 minutes!

## What are Lifecycle Hooks?

Lifecycle hooks let you run custom scripts at different points during Codex execution:
- When tasks start/complete
- Before/after commands run
- When code patches are applied
- When the agent sends messages

## Quick Setup

### 1. Enable Hooks in Configuration

Add this to your `~/.codex/config.yaml`:

```yaml
lifecycleHooks:
  enabled: true
  hooks:
    onTaskStart:
      script: "./hooks/task-start.sh"
    onTaskComplete:
      script: "./hooks/task-complete.sh"
```

### 2. Create Your First Hook

Create a `hooks` directory in your project:

```bash
mkdir hooks
```

Create `hooks/task-start.sh`:

```bash
#!/bin/bash
echo "🚀 Codex task started!"
echo "Session: $CODEX_SESSION_ID"
echo "Model: $CODEX_MODEL"

# Read event data
EVENT_DATA=$(cat)
echo "Event data: $EVENT_DATA"

# Example: Log to file
echo "$(date): Task started" >> ~/.codex/activity.log

exit 0
```

Create `hooks/task-complete.sh`:

```bash
#!/bin/bash
echo "✅ Codex task completed!"

# Read event data
EVENT_DATA=$(cat)
SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false')

if [ "$SUCCESS" = "true" ]; then
    echo "🎉 Task was successful!"
    
    # Example: Auto-commit changes
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git add .
        git commit -m "Codex: Automated changes" || echo "No changes to commit"
    fi
else
    echo "⚠️ Task had issues"
fi

exit 0
```

### 3. Make Scripts Executable

```bash
chmod +x hooks/*.sh
```

### 4. Test Your Hooks

Run any Codex command and watch your hooks execute:

```bash
codex "create a simple hello world script"
```

You should see your hook messages in the output!

## Common Use Cases

### Git Integration

Auto-commit successful changes:

```yaml
lifecycleHooks:
  enabled: true
  hooks:
    onTaskComplete:
      script: "./hooks/git-commit.sh"
      filter:
        customExpression: "eventData.success === true"
```

### Slack Notifications

Get notified about deployments:

```yaml
lifecycleHooks:
  enabled: true
  environment:
    SLACK_WEBHOOK: "https://hooks.slack.com/your/webhook/url"
  hooks:
    onCommandComplete:
      script: "./hooks/slack-notify.sh"
      filter:
        commands: ["docker", "kubectl", "npm run deploy"]
```

### Code Quality

Run linting after code changes:

```yaml
lifecycleHooks:
  enabled: true
  hooks:
    onPatchApply:
      script: "./hooks/lint-check.sh"
      filter:
        fileExtensions: ["ts", "js", "tsx", "jsx"]
```

## Hook Script Basics

### Environment Variables Available

- `CODEX_EVENT_TYPE`: Type of event (task_start, command_complete, etc.)
- `CODEX_SESSION_ID`: Unique session identifier
- `CODEX_MODEL`: AI model being used
- `CODEX_WORKING_DIR`: Current working directory
- `CODEX_COMMAND`: Command being executed (for command hooks)
- `CODEX_EXIT_CODE`: Command exit code (for completion hooks)

### Event Data via STDIN

Your script receives detailed JSON data via STDIN:

```bash
# Read and parse event data
EVENT_DATA=$(cat)
COMMAND=$(echo "$EVENT_DATA" | jq -r '.command | join(" ")')
SUCCESS=$(echo "$EVENT_DATA" | jq -r '.success // false')
```

### Exit Codes

- `0`: Success, continue normally
- `1`: Warning, log but continue
- `2`: Error, abort operation (use sparingly)

## Advanced Features

### Filtering

Only run hooks when specific conditions are met:

```yaml
onCommandComplete:
  script: "./hooks/deployment-notify.sh"
  filter:
    commands: ["docker", "kubectl"]
    exitCodes: [0]  # Only successful commands
    durationRange:
      min: 5000  # Only long-running commands
    timeRange:
      start: "09:00"
      end: "17:00"
      daysOfWeek: [1, 2, 3, 4, 5]  # Weekdays only
```

### Custom Expressions

Use JavaScript for complex filtering:

```yaml
filter:
  customExpression: |
    exitCode === 0 && 
    command.join(' ').includes('production') &&
    workingDirectory.includes('critical')
```

### Async Execution

Run hooks without blocking Codex:

```yaml
onTaskComplete:
  script: "./hooks/slow-operation.sh"
  async: true  # Don't wait for completion
```

## Troubleshooting

### Hook Not Running?

1. Check if hooks are enabled: `lifecycleHooks.enabled: true`
2. Verify script path exists and is executable: `chmod +x script.sh`
3. Check filters aren't excluding your use case
4. Look for errors in Codex output

### Script Errors?

1. Test script independently: `./hooks/your-script.sh`
2. Check script syntax and dependencies
3. Verify JSON parsing if using event data
4. Add error handling: `set -e` for bash scripts

### Need Help?

- See full documentation: [Lifecycle Hooks Documentation](./lifecycle-hooks.md)
- Check examples: [Example Scripts](../examples/hooks/)
- Review test cases: [Test Files](../tests/)

## Next Steps

1. **Explore Examples**: Check out `codex-cli/examples/hooks/` for more scripts
2. **Read Full Docs**: See `lifecycle-hooks.md` for complete documentation
3. **Join Community**: Share your hooks and get help from other users
4. **Contribute**: Submit your useful hooks as examples for others

Happy automating! 🚀
