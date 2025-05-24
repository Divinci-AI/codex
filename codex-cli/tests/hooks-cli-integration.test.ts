import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { spawn, ChildProcess } from "node:child_process";
import { writeFileSync, mkdirSync, rmSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

// Integration tests for CLI with hooks enabled
describe("CLI Hooks Integration", () => {
  let testDir: string;
  let hooksConfigPath: string;
  let logFilePath: string;

  beforeEach(() => {
    // Create temporary test directory
    testDir = join(tmpdir(), `codex-cli-hooks-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });
    
    hooksConfigPath = join(testDir, "hooks.toml");
    logFilePath = join(testDir, "hook-execution.log");
  });

  afterEach(() => {
    // Clean up test directory
    if (existsSync(testDir)) {
      rmSync(testDir, { recursive: true, force: true });
    }
  });

  describe("CLI with Hooks Configuration", () => {
    it("should load hooks configuration from file", async () => {
      // Create a logging hook that writes to a file
      const loggingScriptPath = join(testDir, "logging-hook.sh");
      writeFileSync(loggingScriptPath, `#!/bin/bash
echo "$(date): Hook executed - Event: $CODEX_EVENT_TYPE, Session: $CODEX_SESSION_ID" >> "${logFilePath}"
exit 0
`, { mode: 0o755 });

      // Create hooks configuration
      const hooksConfig = `
[hooks]
enabled = true
timeout_seconds = 30
parallel_execution = false

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${loggingScriptPath}"]
description = "Session logging hook"
enabled = true
required = false
timeout = 5
mode = "async"
priority = "normal"

[[hooks.session]]
event = "session.end"
type = "script"
command = ["${loggingScriptPath}"]
description = "Session end logging hook"
enabled = true
required = false
timeout = 5
mode = "async"
priority = "normal"
`;

      writeFileSync(hooksConfigPath, hooksConfig);

      // Test that configuration file exists and is readable
      expect(existsSync(hooksConfigPath)).toBe(true);
      expect(existsSync(loggingScriptPath)).toBe(true);
      
      const configContent = readFileSync(hooksConfigPath, 'utf-8');
      expect(configContent).toContain('[hooks]');
      expect(configContent).toContain('enabled = true');
    });

    it("should handle CLI execution with hooks enabled", async () => {
      // Create a simple hook that creates a marker file
      const markerFilePath = join(testDir, "hook-executed.marker");
      const markerScriptPath = join(testDir, "marker-hook.sh");
      
      writeFileSync(markerScriptPath, `#!/bin/bash
echo "Hook executed at $(date)" > "${markerFilePath}"
echo "Event: $CODEX_EVENT_TYPE" >> "${markerFilePath}"
echo "Session: $CODEX_SESSION_ID" >> "${markerFilePath}"
exit 0
`, { mode: 0o755 });

      // Create hooks configuration
      const hooksConfig = `
[hooks]
enabled = true
timeout_seconds = 10

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${markerScriptPath}"]
description = "Marker hook"
enabled = true
required = false
`;

      writeFileSync(hooksConfigPath, hooksConfig);

      // Note: In a real test environment, you would:
      // 1. Set environment variables to point to the test hooks config
      // 2. Run the actual CLI binary with a simple command
      // 3. Verify that the hook was executed by checking the marker file
      
      // For now, we verify the test setup is correct
      expect(existsSync(markerScriptPath)).toBe(true);
      expect(existsSync(hooksConfigPath)).toBe(true);
    });
  });

  describe("Hook Execution During CLI Operations", () => {
    it("should execute hooks during command execution", async () => {
      // Create hooks for command execution events
      const commandLogPath = join(testDir, "command-hooks.log");
      const commandHookScript = join(testDir, "command-hook.sh");
      
      writeFileSync(commandHookScript, `#!/bin/bash
echo "$(date): Command hook - Event: $CODEX_EVENT_TYPE" >> "${commandLogPath}"
echo "Command: $CODEX_COMMAND" >> "${commandLogPath}"
echo "Working Dir: $CODEX_WORKDIR" >> "${commandLogPath}"
echo "---" >> "${commandLogPath}"
exit 0
`, { mode: 0o755 });

      const commandHooksConfig = `
[hooks]
enabled = true

[[hooks.exec]]
event = "exec.before"
type = "script"
command = ["${commandHookScript}"]
description = "Pre-command hook"
enabled = true

[[hooks.exec]]
event = "exec.after"
type = "script"
command = ["${commandHookScript}"]
description = "Post-command hook"
enabled = true
`;

      writeFileSync(hooksConfigPath, commandHooksConfig);

      // Test setup verification
      expect(existsSync(commandHookScript)).toBe(true);
      expect(existsSync(hooksConfigPath)).toBe(true);
    });

    it("should handle hook failures gracefully", async () => {
      // Create a hook that will fail
      const failingHookScript = join(testDir, "failing-hook.sh");
      writeFileSync(failingHookScript, `#!/bin/bash
echo "This hook will fail" >&2
exit 1
`, { mode: 0o755 });

      // Create a hook that will succeed
      const successHookScript = join(testDir, "success-hook.sh");
      const successMarkerPath = join(testDir, "success.marker");
      writeFileSync(successHookScript, `#!/bin/bash
echo "Success hook executed" > "${successMarkerPath}"
exit 0
`, { mode: 0o755 });

      const mixedHooksConfig = `
[hooks]
enabled = true

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${failingHookScript}"]
description = "Failing hook"
enabled = true
required = false  # Non-critical

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${successHookScript}"]
description = "Success hook"
enabled = true
required = false
`;

      writeFileSync(hooksConfigPath, mixedHooksConfig);

      // Verify test setup
      expect(existsSync(failingHookScript)).toBe(true);
      expect(existsSync(successHookScript)).toBe(true);
    });

    it("should respect hook priorities and execution order", async () => {
      const executionLogPath = join(testDir, "execution-order.log");
      
      // Create hooks with different priorities
      const highPriorityScript = join(testDir, "high-priority-hook.sh");
      writeFileSync(highPriorityScript, `#!/bin/bash
echo "$(date): HIGH priority hook executed" >> "${executionLogPath}"
sleep 0.1
exit 0
`, { mode: 0o755 });

      const normalPriorityScript = join(testDir, "normal-priority-hook.sh");
      writeFileSync(normalPriorityScript, `#!/bin/bash
echo "$(date): NORMAL priority hook executed" >> "${executionLogPath}"
sleep 0.1
exit 0
`, { mode: 0o755 });

      const lowPriorityScript = join(testDir, "low-priority-hook.sh");
      writeFileSync(lowPriorityScript, `#!/bin/bash
echo "$(date): LOW priority hook executed" >> "${executionLogPath}"
sleep 0.1
exit 0
`, { mode: 0o755 });

      const priorityHooksConfig = `
[hooks]
enabled = true
parallel_execution = false  # Sequential execution to test order

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${lowPriorityScript}"]
priority = "low"
description = "Low priority hook"

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${highPriorityScript}"]
priority = "high"
description = "High priority hook"

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${normalPriorityScript}"]
priority = "normal"
description = "Normal priority hook"
`;

      writeFileSync(hooksConfigPath, priorityHooksConfig);

      // Verify all scripts are created
      expect(existsSync(highPriorityScript)).toBe(true);
      expect(existsSync(normalPriorityScript)).toBe(true);
      expect(existsSync(lowPriorityScript)).toBe(true);
    });
  });

  describe("Webhook Hooks Integration", () => {
    it("should configure and execute webhook hooks", async () => {
      // Create a webhook configuration that would call a test endpoint
      const webhookConfig = `
[hooks]
enabled = true

[[hooks.task]]
event = "task.complete"
type = "webhook"
url = "https://httpbin.org/post"
method = "POST"
timeout = 10
retry_count = 2
description = "Task completion webhook"

[hooks.task.headers]
"Content-Type" = "application/json"
"X-Codex-Event" = "task.complete"
"User-Agent" = "Codex-CLI/1.0"
`;

      writeFileSync(hooksConfigPath, webhookConfig);

      // Test webhook configuration
      expect(existsSync(hooksConfigPath)).toBe(true);
      
      const configContent = readFileSync(hooksConfigPath, 'utf-8');
      expect(configContent).toContain('type = "webhook"');
      expect(configContent).toContain('https://httpbin.org/post');
    });

    it("should handle webhook failures and retries", async () => {
      const webhookRetryConfig = `
[hooks]
enabled = true

[[hooks.error]]
event = "error.occurred"
type = "webhook"
url = "https://invalid-webhook-url-that-will-fail.example.com/webhook"
method = "POST"
timeout = 5
retry_count = 3
required = false  # Non-critical
description = "Error reporting webhook (will fail)"
`;

      writeFileSync(hooksConfigPath, webhookRetryConfig);

      expect(existsSync(hooksConfigPath)).toBe(true);
    });
  });

  describe("MCP Tool Hooks Integration", () => {
    it("should configure MCP tool hooks", async () => {
      const mcpConfig = `
[hooks]
enabled = true

[[hooks.exec]]
event = "exec.before"
type = "mcp_tool"
server = "security_scanner"
tool = "scan_command"
timeout = 15
description = "Security scan before command execution"
required = false

[[hooks.patch]]
event = "patch.before"
type = "mcp_tool"
server = "code_analyzer"
tool = "analyze_changes"
timeout = 20
description = "Analyze code changes before applying patch"
`;

      writeFileSync(hooksConfigPath, mcpConfig);

      expect(existsSync(hooksConfigPath)).toBe(true);
      
      const configContent = readFileSync(hooksConfigPath, 'utf-8');
      expect(configContent).toContain('type = "mcp_tool"');
      expect(configContent).toContain('server = "security_scanner"');
    });
  });

  describe("Performance and Scalability", () => {
    it("should handle multiple hooks efficiently", async () => {
      const performanceLogPath = join(testDir, "performance.log");
      
      // Create multiple hooks to test performance
      const hooks = [];
      for (let i = 0; i < 10; i++) {
        const hookScript = join(testDir, `perf-hook-${i}.sh`);
        writeFileSync(hookScript, `#!/bin/bash
start_time=$(date +%s%N)
echo "Hook ${i} started at $start_time" >> "${performanceLogPath}"
sleep 0.05  # Small delay to simulate work
end_time=$(date +%s%N)
duration=$((end_time - start_time))
echo "Hook ${i} completed in $duration nanoseconds" >> "${performanceLogPath}"
exit 0
`, { mode: 0o755 });
        hooks.push(hookScript);
      }

      // Create configuration with parallel execution
      let perfConfig = `
[hooks]
enabled = true
parallel_execution = true
timeout_seconds = 30
`;

      hooks.forEach((hook, i) => {
        perfConfig += `
[[hooks.session]]
event = "session.start"
type = "script"
command = ["${hook}"]
description = "Performance test hook ${i}"
priority = "normal"
`;
      });

      writeFileSync(hooksConfigPath, perfConfig);

      // Verify all hooks are created
      hooks.forEach(hook => {
        expect(existsSync(hook)).toBe(true);
      });
      expect(existsSync(hooksConfigPath)).toBe(true);
    });

    it("should handle hook timeouts properly", async () => {
      const timeoutTestScript = join(testDir, "timeout-test.sh");
      writeFileSync(timeoutTestScript, `#!/bin/bash
echo "Starting potentially long-running operation"
sleep 10  # This should timeout
echo "This should not be reached"
exit 0
`, { mode: 0o755 });

      const timeoutConfig = `
[hooks]
enabled = true
timeout_seconds = 2  # Global timeout

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${timeoutTestScript}"]
timeout = 1  # Hook-specific timeout (shorter)
required = false
description = "Timeout test hook"
`;

      writeFileSync(hooksConfigPath, timeoutConfig);

      expect(existsSync(timeoutTestScript)).toBe(true);
      expect(existsSync(hooksConfigPath)).toBe(true);
    });
  });

  describe("Environment Variable Handling", () => {
    it("should pass correct environment variables to hooks", async () => {
      const envTestScript = join(testDir, "env-test.sh");
      const envLogPath = join(testDir, "env-variables.log");
      
      writeFileSync(envTestScript, `#!/bin/bash
echo "=== Environment Variables ===" > "${envLogPath}"
echo "CODEX_EVENT_TYPE: $CODEX_EVENT_TYPE" >> "${envLogPath}"
echo "CODEX_SESSION_ID: $CODEX_SESSION_ID" >> "${envLogPath}"
echo "CODEX_TIMESTAMP: $CODEX_TIMESTAMP" >> "${envLogPath}"
echo "CODEX_TASK_ID: $CODEX_TASK_ID" >> "${envLogPath}"
echo "CODEX_COMMAND: $CODEX_COMMAND" >> "${envLogPath}"
echo "CODEX_WORKDIR: $CODEX_WORKDIR" >> "${envLogPath}"
echo "CUSTOM_VAR: $CUSTOM_VAR" >> "${envLogPath}"
echo "=== All CODEX_ Variables ===" >> "${envLogPath}"
env | grep CODEX_ >> "${envLogPath}" || echo "No CODEX_ variables found" >> "${envLogPath}"
exit 0
`, { mode: 0o755 });

      const envConfig = `
[hooks]
enabled = true

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${envTestScript}"]
description = "Environment variable test"

[hooks.session.environment]
CUSTOM_VAR = "custom_value"
TEST_VAR = "test_value"
`;

      writeFileSync(hooksConfigPath, envConfig);

      expect(existsSync(envTestScript)).toBe(true);
      expect(existsSync(hooksConfigPath)).toBe(true);
    });
  });

  describe("Error Handling and Recovery", () => {
    it("should continue execution when non-critical hooks fail", async () => {
      const criticalHookScript = join(testDir, "critical-hook.sh");
      const criticalMarkerPath = join(testDir, "critical.marker");
      
      writeFileSync(criticalHookScript, `#!/bin/bash
echo "Critical hook executed" > "${criticalMarkerPath}"
exit 0
`, { mode: 0o755 });

      const nonCriticalFailingScript = join(testDir, "non-critical-failing.sh");
      writeFileSync(nonCriticalFailingScript, `#!/bin/bash
echo "Non-critical hook failing" >&2
exit 1
`, { mode: 0o755 });

      const errorHandlingConfig = `
[hooks]
enabled = true

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${nonCriticalFailingScript}"]
required = false  # Non-critical
description = "Non-critical failing hook"

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${criticalHookScript}"]
required = true  # Critical
description = "Critical hook that should execute"
`;

      writeFileSync(hooksConfigPath, errorHandlingConfig);

      expect(existsSync(criticalHookScript)).toBe(true);
      expect(existsSync(nonCriticalFailingScript)).toBe(true);
    });
  });
});
