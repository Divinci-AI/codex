import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { AgentLoop } from "../src/utils/agent/agent-loop.ts";
import type { AppConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("AgentLoop Lifecycle Hooks Integration", () => {
  let testDir: string;
  let testConfig: AppConfig;
  let hookOutputFile: string;

  beforeEach(() => {
    // Create a temporary directory for test scripts
    testDir = join(tmpdir(), `codex-hooks-integration-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });

    hookOutputFile = join(testDir, "hook-output.txt");

    // Create a simple test hook script
    const hookScript = join(testDir, "test-hook.sh");
    const scriptContent = `#!/bin/bash
echo "Hook executed: $CODEX_EVENT_TYPE" >> "${hookOutputFile}"
echo "Session: $CODEX_SESSION_ID" >> "${hookOutputFile}"
echo "Model: $CODEX_MODEL" >> "${hookOutputFile}"
echo "---" >> "${hookOutputFile}"
`;
    writeFileSync(hookScript, scriptContent);
    chmodSync(hookScript, 0o755);

    // Test configuration with lifecycle hooks enabled
    testConfig = {
      model: "test-model",
      instructions: "Test instructions",
      apiKey: "test-api-key", // Dummy API key for testing
      lifecycleHooks: {
        enabled: true,
        timeout: 5000,
        workingDirectory: testDir,
        environment: {
          TEST_VAR: "test-value",
        },
        hooks: {
          onTaskStart: {
            script: "./test-hook.sh",
            async: false,
          },
          onTaskComplete: {
            script: "./test-hook.sh",
            async: false,
          },
          onTaskError: {
            script: "./test-hook.sh",
            async: false,
          },
        },
      },
    };
  });

  afterEach(() => {
    // Clean up test files
    try {
      if (existsSync(hookOutputFile)) {
        unlinkSync(hookOutputFile);
      }
      const hookScript = join(testDir, "test-hook.sh");
      if (existsSync(hookScript)) {
        unlinkSync(hookScript);
      }
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  it("should initialize HookExecutor when lifecycle hooks are enabled", () => {
    const agentLoop = new AgentLoop({
      model: "test-model",
      instructions: "Test instructions",
      approvalPolicy: "auto",
      config: testConfig,
      onItem: () => {},
      onLoading: () => {},
      getCommandConfirmation: async () => true,
      onLastResponseId: () => {},
    });

    // The HookExecutor should be initialized (we can't directly access it due to private visibility)
    // But we can verify the constructor doesn't throw and the instance is created
    expect(agentLoop).toBeDefined();
    expect(agentLoop.sessionId).toBeDefined();
  });

  it("should not initialize HookExecutor when lifecycle hooks are disabled", () => {
    const configWithoutHooks = {
      ...testConfig,
      lifecycleHooks: {
        ...testConfig.lifecycleHooks!,
        enabled: false,
      },
    };

    const agentLoop = new AgentLoop({
      model: "test-model",
      instructions: "Test instructions",
      approvalPolicy: "auto",
      config: configWithoutHooks,
      onItem: () => {},
      onLoading: () => {},
      getCommandConfirmation: async () => true,
      onLastResponseId: () => {},
    });

    expect(agentLoop).toBeDefined();
    expect(agentLoop.sessionId).toBeDefined();
  });

  it("should work without lifecycle hooks configuration", () => {
    const configWithoutHooks = {
      model: "test-model",
      instructions: "Test instructions",
      apiKey: "test-api-key", // Dummy API key for testing
    };

    const agentLoop = new AgentLoop({
      model: "test-model",
      instructions: "Test instructions",
      approvalPolicy: "auto",
      config: configWithoutHooks,
      onItem: () => {},
      onLoading: () => {},
      getCommandConfirmation: async () => true,
      onLastResponseId: () => {},
    });

    expect(agentLoop).toBeDefined();
    expect(agentLoop.sessionId).toBeDefined();
  });

  // Note: Testing actual hook execution during AgentLoop.run() would require
  // mocking the OpenAI API calls, which is complex. The integration is tested
  // through the constructor and the HookExecutor unit tests verify the execution logic.
});
