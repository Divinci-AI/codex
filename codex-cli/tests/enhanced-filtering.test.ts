import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { HookExecutor, type HookContext } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Enhanced Filtering System", () => {
  let testDir: string;
  let hookOutputFile: string;

  beforeEach(() => {
    testDir = join(tmpdir(), `codex-filtering-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });
    hookOutputFile = join(testDir, "hook-output.txt");

    // Create a simple test hook script
    const hookScript = join(testDir, "test-hook.sh");
    const scriptContent = `#!/bin/bash
echo "Hook executed: $CODEX_EVENT_TYPE" >> "${hookOutputFile}"
echo "Command: $CODEX_COMMAND" >> "${hookOutputFile}"
`;
    writeFileSync(hookScript, scriptContent);
    chmodSync(hookScript, 0o755);
  });

  afterEach(() => {
    try {
      const files = ["hook-output.txt", "test-hook.sh"];
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
    eventType: "command_start",
    eventData: {},
    ...overrides,
  });

  it("should filter by file extensions", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onPatchApply: {
          script: "./test-hook.sh",
          filter: {
            fileExtensions: ["ts", "js"],
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute for TypeScript files
    const tsContext = createTestContext({
      eventType: "patch_apply",
      eventData: { files: ["src/test.ts", "src/utils.js"] },
    });
    const tsResult = await hookExecutor.executeHook("onPatchApply", tsContext);
    expect(tsResult).not.toBeNull();

    // Should not execute for other file types
    const pyContext = createTestContext({
      eventType: "patch_apply",
      eventData: { files: ["script.py", "README.md"] },
    });
    const pyResult = await hookExecutor.executeHook("onPatchApply", pyContext);
    expect(pyResult).toBeNull();
  });

  it("should filter by duration range", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandComplete: {
          script: "./test-hook.sh",
          filter: {
            durationRange: {
              min: 1000, // 1 second
              max: 5000, // 5 seconds
            },
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute for commands within duration range
    const validContext = createTestContext({
      eventType: "command_complete",
      eventData: { durationMs: 3000 },
    });
    const validResult = await hookExecutor.executeHook("onCommandComplete", validContext);
    expect(validResult).not.toBeNull();

    // Should not execute for commands too fast
    const fastContext = createTestContext({
      eventType: "command_complete",
      eventData: { durationMs: 500 },
    });
    const fastResult = await hookExecutor.executeHook("onCommandComplete", fastContext);
    expect(fastResult).toBeNull();

    // Should not execute for commands too slow
    const slowContext = createTestContext({
      eventType: "command_complete",
      eventData: { durationMs: 10000 },
    });
    const slowResult = await hookExecutor.executeHook("onCommandComplete", slowContext);
    expect(slowResult).toBeNull();
  });

  it("should filter by time range", async () => {
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    
    // Create a time range that includes the current time
    const startTime = `${String(currentHour).padStart(2, '0')}:${String(Math.max(0, currentMinute - 5)).padStart(2, '0')}`;
    const endTime = `${String(currentHour).padStart(2, '0')}:${String(Math.min(59, currentMinute + 5)).padStart(2, '0')}`;

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onTaskStart: {
          script: "./test-hook.sh",
          filter: {
            timeRange: {
              start: startTime,
              end: endTime,
              daysOfWeek: [now.getDay()], // Current day of week
            },
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute during valid time range
    const context = createTestContext({
      eventType: "task_start",
    });
    const result = await hookExecutor.executeHook("onTaskStart", context);
    expect(result).not.toBeNull();
  });

  it("should filter by environment variables", async () => {
    // Set a test environment variable
    process.env.TEST_ENV_VAR = "test-value";
    process.env.TEST_REGEX_VAR = "production-server-01";

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./test-hook.sh",
          filter: {
            environment: {
              TEST_ENV_VAR: "test-value",
              // Note: RegExp objects can't be serialized in JSON, so this would need
              // to be handled differently in real config (e.g., as string patterns)
            },
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute when environment matches
    const context = createTestContext({
      eventType: "command_start",
      eventData: { command: ["echo", "test"] },
    });
    const result = await hookExecutor.executeHook("onCommandStart", context);
    expect(result).not.toBeNull();

    // Clean up
    delete process.env.TEST_ENV_VAR;
    delete process.env.TEST_REGEX_VAR;
  });

  it("should filter by custom expressions", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandComplete: {
          script: "./test-hook.sh",
          filter: {
            customExpression: "exitCode === 0 && command && command.includes('npm')",
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute for successful npm commands
    const successContext = createTestContext({
      eventType: "command_complete",
      eventData: {
        command: ["npm", "test"],
        exitCode: 0,
      },
    });
    const successResult = await hookExecutor.executeHook("onCommandComplete", successContext);
    expect(successResult).not.toBeNull();

    // Should not execute for failed npm commands
    const failContext = createTestContext({
      eventType: "command_complete",
      eventData: {
        command: ["npm", "test"],
        exitCode: 1,
      },
    });
    const failResult = await hookExecutor.executeHook("onCommandComplete", failContext);
    expect(failResult).toBeNull();

    // Should not execute for successful non-npm commands
    const nonNpmContext = createTestContext({
      eventType: "command_complete",
      eventData: {
        command: ["echo", "hello"],
        exitCode: 0,
      },
    });
    const nonNpmResult = await hookExecutor.executeHook("onCommandComplete", nonNpmContext);
    expect(nonNpmResult).toBeNull();
  });

  it("should handle invalid custom expressions gracefully", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./test-hook.sh",
          filter: {
            customExpression: "invalid.syntax.here(", // Invalid JavaScript
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should not execute due to invalid expression
    const context = createTestContext({
      eventType: "command_start",
      eventData: { command: ["echo", "test"] },
    });
    const result = await hookExecutor.executeHook("onCommandStart", context);
    expect(result).toBeNull();
  });

  it("should combine multiple filters with AND logic", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandComplete: {
          script: "./test-hook.sh",
          filter: {
            commands: ["npm"],
            exitCodes: [0],
            durationRange: {
              min: 100,
              max: 10000,
            },
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Should execute when all filters match
    const validContext = createTestContext({
      eventType: "command_complete",
      eventData: {
        command: ["npm", "test"],
        exitCode: 0,
        durationMs: 5000,
      },
    });
    const validResult = await hookExecutor.executeHook("onCommandComplete", validContext);
    expect(validResult).not.toBeNull();

    // Should not execute when one filter doesn't match
    const invalidContext = createTestContext({
      eventType: "command_complete",
      eventData: {
        command: ["npm", "test"],
        exitCode: 1, // Wrong exit code
        durationMs: 5000,
      },
    });
    const invalidResult = await hookExecutor.executeHook("onCommandComplete", invalidContext);
    expect(invalidResult).toBeNull();
  });
});
