# Security Hooks

This directory contains example hooks for security monitoring and file protection during Codex sessions.

## Files

- `scan-commands.py` - Scans commands for potentially dangerous operations
- `backup-files.sh` - Creates backups of important files before sessions start

## Command Security Scanner

The command scanner analyzes commands for potentially dangerous patterns and logs security events.

### Setup

1. Make the script executable:
   ```bash
   chmod +x examples/hooks/security/scan-commands.py
   ```

2. Configure your `hooks.toml`:
   ```toml
   [[hooks.task]]
   event = "command_start"
   type = "script"
   command = ["python3", "./examples/hooks/security/scan-commands.py"]
   ```

### Features

- **Dangerous Pattern Detection**: Identifies potentially harmful commands
- **Warning System**: Flags risky but not necessarily dangerous commands
- **Security Logging**: Logs all scan results to `~/.codex/security.log`
- **Risk Assessment**: Categorizes commands as low, medium, or high risk

### Dangerous Patterns Detected

- File system operations: `rm /`, `rm *`, `chmod 777`
- Network operations: `curl | sh`, `wget | sh`
- System operations: `sudo rm`, `mkfs.`, `dd of=/dev/`
- Process operations: `kill -9 1`, `killall -9`

### Warning Patterns

- Any `sudo` usage
- World-readable permissions
- Forced operations (`--force` flags)
- Find with exec

### Blocking Commands

To prevent execution of dangerous commands, uncomment this line in the script:
```python
# sys.exit(1)  # Uncomment to block dangerous commands
```

## File Backup Hook

The backup hook creates snapshots of important files before Codex sessions begin.

### Setup

1. Make the script executable:
   ```bash
   chmod +x examples/hooks/security/backup-files.sh
   ```

2. Configure your `hooks.toml`:
   ```toml
   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["./examples/hooks/security/backup-files.sh"]
   ```

### Features

- **Automatic Backups**: Creates backups on session start
- **Pattern-Based**: Backs up files matching configurable patterns
- **Directory Structure**: Preserves original directory structure
- **Cleanup**: Automatically removes old backups (keeps last 10)
- **Manifest**: Creates a manifest file listing all backed up files

### File Patterns

The backup script includes patterns for common development files:

- Source code: `*.py`, `*.js`, `*.ts`, `*.go`, `*.rs`, etc.
- Configuration: `*.json`, `*.yml`, `*.toml`, `*.ini`
- Build files: `Dockerfile`, `package.json`, `requirements.txt`
- Documentation: `*.md`

### Backup Location

Backups are stored in `~/.codex/backups/` with the following structure:
```
~/.codex/backups/
├── session_abc123_20250101_120000/
│   ├── MANIFEST.txt
│   ├── src/
│   │   └── main.py
│   └── package.json
└── session_def456_20250101_130000/
    └── ...
```

### Customization

You can customize the backup patterns by editing the `BACKUP_PATTERNS` array in the script:

```bash
BACKUP_PATTERNS=(
    "*.py"
    "*.js"
    # Add your custom patterns here
)
```

## Security Best Practices

1. **Review Logs Regularly**: Check `~/.codex/security.log` for security events
2. **Monitor Backups**: Ensure backups are being created successfully
3. **Customize Patterns**: Adjust detection patterns for your specific environment
4. **Test Hooks**: Verify hooks work correctly before relying on them
5. **Secure Storage**: Ensure backup directories have appropriate permissions

## Log Formats

### Security Log (`~/.codex/security.log`)
```json
{
  "timestamp": "2025-01-01T12:00:00",
  "session_id": "abc123",
  "command": "rm -rf /tmp/test",
  "issues": [...],
  "warnings": [...],
  "risk_level": "high"
}
```

### Backup Log (`~/.codex/backup.log`)
```
[2025-01-01T12:00:00] SESSION_BACKUP: Session abc123 - 25 files backed up
```

## Integration with Other Tools

These security hooks can be integrated with:

- **SIEM Systems**: Forward logs to security monitoring systems
- **Alerting**: Combine with notification hooks for real-time alerts
- **CI/CD**: Use in automated testing environments
- **Compliance**: Support audit and compliance requirements
