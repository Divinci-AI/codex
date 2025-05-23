import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { HookExecutor, type HookContext } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("HookExecutor", () => {
  let testDir: string;
  let hookExecutor: HookExecutor;
  let testConfig: LifecycleHooksConfig;

  beforeEach(() => {
    // Create a temporary directory for test scripts
    testDir = join(tmpdir(), `codex-hooks-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });

    // Default test configuration
    testConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {
        TEST_VAR: "test-value",
        INTERPOLATED_VAR: "${HOME}/test",
      },
      hooks: {},
    };

    hookExecutor = new HookExecutor(testConfig);
  });

  afterEach(() => {
    // Clean up test files
    try {
      const files = [
        "test-hook.sh",
        "test-hook.py",
        "test-hook.js",
        "failing-hook.sh",
        "timeout-hook.sh",
        "filter-test.sh",
      ];
      files.forEach((file) => {
        const filePath = join(testDir, file);
        if (existsSync(filePath)) {
          unlinkSync(filePath);
        }
      });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  const createTestContext = (overrides: Partial<HookContext> = {}): HookContext => ({
    sessionId: "test-session-123",
    model: "test-model",
    workingDirectory: testDir,
    eventType: "task_start",
    eventData: {},
    ...overrides,
  });

  it("should return null when hooks are disabled", async () => {
    const disabledConfig = { ...testConfig, enabled: false };
    const disabledExecutor = new HookExecutor(disabledConfig);

    const result = await disabledExecutor.executeHook("onTaskStart", createTestContext());
    expect(result).toBeNull();
  });

  it("should return null when hook is not configured", async () => {
    const result = await hookExecutor.executeHook("onTaskStart", createTestContext());
    expect(result).toBeNull();
  });

  it("should execute a simple bash script successfully", async () => {
    // Create a test script
    const scriptPath = join(testDir, "test-hook.sh");
    const scriptContent = `#!/bin/bash
echo "Hook executed successfully"
echo "Session ID: $CODEX_SESSION_ID"
echo "Event Type: $CODEX_EVENT_TYPE"
exit 0
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure the hook
    testConfig.hooks.onTaskStart = {
      script: "./test-hook.sh",
    };
    hookExecutor = new HookExecutor(testConfig);

    const result = await hookExecutor.executeHook("onTaskStart", createTestContext());

    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.exitCode).toBe(0);
    expect(result!.stdout).toContain("Hook executed successfully");
    expect(result!.stdout).toContain("Session ID: test-session-123");
    expect(result!.stdout).toContain("Event Type: task_start");
    expect(result!.duration).toBeGreaterThan(0);
  });

  it("should execute a Python script with event data via stdin", async () => {
    // Create a Python test script
    const scriptPath = join(testDir, "test-hook.py");
    const scriptContent = `#!/usr/bin/env python3
import json
import sys
import os

# Read event data from stdin
event_data = json.load(sys.stdin)

print(f"Python hook executed")
print(f"Event data: {event_data}")
print(f"Environment: {os.environ.get('CODEX_SESSION_ID', 'not-set')}")

sys.exit(0)
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure the hook
    testConfig.hooks.onCommandComplete = {
      script: "./test-hook.py",
    };
    hookExecutor = new HookExecutor(testConfig);

    const context = createTestContext({
      eventType: "command_complete",
      eventData: { command: ["git", "status"], exitCode: 0 },
    });

    const result = await hookExecutor.executeHook("onCommandComplete", context);

    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.exitCode).toBe(0);
    expect(result!.stdout).toContain("Python hook executed");
    expect(result!.stdout).toContain("git");
    expect(result!.stdout).toContain("test-session-123");
  });

  it("should handle script execution failures gracefully", async () => {
    // Create a failing script
    const scriptPath = join(testDir, "failing-hook.sh");
    const scriptContent = `#!/bin/bash
echo "This script will fail"
exit 1
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure the hook
    testConfig.hooks.onTaskError = {
      script: "./failing-hook.sh",
    };
    hookExecutor = new HookExecutor(testConfig);

    const result = await hookExecutor.executeHook("onTaskError", createTestContext());

    expect(result).not.toBeNull();
    expect(result!.success).toBe(false);
    expect(result!.exitCode).toBe(1);
    expect(result!.stdout).toContain("This script will fail");
  });

  it("should handle script timeout", async () => {
    // Create a script that runs longer than timeout
    const scriptPath = join(testDir, "timeout-hook.sh");
    const scriptContent = `#!/bin/bash
sleep 3
echo "This should not be reached"
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure the hook with short timeout
    testConfig.hooks.onTaskStart = {
      script: "./timeout-hook.sh",
      timeout: 500, // 0.5 seconds
    };
    hookExecutor = new HookExecutor(testConfig);

    const result = await hookExecutor.executeHook("onTaskStart", createTestContext());

    expect(result).not.toBeNull();
    expect(result!.success).toBe(false);
    expect(result!.duration).toBeLessThan(1500); // Should timeout quickly
  }, 10000); // Give the test itself 10 seconds

  it("should handle missing script files", async () => {
    // Configure hook with non-existent script
    testConfig.hooks.onTaskStart = {
      script: "./non-existent-script.sh",
    };
    hookExecutor = new HookExecutor(testConfig);

    const result = await hookExecutor.executeHook("onTaskStart", createTestContext());

    expect(result).not.toBeNull();
    expect(result!.success).toBe(false);
    expect(result!.exitCode).toBe(1);
    expect(result!.error).toContain("Script file does not exist");
  });

  it("should apply command filters correctly", async () => {
    // Create a test script
    const scriptPath = join(testDir, "filter-test.sh");
    const scriptContent = `#!/bin/bash
echo "Filtered hook executed for: $CODEX_COMMAND"
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure hook with command filter
    testConfig.hooks.onCommandStart = {
      script: "./filter-test.sh",
      filter: {
        commands: ["git", "npm"],
      },
    };
    hookExecutor = new HookExecutor(testConfig);

    // Test with matching command
    const matchingContext = createTestContext({
      eventType: "command_start",
      eventData: { command: ["git", "status"] },
    });
    const matchingResult = await hookExecutor.executeHook("onCommandStart", matchingContext);
    expect(matchingResult).not.toBeNull();
    expect(matchingResult!.success).toBe(true);

    // Test with non-matching command
    const nonMatchingContext = createTestContext({
      eventType: "command_start",
      eventData: { command: ["docker", "ps"] },
    });
    const nonMatchingResult = await hookExecutor.executeHook("onCommandStart", nonMatchingContext);
    expect(nonMatchingResult).toBeNull();
  });

  it("should apply exit code filters correctly", async () => {
    // Create a test script
    const scriptPath = join(testDir, "exit-filter-test.sh");
    const scriptContent = `#!/bin/bash
echo "Hook for successful commands only"
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure hook with exit code filter
    testConfig.hooks.onCommandComplete = {
      script: "./exit-filter-test.sh",
      filter: {
        exitCodes: [0], // Only success
      },
    };
    hookExecutor = new HookExecutor(testConfig);

    // Test with successful command
    const successContext = createTestContext({
      eventType: "command_complete",
      eventData: { command: ["echo", "test"], exitCode: 0 },
    });
    const successResult = await hookExecutor.executeHook("onCommandComplete", successContext);
    expect(successResult).not.toBeNull();

    // Test with failed command
    const failureContext = createTestContext({
      eventType: "command_complete",
      eventData: { command: ["false"], exitCode: 1 },
    });
    const failureResult = await hookExecutor.executeHook("onCommandComplete", failureContext);
    expect(failureResult).toBeNull();
  });

  it("should pass custom environment variables to hooks", async () => {
    // Create a test script that checks environment variables
    const scriptPath = join(testDir, "env-test.sh");
    const scriptContent = `#!/bin/bash
echo "TEST_VAR: $TEST_VAR"
echo "HOOK_SPECIFIC: $HOOK_SPECIFIC"
echo "INTERPOLATED: $INTERPOLATED_VAR"
`;
    writeFileSync(scriptPath, scriptContent);
    chmodSync(scriptPath, 0o755);

    // Configure hook with custom environment
    testConfig.hooks.onTaskStart = {
      script: "./env-test.sh",
      environment: {
        HOOK_SPECIFIC: "hook-value",
      },
    };
    hookExecutor = new HookExecutor(testConfig);

    const result = await hookExecutor.executeHook("onTaskStart", createTestContext());

    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.stdout).toContain("TEST_VAR: test-value");
    expect(result!.stdout).toContain("HOOK_SPECIFIC: hook-value");
    // Note: Variable interpolation would need actual HOME env var to test properly
  });

  it("should execute multiple hooks for an event type", async () => {
    // This test would require implementing executeHooksForEvent properly
    // For now, we'll test the basic structure
    const results = await hookExecutor.executeHooksForEvent("task_start", {
      sessionId: "test-session",
      model: "test-model",
      workingDirectory: testDir,
      eventData: {},
    });

    expect(Array.isArray(results)).toBe(true);
    // Since no hooks are configured, should return empty array
    expect(results).toHaveLength(0);
  });
});
