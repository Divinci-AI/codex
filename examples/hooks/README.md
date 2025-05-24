# Codex Lifecycle Hooks Examples

This directory contains comprehensive examples of Codex lifecycle hooks that demonstrate various use cases and integration patterns.

## Quick Start

1. **Copy the example configuration**:
   ```bash
   cp examples/hooks.toml ./hooks.toml
   ```

2. **Enable hooks in your Codex configuration** (`~/.codex/config.json`):
   ```json
   {
     "hooks": {
       "enabled": true,
       "configPath": "./hooks.toml"
     }
   }
   ```

3. **Test with a simple hook**:
   ```bash
   # Edit hooks.toml to enable only session logging
   codex "Hello, world!"
   # Check ~/.codex/session.log for logged events
   ```

## Directory Structure

```
examples/hooks/
├── README.md                    # This file
├── templates/                   # Hook script templates
│   └── basic-script.sh         # Basic hook script template
├── session-logging/            # Session activity logging
│   ├── log-session-start.sh
│   ├── log-session-end.sh
│   └── README.md
├── notifications/              # External notifications
│   ├── slack-webhook.sh
│   ├── email-notification.py
│   └── README.md
├── security/                   # Security monitoring
│   ├── scan-commands.py
│   ├── backup-files.sh
│   └── README.md
├── analytics/                  # Usage analytics
│   ├── track-usage.js
│   ├── performance-metrics.py
│   └── README.md
└── hooks.toml                  # Example configuration file
```

## Hook Categories

### 📝 Session Logging
Basic logging of session activity to local files.
- **Use case**: Audit trails, debugging, session history
- **Files**: `session-logging/`
- **Requirements**: Bash shell

### 🔔 Notifications
Send notifications to external services when events occur.
- **Use case**: Team collaboration, monitoring, alerts
- **Files**: `notifications/`
- **Requirements**: 
  - Slack: Webhook URL
  - Email: SMTP configuration

### 🔒 Security
Monitor and protect against potentially dangerous operations.
- **Use case**: Security compliance, risk management, auditing
- **Files**: `security/`
- **Requirements**: Python 3

### 📊 Analytics
Track usage patterns and performance metrics.
- **Use case**: Usage optimization, performance monitoring, reporting
- **Files**: `analytics/`
- **Requirements**: 
  - Node.js (for usage tracking)
  - Python 3 + psutil (for performance metrics)

## Configuration Examples

### Minimal Configuration
```toml
[hooks]
enabled = true

[[hooks.task]]
event = "session_start"
type = "script"
command = ["./examples/hooks/session-logging/log-session-start.sh"]
```

### Production Configuration
```toml
[hooks]
enabled = true
timeout_seconds = 30
debug = false

# Session logging
[[hooks.task]]
event = "session_start"
type = "script"
command = ["./examples/hooks/session-logging/log-session-start.sh"]
priority = 1

# File backup
[[hooks.task]]
event = "session_start"
type = "script"
command = ["./examples/hooks/security/backup-files.sh"]
priority = 2

# Security scanning
[[hooks.task]]
event = "command_start"
type = "script"
command = ["python3", "./examples/hooks/security/scan-commands.py"]

# Slack notifications for errors
[[hooks.task]]
event = "error"
type = "script"
command = ["./examples/hooks/notifications/slack-webhook.sh"]
environment = { SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" }
```

## Getting Started Guide

### Step 1: Choose Your Hooks
Start with basic session logging, then add more hooks as needed:

1. **Session Logging** (recommended first step)
2. **Security Scanning** (for safety)
3. **Analytics** (for insights)
4. **Notifications** (for team collaboration)

### Step 2: Install Dependencies
```bash
# For Python hooks
pip install psutil

# For Node.js hooks (if not already installed)
# Install Node.js from https://nodejs.org/

# For notifications
# Configure Slack webhook or SMTP settings
```

### Step 3: Customize Configuration
Edit `hooks.toml` to:
- Enable/disable specific hooks
- Configure notification endpoints
- Set custom timeouts
- Add conditional execution

### Step 4: Test Your Setup
```bash
# Test with a simple command
codex "echo 'Testing hooks'"

# Check log files
cat ~/.codex/session.log
cat ~/.codex/hooks.log

# Generate analytics report
node examples/hooks/analytics/track-usage.js --report
```

## Best Practices

### 🚀 Performance
- Keep hooks lightweight and fast
- Use appropriate timeouts
- Avoid blocking operations
- Monitor hook execution times

### 🔒 Security
- Validate all inputs in hook scripts
- Use environment variables for secrets
- Set proper file permissions
- Regularly review hook configurations

### 🛠️ Maintenance
- Version control your hook configurations
- Document custom hooks
- Test hooks in development environments
- Monitor hook success/failure rates

### 📋 Monitoring
- Check log files regularly
- Set up alerts for hook failures
- Monitor system resource usage
- Track hook execution metrics

## Troubleshooting

### Common Issues

**Hooks not executing:**
```bash
# Check configuration
cat hooks.toml

# Verify file permissions
ls -la examples/hooks/session-logging/

# Enable debug mode
# Add "debug = true" to [hooks] section in hooks.toml
```

**Permission errors:**
```bash
# Make scripts executable
chmod +x examples/hooks/**/*.sh
chmod +x examples/hooks/**/*.py
chmod +x examples/hooks/**/*.js
```

**Missing dependencies:**
```bash
# Install Python dependencies
pip install psutil

# Check Node.js installation
node --version
```

### Debug Mode
Enable debug logging in `hooks.toml`:
```toml
[hooks]
enabled = true
debug = true
```

### Log Files
Check these locations for hook activity:
- `~/.codex/session.log` - Session logging
- `~/.codex/hooks.log` - General hook logs
- `~/.codex/security.log` - Security scan results
- `~/.codex/analytics/` - Analytics data

## Advanced Usage

### Custom Hook Development
Use the template in `templates/basic-script.sh` as a starting point for custom hooks.

### Integration with CI/CD
Hooks can be integrated with continuous integration systems:
```toml
[[hooks.task]]
event = "session_end"
type = "webhook"
url = "https://ci.example.com/codex-session-complete"
method = "POST"
```

### Multi-Environment Configuration
Use different hook configurations for different environments:
```bash
# Development
cp hooks.dev.toml hooks.toml

# Production
cp hooks.prod.toml hooks.toml
```

## Contributing

To contribute new hook examples:

1. Create a new directory under `examples/hooks/`
2. Include a README.md with setup instructions
3. Add example configuration to `hooks.toml`
4. Test thoroughly in different environments
5. Document any dependencies or requirements

## Support

For help with hooks:
- Read the main documentation: `docs/hooks.md`
- Check example configurations in this directory
- Review log files for error messages
- Test with minimal configurations first
