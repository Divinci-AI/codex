import { describe, it, expect, afterEach } from "vitest";
import {
  DEFAULT_LIFECYCLE_HOOKS_CONFIG,
  loadConfig,
} from "../src/utils/config.js";
import { writeFileSync, unlinkSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Lifecycle Hooks Configuration", () => {
  const testConfigPath = join(tmpdir(), "test-codex-config.json");
  const testInstructionsPath = join(tmpdir(), "test-instructions.md");

  afterEach(() => {
    // Clean up test files
    if (existsSync(testConfigPath)) {
      unlinkSync(testConfigPath);
    }
    if (existsSync(testInstructionsPath)) {
      unlinkSync(testInstructionsPath);
    }
  });

  it("should have correct default lifecycle hooks configuration", () => {
    expect(DEFAULT_LIFECYCLE_HOOKS_CONFIG).toEqual({
      enabled: false,
      timeout: 30000,
      workingDirectory: ".",
      environment: {},
      hooks: {},
    });
  });

  it("should load default configuration when no lifecycle hooks are specified", () => {
    const config = {
      model: "test-model",
    };

    writeFileSync(testConfigPath, JSON.stringify(config, null, 2));
    writeFileSync(testInstructionsPath, "");

    const loadedConfig = loadConfig(testConfigPath, testInstructionsPath, {
      disableProjectDoc: true,
    });

    expect(loadedConfig.lifecycleHooks).toEqual(DEFAULT_LIFECYCLE_HOOKS_CONFIG);
  });

  it("should merge user lifecycle hooks configuration with defaults", () => {
    const config = {
      model: "test-model",
      lifecycleHooks: {
        enabled: true,
        timeout: 60000,
        hooks: {
          onTaskStart: {
            script: "./hooks/task-start.sh",
            async: false,
          },
          onTaskComplete: {
            script: "./hooks/task-complete.sh",
            async: true,
            filter: {
              commands: ["git", "npm"],
            },
          },
        },
      },
    };

    writeFileSync(testConfigPath, JSON.stringify(config, null, 2));
    writeFileSync(testInstructionsPath, "");

    const loadedConfig = loadConfig(testConfigPath, testInstructionsPath, {
      disableProjectDoc: true,
    });

    expect(loadedConfig.lifecycleHooks?.enabled).toBe(true);
    expect(loadedConfig.lifecycleHooks?.timeout).toBe(60000);
    expect(loadedConfig.lifecycleHooks?.workingDirectory).toBe(".");
    expect(loadedConfig.lifecycleHooks?.hooks.onTaskStart).toEqual({
      script: "./hooks/task-start.sh",
      async: false,
    });
    expect(loadedConfig.lifecycleHooks?.hooks.onTaskComplete).toEqual({
      script: "./hooks/task-complete.sh",
      async: true,
      filter: {
        commands: ["git", "npm"],
      },
    });
  });

  it("should validate hook configurations and remove invalid ones", () => {
    const config = {
      model: "test-model",
      lifecycleHooks: {
        enabled: true,
        hooks: {
          onTaskStart: {
            script: "./hooks/valid-hook.sh",
          },
          onTaskComplete: {
            // Missing required 'script' property
            async: true,
          },
        },
      },
    };

    writeFileSync(testConfigPath, JSON.stringify(config, null, 2));
    writeFileSync(testInstructionsPath, "");

    const loadedConfig = loadConfig(testConfigPath, testInstructionsPath, {
      disableProjectDoc: true,
    });

    expect(loadedConfig.lifecycleHooks?.hooks.onTaskStart).toEqual({
      script: "./hooks/valid-hook.sh",
    });
    expect(loadedConfig.lifecycleHooks?.hooks.onTaskComplete).toBeUndefined();
  });

  it("should handle invalid timeout values", () => {
    const config = {
      model: "test-model",
      lifecycleHooks: {
        enabled: true,
        timeout: -1000, // Invalid negative timeout
        hooks: {
          onTaskStart: {
            script: "./hooks/task-start.sh",
          },
        },
      },
    };

    writeFileSync(testConfigPath, JSON.stringify(config, null, 2));
    writeFileSync(testInstructionsPath, "");

    const loadedConfig = loadConfig(testConfigPath, testInstructionsPath, {
      disableProjectDoc: true,
    });

    // Should fall back to default timeout
    expect(loadedConfig.lifecycleHooks?.timeout).toBe(
      DEFAULT_LIFECYCLE_HOOKS_CONFIG.timeout,
    );
  });

  it("should support YAML configuration format", () => {
    const yamlConfigPath = join(tmpdir(), "test-codex-config.yaml");
    const yamlConfig = `
model: test-model
lifecycleHooks:
  enabled: true
  timeout: 45000
  environment:
    CUSTOM_VAR: "test-value"
  hooks:
    onTaskStart:
      script: "./hooks/start.sh"
      async: false
    onCommandComplete:
      script: "./hooks/command-done.py"
      async: true
      filter:
        commands:
          - "git"
          - "npm"
        exitCodes:
          - 0
`;

    writeFileSync(yamlConfigPath, yamlConfig);
    writeFileSync(testInstructionsPath, "");

    const loadedConfig = loadConfig(yamlConfigPath, testInstructionsPath, {
      disableProjectDoc: true,
    });

    expect(loadedConfig.lifecycleHooks?.enabled).toBe(true);
    expect(loadedConfig.lifecycleHooks?.timeout).toBe(45000);
    expect(loadedConfig.lifecycleHooks?.environment).toEqual({
      CUSTOM_VAR: "test-value",
    });
    expect(loadedConfig.lifecycleHooks?.hooks.onTaskStart?.script).toBe(
      "./hooks/start.sh",
    );
    expect(loadedConfig.lifecycleHooks?.hooks.onCommandComplete?.filter).toEqual({
      commands: ["git", "npm"],
      exitCodes: [0],
    });

    // Clean up
    unlinkSync(yamlConfigPath);
  });
});
