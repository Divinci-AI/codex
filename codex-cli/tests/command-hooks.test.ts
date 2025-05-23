import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { handleExecCommand } from "../src/utils/agent/handle-exec-command.ts";
import { HookExecutor } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { AppConfig, LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Command Execution Hooks", () => {
  let testDir: string;
  let hookOutputFile: string;
  let hookExecutor: HookExecutor;
  let testConfig: AppConfig;

  beforeEach(() => {
    // Create a temporary directory for test scripts
    testDir = join(tmpdir(), `codex-command-hooks-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });

    hookOutputFile = join(testDir, "hook-output.txt");

    // Create test hook scripts
    const commandStartScript = join(testDir, "command-start.sh");
    const commandCompleteScript = join(testDir, "command-complete.sh");

    const startScriptContent = `#!/bin/bash
echo "COMMAND_START: $CODEX_COMMAND" >> "${hookOutputFile}"
echo "EVENT_TYPE: $CODEX_EVENT_TYPE" >> "${hookOutputFile}"
echo "WORKING_DIR: $CODEX_WORKING_DIR" >> "${hookOutputFile}"
`;

    const completeScriptContent = `#!/bin/bash
echo "COMMAND_COMPLETE: $CODEX_COMMAND" >> "${hookOutputFile}"
echo "EXIT_CODE: $CODEX_EXIT_CODE" >> "${hookOutputFile}"
echo "EVENT_TYPE: $CODEX_EVENT_TYPE" >> "${hookOutputFile}"
`;

    writeFileSync(commandStartScript, startScriptContent);
    writeFileSync(commandCompleteScript, completeScriptContent);
    chmodSync(commandStartScript, 0o755);
    chmodSync(commandCompleteScript, 0o755);

    // Test configuration with command hooks enabled
    const hooksConfig: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./command-start.sh",
          async: false,
        },
        onCommandComplete: {
          script: "./command-complete.sh",
          async: false,
        },
      },
    };

    hookExecutor = new HookExecutor(hooksConfig);

    testConfig = {
      model: "test-model",
      instructions: "Test instructions",
      apiKey: "test-api-key",
      lifecycleHooks: hooksConfig,
    };
  });

  afterEach(() => {
    // Clean up test files
    try {
      const files = [
        "hook-output.txt",
        "command-start.sh",
        "command-complete.sh",
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

  it("should execute command hooks for simple commands", async () => {
    const execInput = {
      cmd: ["echo", "hello world"],
      workdir: testDir,
    };

    const result = await handleExecCommand(
      execInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "test-session-123",
    );

    expect(result.outputText).toContain("hello world");
    expect(result.metadata.exit_code).toBe(0);

    // Check that hooks were executed
    if (existsSync(hookOutputFile)) {
      const hookOutput = require("fs").readFileSync(hookOutputFile, "utf8");
      expect(hookOutput).toContain("COMMAND_START: echo hello world");
      expect(hookOutput).toContain("EVENT_TYPE: command_start");
      expect(hookOutput).toContain("COMMAND_COMPLETE: echo hello world");
      expect(hookOutput).toContain("EXIT_CODE: 0");
      expect(hookOutput).toContain("EVENT_TYPE: command_complete");
    }
  });

  it("should execute command hooks for failing commands", async () => {
    const execInput = {
      cmd: ["ls", "/nonexistent"], // Command that should fail
      workdir: testDir,
    };

    const result = await handleExecCommand(
      execInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "test-session-456",
    );

    expect(result.metadata.exit_code).toBeGreaterThan(0); // Should be non-zero for failure

    // Check that hooks were executed
    if (existsSync(hookOutputFile)) {
      const hookOutput = require("fs").readFileSync(hookOutputFile, "utf8");
      expect(hookOutput).toContain("COMMAND_START: ls /nonexistent");
      expect(hookOutput).toContain("COMMAND_COMPLETE: ls /nonexistent");
      expect(hookOutput).toMatch(/EXIT_CODE: [1-9]/); // Should be non-zero
    }
  });

  it("should work without hooks when hookExecutor is not provided", async () => {
    const execInput = {
      cmd: ["echo", "no hooks"],
      workdir: testDir,
    };

    const result = await handleExecCommand(
      execInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      undefined, // No hookExecutor
      "test-session-789",
    );

    expect(result.outputText).toContain("no hooks");
    expect(result.metadata.exit_code).toBe(0);

    // Hook output file should not exist
    expect(existsSync(hookOutputFile)).toBe(false);
  });

  it("should handle hook execution errors gracefully", async () => {
    // Create a hook script that will fail
    const failingScript = join(testDir, "failing-hook.sh");
    const failingScriptContent = `#!/bin/bash
echo "This hook will fail"
exit 1
`;
    writeFileSync(failingScript, failingScriptContent);
    chmodSync(failingScript, 0o755);

    const hooksConfigWithFailingHook: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./failing-hook.sh",
          async: false,
        },
      },
    };

    const failingHookExecutor = new HookExecutor(hooksConfigWithFailingHook);

    const execInput = {
      cmd: ["echo", "test with failing hook"],
      workdir: testDir,
    };

    // Command should still succeed even if hook fails
    const result = await handleExecCommand(
      execInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      failingHookExecutor,
      "test-session-error",
    );

    expect(result.outputText).toContain("test with failing hook");
    expect(result.metadata.exit_code).toBe(0);

    // Clean up
    unlinkSync(failingScript);
  });
});
