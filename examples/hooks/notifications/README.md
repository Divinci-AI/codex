# Notification Hooks

This directory contains example hooks for sending notifications when Codex events occur.

## Files

- `slack-webhook.sh` - Sends notifications to Slack via webhook
- `email-notification.py` - Sends email notifications via SMTP

## Slack Webhook Setup

1. Create a Slack webhook URL in your Slack workspace:
   - Go to https://api.slack.com/apps
   - Create a new app or use an existing one
   - Add "Incoming Webhooks" feature
   - Create a webhook for your desired channel

2. Set the webhook URL:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

3. Make the script executable:
   ```bash
   chmod +x examples/hooks/notifications/slack-webhook.sh
   ```

4. Configure your `hooks.toml`:
   ```toml
   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["./examples/hooks/notifications/slack-webhook.sh"]
   environment = { SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" }
   ```

## Email Notification Setup

1. Set up email configuration:
   ```bash
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   export SMTP_USERNAME="your-email@gmail.com"
   export SMTP_PASSWORD="your-app-password"
   export EMAIL_TO="recipient@example.com"
   export EMAIL_FROM="your-email@gmail.com"
   ```

2. Make the script executable:
   ```bash
   chmod +x examples/hooks/notifications/email-notification.py
   ```

3. Configure your `hooks.toml`:
   ```toml
   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["python3", "./examples/hooks/notifications/email-notification.py"]
   environment = { 
     SMTP_USERNAME = "your-email@gmail.com",
     SMTP_PASSWORD = "your-app-password",
     EMAIL_TO = "recipient@example.com"
   }
   ```

## Supported Events

Both notification hooks support the following events:

- `session_start` - When a Codex session begins
- `session_end` - When a Codex session ends
- `task_start` - When a task starts
- `task_end` - When a task completes
- `command_start` - When a command begins execution
- `command_end` - When a command finishes
- `error` - When an error occurs

## Security Notes

### Slack Webhook
- Store webhook URLs securely
- Consider using environment variables or secure configuration files
- Webhook URLs should be treated as secrets

### Email Notifications
- Use app-specific passwords for Gmail (not your regular password)
- Consider using OAuth2 for production environments
- Store credentials securely using environment variables or secret management

## Customization

You can customize the notification format by modifying the scripts:

- **Slack**: Edit the JSON payload structure and message formatting
- **Email**: Modify the `format_message()` function to change email content

## Testing

Test your notification setup:

```bash
# Test Slack webhook
CODEX_EVENT_TYPE="session_start" \
CODEX_SESSION_ID="test123" \
CODEX_MODEL="gpt-4" \
CODEX_TIMESTAMP="$(date -Iseconds)" \
./examples/hooks/notifications/slack-webhook.sh

# Test email notification
CODEX_EVENT_TYPE="session_start" \
CODEX_SESSION_ID="test123" \
CODEX_MODEL="gpt-4" \
CODEX_TIMESTAMP="$(date -Iseconds)" \
python3 ./examples/hooks/notifications/email-notification.py
```
