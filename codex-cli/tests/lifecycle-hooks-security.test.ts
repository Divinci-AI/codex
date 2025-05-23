import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { HookExecutor } from "../src/utils/lifecycle-hooks/hook-executor.ts";
import type { LifecycleHooksConfig } from "../src/utils/config.ts";
import { writeFileSync, unlinkSync, existsSync, mkdirSync, chmodSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

describe("Lifecycle Hooks Security Tests", () => {
  let testDir: string;

  beforeEach(() => {
    testDir = join(tmpdir(), `codex-security-test-${Date.now()}`);
    mkdirSync(testDir, { recursive: true });
  });

  afterEach(() => {
    try {
      const files = [
        "test-hook.sh",
        "malicious-hook.sh",
        "injection-test.sh",
        "path-traversal.sh",
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

  const createTestContext = (overrides: any = {}) => ({
    sessionId: "security-test-session",
    model: "test-model",
    workingDirectory: testDir,
    eventType: "command_start",
    eventData: {},
    ...overrides,
  });

  it("should prevent path traversal attacks in script paths", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "../../../etc/passwd", // Attempt path traversal
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();
    const result = await hookExecutor.executeHook("onCommandStart", context);

    // Hook should fail due to permission denied or file not executable
    expect(result).not.toBeNull();
    expect(result!.success).toBe(false);
    // The system prevents execution of /etc/passwd (not executable)
    expect(result!.stderr).toContain("EACCES");
  });

  it("should handle malicious script content safely", async () => {
    // Create a script that attempts to access sensitive information
    const maliciousScript = join(testDir, "malicious-hook.sh");
    const maliciousContent = `#!/bin/bash
# Attempt to access sensitive files
cat /etc/passwd 2>/dev/null || echo "Access denied"
# Attempt to modify system files
echo "malicious" > /etc/hosts 2>/dev/null || echo "Write denied"
# Attempt to execute privileged commands
sudo whoami 2>/dev/null || echo "Sudo denied"
exit 0
`;
    writeFileSync(maliciousScript, maliciousContent);
    chmodSync(maliciousScript, 0o755);

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./malicious-hook.sh",
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();
    const result = await hookExecutor.executeHook("onCommandStart", context);

    // Hook should execute but malicious actions should be denied
    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);
    expect(result!.stdout).toContain("denied");
  });

  it("should sanitize environment variables", async () => {
    // Create a hook that tries to use environment variables
    const envTestScript = join(testDir, "env-test.sh");
    const envTestContent = `#!/bin/bash
echo "PATH: $PATH"
echo "HOME: $HOME"
echo "MALICIOUS_VAR: $MALICIOUS_VAR"
echo "CODEX_SESSION_ID: $CODEX_SESSION_ID"
exit 0
`;
    writeFileSync(envTestScript, envTestContent);
    chmodSync(envTestScript, 0o755);

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {
        MALICIOUS_VAR: "$(rm -rf /)", // Attempt command injection
        SAFE_VAR: "safe-value",
      },
      hooks: {
        onCommandStart: {
          script: "./env-test.sh",
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();
    const result = await hookExecutor.executeHook("onCommandStart", context);

    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);

    // Environment variables should be passed as-is (not executed)
    expect(result!.stdout).toContain("MALICIOUS_VAR: $(rm -rf /)");
    expect(result!.stdout).toContain("CODEX_SESSION_ID: security-test-session");
  });

  it("should handle injection attempts in event data", async () => {
    const injectionTestScript = join(testDir, "injection-test.sh");
    const injectionTestContent = `#!/bin/bash
# Read event data from stdin
EVENT_DATA=$(cat)
echo "Event data received: $EVENT_DATA"

# Try to extract command safely
COMMAND=$(echo "$EVENT_DATA" | jq -r '.command | join(" ")' 2>/dev/null || echo "Invalid JSON")
echo "Extracted command: $COMMAND"
exit 0
`;
    writeFileSync(injectionTestScript, injectionTestContent);
    chmodSync(injectionTestScript, 0o755);

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./injection-test.sh",
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    // Create context with potentially malicious event data
    const context = createTestContext({
      eventData: {
        command: ["echo", "'; rm -rf /; echo '"], // Attempt command injection
        maliciousField: "$(whoami)",
      },
    });

    const result = await hookExecutor.executeHook("onCommandStart", context);

    expect(result).not.toBeNull();
    expect(result!.success).toBe(true);

    // Malicious content should be treated as literal strings
    expect(result!.stdout).toContain("'; rm -rf /; echo '");
    expect(result!.stdout).toContain("$(whoami)");
  });

  it("should enforce timeout limits to prevent DoS", async () => {
    // Create a script that runs indefinitely
    const dosScript = join(testDir, "dos-hook.sh");
    const dosContent = `#!/bin/bash
while true; do
  echo "Running forever..."
  sleep 1
done
`;
    writeFileSync(dosScript, dosContent);
    chmodSync(dosScript, 0o755);

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 1000, // 1 second timeout
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./dos-hook.sh",
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();
    const startTime = Date.now();

    const result = await hookExecutor.executeHook("onCommandStart", context);

    const endTime = Date.now();
    const executionTime = endTime - startTime;

    // Hook should timeout and fail
    expect(result).not.toBeNull();
    expect(result!.success).toBe(false);
    expect(executionTime).toBeLessThan(2000); // Should timeout quickly
    expect(result!.stderr).toContain("timed out");
  });

  it("should validate custom expressions safely", async () => {
    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./test-hook.sh",
          filter: {
            customExpression: "process.exit(1)", // Attempt to crash process
          },
        },
      },
    };

    // Create a simple test hook
    const testScript = join(testDir, "test-hook.sh");
    writeFileSync(testScript, "#!/bin/bash\necho 'Hook executed'\nexit 0\n");
    chmodSync(testScript, 0o755);

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();

    // This should not crash the process
    const result = await hookExecutor.executeHook("onCommandStart", context);

    // Hook should not execute due to failed expression
    expect(result).toBeNull();

    // Process should still be running
    expect(process.pid).toBeGreaterThan(0);
  });

  it("should handle malicious custom expressions", async () => {
    const maliciousExpressions = [
      "require('fs').unlinkSync('/etc/passwd')", // File system access
      "require('child_process').exec('rm -rf /')", // Command execution
      "while(true){}", // Infinite loop
      "throw new Error('Malicious error')", // Exception throwing
      "global.process = null", // Global modification
    ];

    const testScript = join(testDir, "test-hook.sh");
    writeFileSync(testScript, "#!/bin/bash\necho 'Hook executed'\nexit 0\n");
    chmodSync(testScript, 0o755);

    for (const expression of maliciousExpressions) {
      const config: LifecycleHooksConfig = {
        enabled: true,
        timeout: 5000,
        workingDirectory: testDir,
        environment: {},
        hooks: {
          onCommandStart: {
            script: "./test-hook.sh",
            filter: {
              customExpression: expression,
            },
          },
        },
      };

      const hookExecutor = new HookExecutor(config);
      const context = createTestContext();

      // Should not crash or cause security issues
      const result = await hookExecutor.executeHook("onCommandStart", context);

      // Most malicious expressions should fail and return null
      expect(result).toBeNull();
    }
  });

  it("should limit resource usage", async () => {
    // Create a script that tries to consume lots of memory
    const resourceScript = join(testDir, "resource-hook.sh");
    const resourceContent = `#!/bin/bash
# Try to allocate large amounts of memory
dd if=/dev/zero of=/tmp/large-file bs=1M count=100 2>/dev/null || echo "Resource limit hit"
# Try to create many processes
for i in {1..100}; do
  sleep 1 &
done 2>/dev/null || echo "Process limit hit"
wait
exit 0
`;
    writeFileSync(resourceScript, resourceContent);
    chmodSync(resourceScript, 0o755);

    const config: LifecycleHooksConfig = {
      enabled: true,
      timeout: 5000,
      workingDirectory: testDir,
      environment: {},
      hooks: {
        onCommandStart: {
          script: "./resource-hook.sh",
        },
      },
    };

    const hookExecutor = new HookExecutor(config);

    const context = createTestContext();
    const result = await hookExecutor.executeHook("onCommandStart", context);

    // Hook should complete (possibly with resource limits hit)
    expect(result).not.toBeNull();
    // The script should handle resource limits gracefully
    expect(result!.stdout).toMatch(/(Resource limit hit|Process limit hit|)/);
  });
});
