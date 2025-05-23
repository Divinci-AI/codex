import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { handleExecCommand } from "../src/utils/agent/handle-exec-command.ts";
import { HookExecutor } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { AppConfig, LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync, readFileSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Lifecycle Hooks Integration Tests", () => {
  let testDir: string;
  let hookOutputFile: string;
  let testConfig: AppConfig;

  beforeEach(() => {
    testDir = join(tmpdir(), `codex-integration-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });
    hookOutputFile = join(testDir, "integration-output.txt");

    // Create comprehensive test hook scripts
    createTestHookScripts();

    // Test configuration with all hooks enabled
    const hooksConfig: LifecycleHooksConfig = {
      enabled: true,
      timeout: 10000,
      workingDirectory: testDir,
      environment: {
        TEST_INTEGRATION: "true",
        OUTPUT_FILE: hookOutputFile,
      },
      hooks: {
        onTaskStart: {
          script: "./task-start-hook.sh",
          async: false,
        },
        onTaskComplete: {
          script: "./task-complete-hook.sh",
          async: false,
        },
        onTaskError: {
          script: "./task-error-hook.sh",
          async: false,
        },
        onCommandStart: {
          script: "./command-start-hook.sh",
          async: false,
          filter: {
            commands: ["echo", "ls"],
          },
        },
        onCommandComplete: {
          script: "./command-complete-hook.sh",
          async: false,
        },
        onPatchApply: {
          script: "./patch-apply-hook.sh",
          async: false,
          filter: {
            fileExtensions: ["txt", "md"],
          },
        },
      },
    };

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
        "integration-output.txt",
        "task-start-hook.sh",
        "task-complete-hook.sh",
        "task-error-hook.sh",
        "command-start-hook.sh",
        "command-complete-hook.sh",
        "patch-apply-hook.sh",
        "test-file.txt",
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

  function createTestHookScripts() {
    const scripts = {
      "task-start-hook.sh": `#!/bin/bash
echo "TASK_START:\${CODEX_SESSION_ID}:\${CODEX_MODEL}" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
      "task-complete-hook.sh": `#!/bin/bash
echo "TASK_COMPLETE:\${CODEX_SESSION_ID}" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
      "task-error-hook.sh": `#!/bin/bash
echo "TASK_ERROR:\${CODEX_SESSION_ID}" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
      "command-start-hook.sh": `#!/bin/bash
echo "COMMAND_START:\${CODEX_COMMAND}" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
      "command-complete-hook.sh": `#!/bin/bash
echo "COMMAND_COMPLETE:\${CODEX_COMMAND}:\${CODEX_EXIT_CODE}" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
      "patch-apply-hook.sh": `#!/bin/bash
echo "PATCH_APPLY" >> "\${OUTPUT_FILE}"
cat >> "\${OUTPUT_FILE}"
echo "---" >> "\${OUTPUT_FILE}"
`,
    };

    Object.entries(scripts).forEach(([filename, content]) => {
      const scriptPath = join(testDir, filename);
      writeFileSync(scriptPath, content);
      chmodSync(scriptPath, 0o755);
    });
  }

  function getHookOutput(): string {
    if (existsSync(hookOutputFile)) {
      return readFileSync(hookOutputFile, "utf8");
    }
    return "";
  }

  it("should execute command hooks during command execution", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "integration test"],
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
      "integration-test-session",
    );

    expect(result.outputText).toContain("integration test");
    expect(result.metadata.exit_code).toBe(0);

    // Check that command hooks were executed
    const output = getHookOutput();
    expect(output).toContain("COMMAND_START:echo integration test");
    expect(output).toContain("COMMAND_COMPLETE:echo integration test:0");
  });

  it("should execute hooks with proper filtering", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    // Test command that should trigger hooks (echo is in filter)
    const allowedExecInput = {
      cmd: ["echo", "allowed command"],
      workdir: testDir,
    };

    await handleExecCommand(
      allowedExecInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "filter-test-session",
    );

    const outputAfterAllowed = getHookOutput();
    expect(outputAfterAllowed).toContain("COMMAND_START:echo allowed command");

    // Clear output file
    writeFileSync(hookOutputFile, "");

    // Test command that should NOT trigger onCommandStart hook (not in filter)
    const blockedExecInput = {
      cmd: ["pwd"],
      workdir: testDir,
    };

    await handleExecCommand(
      blockedExecInput,
      testConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "filter-test-session-2",
    );

    const outputAfterBlocked = getHookOutput();
    expect(outputAfterBlocked).not.toContain("COMMAND_START:pwd");
    // But onCommandComplete should still execute (no filter)
    expect(outputAfterBlocked).toContain("COMMAND_COMPLETE:pwd:0");
  });

  it("should handle hook execution errors gracefully", async () => {
    // Create a failing hook
    const failingHookPath = join(testDir, "failing-hook.sh");
    const failingHookContent = `#!/bin/bash
echo "This hook will fail" >> "\${OUTPUT_FILE}"
exit 1
`;
    writeFileSync(failingHookPath, failingHookContent);
    chmodSync(failingHookPath, 0o755);

    const configWithFailingHook: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        hooks: {
          onCommandStart: {
            script: "./failing-hook.sh",
            async: false,
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(configWithFailingHook.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "test with failing hook"],
      workdir: testDir,
    };

    // Command should still succeed even if hook fails
    const result = await handleExecCommand(
      execInput,
      configWithFailingHook,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "failing-hook-session",
    );

    expect(result.outputText).toContain("test with failing hook");
    expect(result.metadata.exit_code).toBe(0);

    // Hook should have executed and failed
    const output = getHookOutput();
    expect(output).toContain("This hook will fail");

    // Clean up
    unlinkSync(failingHookPath);
  });

  it("should pass correct context data to hooks", async () => {
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "context test"],
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
      "context-test-session",
    );

    const output = getHookOutput();

    // Check that environment variables were set correctly
    expect(output).toContain("COMMAND_START:echo context test");
    expect(output).toContain("COMMAND_COMPLETE:echo context test:0");

    // Check that JSON event data was passed via STDIN
    expect(output).toContain('"command"');
    expect(output).toContain('"echo"');
    expect(output).toContain('"context test"');
    // exitCode should only be in the COMMAND_COMPLETE hook
    expect(output).toContain('"exitCode": 0');
    expect(output).toContain('"success": true');
  });

  it("should support async hook execution", async () => {
    const asyncConfig: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        hooks: {
          onCommandComplete: {
            script: "./command-complete-hook.sh",
            async: true, // Async execution
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(asyncConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "async test"],
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
      "async-test-session",
    );

    const endTime = Date.now();

    expect(result.outputText).toContain("async test");
    expect(result.metadata.exit_code).toBe(0);

    // Command should complete quickly even with async hook
    expect(endTime - startTime).toBeLessThan(5000);

    // Give async hook time to complete
    await new Promise(resolve => setTimeout(resolve, 1000));

    const output = getHookOutput();
    expect(output).toContain("COMMAND_COMPLETE:echo async test:0");
  });

  it("should handle multiple hooks of the same type", async () => {
    // Create additional hook script
    const additionalHookPath = join(testDir, "additional-hook.sh");
    const additionalHookContent = `#!/bin/bash
echo "ADDITIONAL_HOOK:\${CODEX_COMMAND}" >> "\${OUTPUT_FILE}"
`;
    writeFileSync(additionalHookPath, additionalHookContent);
    chmodSync(additionalHookPath, 0o755);

    // Note: Current implementation only supports one hook per type
    // This test documents the current behavior
    const hookExecutor = new HookExecutor(testConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "multiple hooks test"],
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
      "multiple-hooks-session",
    );

    const output = getHookOutput();
    expect(output).toContain("COMMAND_START:echo multiple hooks test");

    // Clean up
    unlinkSync(additionalHookPath);
  });

  it("should work when hooks are disabled", async () => {
    const disabledConfig: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        enabled: false,
      },
    };

    const hookExecutor = new HookExecutor(disabledConfig.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "disabled hooks test"],
      workdir: testDir,
    };

    const result = await handleExecCommand(
      execInput,
      disabledConfig,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "disabled-hooks-session",
    );

    expect(result.outputText).toContain("disabled hooks test");
    expect(result.metadata.exit_code).toBe(0);

    // No hooks should have executed
    const output = getHookOutput();
    expect(output).toBe("");
  });

  it("should handle missing hook scripts gracefully", async () => {
    const configWithMissingScript: AppConfig = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        hooks: {
          onCommandStart: {
            script: "./nonexistent-hook.sh",
            async: false,
          },
        },
      },
    };

    const hookExecutor = new HookExecutor(configWithMissingScript.lifecycleHooks!);

    const execInput = {
      cmd: ["echo", "missing script test"],
      workdir: testDir,
    };

    // Command should still succeed even if hook script is missing
    const result = await handleExecCommand(
      execInput,
      configWithMissingScript,
      "auto",
      [],
      async () => ({ review: "approve" as const }),
      undefined,
      hookExecutor,
      "missing-script-session",
    );

    expect(result.outputText).toContain("missing script test");
    expect(result.metadata.exit_code).toBe(0);
  });
});
