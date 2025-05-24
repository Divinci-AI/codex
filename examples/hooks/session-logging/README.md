# Session Logging Hooks

This directory contains example hooks for logging Codex session activity.

## Files

- `log-session-start.sh` - Logs when a Codex session starts
- `log-session-end.sh` - Logs when a Codex session ends

## Usage

1. Make the scripts executable:
   ```bash
   chmod +x examples/hooks/session-logging/*.sh
   ```

2. Configure your `hooks.toml` file:
   ```toml
   [hooks]
   enabled = true

   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["./examples/hooks/session-logging/log-session-start.sh"]

   [[hooks.task]]
   event = "session_end"
   type = "script"
   command = ["./examples/hooks/session-logging/log-session-end.sh"]
   ```

## Features

- Logs session activity to `~/.codex/session.log`
- Sends desktop notifications (if available)
- Includes session ID, model, and duration information
- Cross-platform compatible (Linux, macOS)

## Log Format

The log file uses the following format:
```
[2025-01-XX] SESSION_START: Session abc123 started with model gpt-4 (provider: openai)
[2025-01-XX] SESSION_END: Session abc123 ended (duration: 120s)
```

## Environment Variables

The hooks receive the following environment variables:

### Session Start
- `CODEX_EVENT_TYPE` - Always "session_start"
- `CODEX_SESSION_ID` - Unique session identifier
- `CODEX_TIMESTAMP` - ISO timestamp of the event
- `CODEX_MODEL` - The model being used (e.g., "gpt-4")
- `CODEX_PROVIDER` - The provider (e.g., "openai", "azure")

### Session End
- `CODEX_EVENT_TYPE` - Always "session_end"
- `CODEX_SESSION_ID` - Unique session identifier
- `CODEX_TIMESTAMP` - ISO timestamp of the event
- `CODEX_DURATION` - Session duration in milliseconds (optional)
