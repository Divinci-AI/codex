# Analytics Hooks

This directory contains example hooks for tracking usage patterns and performance metrics during Codex sessions.

## Files

- `track-usage.js` - Tracks usage patterns and generates analytics reports
- `performance-metrics.py` - Monitors system performance during Codex operations

## Usage Analytics

The usage tracker collects comprehensive data about how Codex is being used.

### Setup

1. Ensure Node.js is installed
2. Make the script executable:
   ```bash
   chmod +x examples/hooks/analytics/track-usage.js
   ```

3. Configure your `hooks.toml` to track all events:
   ```toml
   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["node", "./examples/hooks/analytics/track-usage.js"]

   [[hooks.task]]
   event = "session_end"
   type = "script"
   command = ["node", "./examples/hooks/analytics/track-usage.js"]

   [[hooks.task]]
   event = "command_start"
   type = "script"
   command = ["node", "./examples/hooks/analytics/track-usage.js"]

   [[hooks.task]]
   event = "task_start"
   type = "script"
   command = ["node", "./examples/hooks/analytics/track-usage.js"]

   [[hooks.task]]
   event = "error"
   type = "script"
   command = ["node", "./examples/hooks/analytics/track-usage.js"]
   ```

### Features

- **Session Tracking**: Records session start/end times and durations
- **Command Analytics**: Tracks command usage patterns
- **Model Usage**: Monitors which models are used most frequently
- **Error Tracking**: Records error rates and patterns
- **Daily Reports**: Generates daily usage summaries

### Data Storage

Analytics data is stored in `~/.codex/analytics/`:
- `usage-YYYY-MM-DD.json` - Daily usage logs
- `usage-summary.json` - Cumulative usage statistics

### Generating Reports

Generate a usage report:
```bash
node examples/hooks/analytics/track-usage.js --report
```

Sample output:
```
📊 Codex Usage Analytics Report
================================
Total Sessions: 45
Total Events: 1,234
Total Commands: 567
Total Tasks: 89
Error Rate: 2.3%
Average Session Duration: 12.5 minutes

Most Used Models:
  gpt-4: 30 sessions
  gpt-3.5-turbo: 15 sessions

Most Used Commands:
  ls: 45 times
  cat: 32 times
  git: 28 times
```

## Performance Metrics

The performance monitor tracks system resource usage during Codex operations.

### Setup

1. Install required Python packages:
   ```bash
   pip install psutil
   ```

2. Make the script executable:
   ```bash
   chmod +x examples/hooks/analytics/performance-metrics.py
   ```

3. Configure your `hooks.toml`:
   ```toml
   [[hooks.task]]
   event = "session_start"
   type = "script"
   command = ["python3", "./examples/hooks/analytics/performance-metrics.py"]

   [[hooks.task]]
   event = "session_end"
   type = "script"
   command = ["python3", "./examples/hooks/analytics/performance-metrics.py"]

   [[hooks.task]]
   event = "command_start"
   type = "script"
   command = ["python3", "./examples/hooks/analytics/performance-metrics.py"]

   [[hooks.task]]
   event = "task_start"
   type = "script"
   command = ["python3", "./examples/hooks/analytics/performance-metrics.py"]
   ```

### Features

- **CPU Monitoring**: Tracks CPU usage during operations
- **Memory Monitoring**: Records memory consumption patterns
- **Disk Usage**: Monitors available disk space
- **Peak Detection**: Identifies peak resource usage
- **Session Correlation**: Links performance data to specific sessions

### Data Storage

Performance data is stored in `~/.codex/analytics/`:
- `metrics-YYYY-MM-DD.json` - Daily performance metrics
- `performance-metrics.json` - Cumulative performance data

### Metrics Collected

- CPU percentage usage
- Memory percentage usage
- Available memory (GB)
- Disk usage percentage
- Available disk space (GB)
- Peak CPU and memory usage per session
- Average resource usage over time

## Data Analysis

### Usage Patterns

The analytics help identify:
- Most active times of day
- Preferred models and providers
- Common command patterns
- Error-prone operations
- Session duration trends

### Performance Insights

Performance metrics reveal:
- Resource-intensive operations
- System bottlenecks
- Optimal session lengths
- Hardware utilization patterns

## Privacy and Security

### Data Collection
- All data is stored locally on your machine
- No data is transmitted to external services
- Personal information is not collected
- File contents are not logged

### Data Retention
- Daily logs are kept indefinitely by default
- You can implement custom cleanup scripts
- Summary data is aggregated and anonymized

### Customization

You can customize data collection by:
- Modifying the tracking scripts
- Adding custom metrics
- Implementing data filtering
- Creating custom reports

## Integration Examples

### Dashboard Integration
```bash
# Create a simple dashboard
cat ~/.codex/analytics/usage-summary.json | jq '.total_sessions'
```

### Automated Reports
```bash
# Daily report via cron
0 9 * * * node /path/to/track-usage.js --report | mail -s "Daily Codex Report" user@example.com
```

### Performance Alerts
```python
# Alert on high resource usage
if cpu_percent > 90:
    send_alert("High CPU usage detected")
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure analytics directory is writable
2. **Missing Dependencies**: Install required packages (psutil for Python)
3. **Large Log Files**: Implement log rotation if files become too large
4. **Performance Impact**: Adjust monitoring frequency if needed

### Debug Mode

Enable debug output:
```bash
DEBUG=1 node examples/hooks/analytics/track-usage.js
DEBUG=1 python3 examples/hooks/analytics/performance-metrics.py
```
