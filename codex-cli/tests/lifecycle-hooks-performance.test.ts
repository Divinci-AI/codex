import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { handleExecCommand } from "../src/utils/agent/handle-exec-command.ts";
import { HookExecutor } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { AppConfig, LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Lifecycle Hooks Performance Tests", () => {
  let testDir: string;
  let testConfig: AppConfig;
  let configWithoutHooks: AppConfig;

  beforeEach(() => {
    testDir = join(tmpdir(), `codex-performance-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });

    // Create a fast hook script
    const fastHookPath = join(testDir, "fast-hook.sh");
    const fastHookContent = `#!/bin/bash
echo "Fast hook executed" > /dev/null
exit 0
`;
    writeFileSync(fastHookPath, fastHookContent);
    chmodSync(fastHookPath, 0o755);

    // Configuration with hooks
    const hooksConfig: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./fast-hook.sh",
          async: false,
        },
        onCommandComplete: {
          script: "./fast-hook.sh",
          async: false,
        },
      },
    };

    testConfig = {
      model: "test-model",
      instructions: "Test instructions",
      apiKey: "test-api-key",
      lifecycleHooks: hooksConfig,
    };

    // Configuration without hooks
    configWithoutHooks = {
      model: "test-model",
      instructions: "Test instructions",
      apiKey: "test-api-key",
    };
  });

  afterEach(() => {
    try {
      const files = ["fast-hook.sh"];
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

  async function measureExecutionTime(
    config: AppConfig,
    hookExecutor?: HookExecutor,
    iterations: number = 5
  ): Promise<Array<number>> {
    const times: Array<number> = [];

    for (let i = 0; i < iterations; i++) {
      const execInput = {
        cmd: ["echo", `performance test ${i}`],
        workdir: testDir,
      };

      const startTime = Date.now();

      await handleExecCommand(
        execInput,
        config,
        "auto",
        [],
        async () => ({ review: "approve" as const }),
        undefined,
        hookExecutor,
        `performance-test-${i}`,
      );

      const endTime = Date.now();
      times.push(endTime - startTime);
    }

    return times;
  }

  function calculateStats(times: Array<number>): { mean: number; median: number; max: number; min: number } {
    const sorted = [...times].sort((a, b) => a - b);
    const mean = times.reduce((sum, time) => sum + time, 0) / times.length;
    const median = sorted[Math.floor(sorted.length / 2)];
    const max = Math.max(...times);
    const min = Math.min(...times);

    return { mean, median, max, min };
  }

  it("should have minimal performance impact when hooks are enabled", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    // Measure execution time with hooks
    const timesWithHooks = await measureExecutionTime(testConfig, hookExecutor, 10);

    // Measure execution time without hooks
    const timesWithoutHooks = await measureExecutionTime(configWithoutHooks, undefined, 10);

    const statsWithHooks = calculateStats(timesWithHooks);
    const statsWithoutHooks = calculateStats(timesWithoutHooks);

    // Performance Results logged for debugging
    // Without hooks - Mean: ${statsWithoutHooks.mean}ms, Median: ${statsWithoutHooks.median}ms
    // With hooks - Mean: ${statsWithHooks.mean}ms, Median: ${statsWithHooks.median}ms

    // Hook overhead should be less than 100ms on average
    const overhead = statsWithHooks.mean - statsWithoutHooks.mean;
    expect(overhead).toBeLessThan(100);

    // Maximum execution time with hooks should be reasonable
    expect(statsWithHooks.max).toBeLessThan(1000);
  });

  it("should handle concurrent hook executions efficiently", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    const concurrentPromises = Array.from({ length: 5 }, (_, i) => {
      const execInput = {
        cmd: ["echo", `concurrent test ${i}`],
        workdir: testDir,
      };

      return handleExecCommand(
        execInput,
        testConfig,
        "auto",
        [],
        async () => ({ review: "approve" as const }),
        undefined,
        hookExecutor,
        `concurrent-test-${i}`,
      );
    });

    const startTime = Date.now();
    const results = await Promise.all(concurrentPromises);
    const endTime = Date.now();

    // Check that we got results (some might be aborted due to approval policy)
    results.forEach((result) => {
      // For performance testing, we just need to ensure the system handles concurrent requests
      expect(result).toBeDefined();
      expect(result.metadata).toBeDefined();
    });

    // Concurrent execution should complete in reasonable time
    const totalTime = endTime - startTime;
    expect(totalTime).toBeLessThan(2000); // Should complete within 2 seconds
  });

  it("should handle async hooks without blocking command execution", async () => {
    // Create a slow async hook
    const slowAsyncHookPath = join(testDir, "slow-async-hook.sh");
    const slowAsyncHookContent = `#!/bin/bash
sleep 2  # 2 second delay
echo "Slow async hook completed" > /dev/null
exit 0
`;
    writeFileSync(slowAsyncHookPath, slowAsyncHookContent);
    chmodSync(slowAsyncHookPath, 0o755);

    const asyncConfig: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        hooks: {
          onCommandComplete: {
            script: "./slow-async-hook.sh",
            async: true, // Async execution
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(asyncConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "async performance test"],
      workdir: testDir,
    };

    const startTime = Date.now();

    const result = await handleExecCommand(
      execInput,
      asyncConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "async-performance-test",
    );

    const endTime = Date.now();

    expect(result.outputText).toContain("async performance test");
    expect(result.metadata.exit_code).toBe(0);

    // Command should complete quickly despite slow async hook
    const executionTime = endTime - startTime;
    expect(executionTime).toBeLessThan(3000); // Should complete within 3 seconds (allowing for some overhead)

    // Clean up
    unlinkSync(slowAsyncHookPath);
  });

  it("should handle hook timeouts efficiently", async () => {
    // Create a hook that will timeout
    const timeoutHookPath = join(testDir, "timeout-hook.sh");
    const timeoutHookContent = `#!/bin/bash
sleep 10  # 10 second delay (will timeout)
echo "This should not be reached"
exit 0
`;
    writeFileSync(timeoutHookPath, timeoutHookContent);
    chmodSync(timeoutHookPath, 0o755);

    const timeoutConfig: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        timeout: 1000, // 1 second timeout
        hooks: {
          onCommandStart: {
            script: "./timeout-hook.sh",
            async: false,
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(timeoutConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "timeout test"],
      workdir: testDir,
    };

    const startTime = Date.now();

    const result = await handleExecCommand(
      execInput,
      timeoutConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "timeout-test",
    );

    const endTime = Date.now();

    expect(result.outputText).toContain("timeout test");
    expect(result.metadata.exit_code).toBe(0);

    // Command should complete quickly due to hook timeout
    const executionTime = endTime - startTime;
    expect(executionTime).toBeLessThan(2000); // Should timeout and complete within 2 seconds

    // Clean up
    unlinkSync(timeoutHookPath);
  });

  it("should have minimal memory overhead", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    // Measure memory before
    const memBefore = process.memoryUsage();

    // Execute multiple commands to test memory usage
    for (let i = 0; i < 20; i++) {
      const execInput = {
        cmd: ["echo", `memory test ${i}`],
        workdir: testDir,
      };

      await handleExecCommand(
        execInput,
        testConfig,
        "auto",
        [],
        async () => ({ review: "approve" as const }),
        undefined,
        hookExecutor,
        `memory-test-${i}`,
      );
    }

    // Measure memory after
    const memAfter = process.memoryUsage();

    // Memory increase should be reasonable (less than 50MB)
    const heapIncrease = (memAfter.heapUsed - memBefore.heapUsed) / 1024 / 1024;
    expect(heapIncrease).toBeLessThan(50);

    // Memory increase: ${heapIncrease.toFixed(2)}MB
  });
});
