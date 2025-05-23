import type { LifecycleHooksConfig, LifecycleHookConfig } from "../config.js";

import { log } from "../logger/log.js";
import { spawn, type SpawnOptions } from "child_process";
import { existsSync } from "fs";
import { resolve as resolvePath, isAbsolute } from "path";


/**
 * Context information passed to lifecycle hooks.
 */
export interface HookContext {
  /** Unique session identifier */
  sessionId: string;
  /** AI model being used */
  model: string;
  /** Current working directory */
  workingDirectory: string;
  /** Type of event that triggered the hook */
  eventType: string;
  /** Additional context data specific to the event */
  eventData: Record<string, unknown>;
}

/**
 * Result of executing a lifecycle hook.
 */
export interface HookResult {
  /** Whether the hook executed successfully */
  success: boolean;
  /** Exit code from the hook script */
  exitCode: number;
  /** Standard output from the hook script */
  stdout: string;
  /** Standard error from the hook script */
  stderr: string;
  /** Execution duration in milliseconds */
  duration: number;
  /** Error message if execution failed */
  error?: string;
}

/**
 * Standard environment variables provided to all hooks.
 */
export interface HookEnvironment {
  /** Type of event that triggered the hook */
  CODEX_EVENT_TYPE: string;
  /** Unique session identifier */
  CODEX_SESSION_ID: string;
  /** AI model being used */
  CODEX_MODEL: string;
  /** Current working directory */
  CODEX_WORKING_DIR: string;
  /** Hook execution timeout in milliseconds */
  CODEX_TIMEOUT: string;
  /** Additional custom environment variables */
  [key: string]: string;
}

/**
 * Core engine for executing lifecycle hook scripts.
 */
export class HookExecutor {
  constructor(private config: LifecycleHooksConfig) {}

  /**
   * Execute a specific lifecycle hook if it exists and passes filters.
   */
  async executeHook(
    hookName: keyof LifecycleHooksConfig["hooks"],
    context: HookContext,
  ): Promise<HookResult | null> {
    if (!this.config.enabled) {
      return null;
    }

    const hookConfig = this.config.hooks[hookName];
    if (!hookConfig) {
      return null;
    }

    // Apply filters to determine if hook should execute
    if (!this.shouldExecuteHook(hookConfig, context)) {
      log(`[hooks] Skipping ${hookName} - filters not matched`);
      return null;
    }

    log(`[hooks] Executing ${hookName}: ${hookConfig.script}`);
    return this.executeScript(hookConfig, context);
  }

  /**
   * Execute multiple hooks for a given event type.
   */
  async executeHooksForEvent(
    eventType: string,
    context: Omit<HookContext, "eventType">,
  ): Promise<Array<HookResult>> {
    const fullContext: HookContext = { ...context, eventType };
    const results: Array<HookResult> = [];

    // Map event types to hook names
    const hookMapping: Record<string, keyof LifecycleHooksConfig["hooks"]> = {
      task_start: "onTaskStart",
      task_complete: "onTaskComplete",
      task_error: "onTaskError",
      command_start: "onCommandStart",
      command_complete: "onCommandComplete",
      patch_apply: "onPatchApply",
      agent_message: "onAgentMessage",
      agent_reasoning: "onAgentReasoning",
      mcp_tool_call: "onMcpToolCall",
    };

    const hookName = hookMapping[eventType];
    if (hookName) {
      const result = await this.executeHook(hookName, fullContext);
      if (result) {
        results.push(result);
      }
    }

    return results;
  }

  /**
   * Check if a hook should execute based on its filters.
   */
  private shouldExecuteHook(
    hookConfig: LifecycleHookConfig,
    context: HookContext,
  ): boolean {
    const filter = hookConfig.filter;
    if (!filter) {
      return true; // No filters means always execute
    }

    // Command filtering
    if (filter.commands && context.eventData?.command) {
      const command = Array.isArray(context.eventData.command)
        ? context.eventData.command.join(" ")
        : context.eventData.command;

      const matches = filter.commands.some((pattern) => {
        // Support both exact matches and regex patterns
        if (pattern.startsWith("/") && pattern.endsWith("/")) {
          const regex = new RegExp(pattern.slice(1, -1));
          return regex.test(command);
        }
        return command.includes(pattern);
      });

      if (!matches) {
        return false;
      }
    }

    // Exit code filtering (for command completion hooks)
    if (filter.exitCodes && context.eventData?.exitCode !== undefined) {
      if (!filter.exitCodes.includes(context.eventData.exitCode)) {
        return false;
      }
    }

    // Message type filtering (for agent hooks)
    if (filter.messageTypes && context.eventData?.messageType) {
      if (!filter.messageTypes.includes(context.eventData.messageType)) {
        return false;
      }
    }

    // Working directory filtering
    if (filter.workingDirectories && context.workingDirectory) {
      const matches = filter.workingDirectories.some((pattern) => {
        // Simple glob-like matching (could be enhanced with a proper glob library)
        if (pattern.includes("*")) {
          const regex = new RegExp(
            pattern.replace(/\*/g, ".*").replace(/\?/g, "."),
          );
          return regex.test(context.workingDirectory);
        }
        return context.workingDirectory.includes(pattern);
      });

      if (!matches) {
        return false;
      }
    }

    // File extension filtering (for patch hooks)
    if (filter.fileExtensions && context.eventData?.files) {
      const files = Array.isArray(context.eventData.files)
        ? context.eventData.files
        : [context.eventData.files];

      const hasMatchingExtension = files.some((file: string) => {
        const ext = file.split('.').pop()?.toLowerCase();
        return ext && filter.fileExtensions!.includes(ext);
      });

      if (!hasMatchingExtension) {
        return false;
      }
    }

    // Duration range filtering
    if (filter.durationRange && context.eventData?.durationMs !== undefined) {
      const duration = context.eventData.durationMs;
      if (filter.durationRange.min !== undefined && duration < filter.durationRange.min) {
        return false;
      }
      if (filter.durationRange.max !== undefined && duration > filter.durationRange.max) {
        return false;
      }
    }

    // Time range filtering
    if (filter.timeRange) {
      const now = new Date();

      // Check day of week
      if (filter.timeRange.daysOfWeek) {
        const dayOfWeek = now.getDay();
        if (!filter.timeRange.daysOfWeek.includes(dayOfWeek)) {
          return false;
        }
      }

      // Check time range
      if (filter.timeRange.start || filter.timeRange.end) {
        const currentTime = now.getHours() * 60 + now.getMinutes();

        if (filter.timeRange.start) {
          const [startHour, startMin] = filter.timeRange.start.split(':').map(Number);
          const startTime = startHour * 60 + startMin;
          if (currentTime < startTime) {
            return false;
          }
        }

        if (filter.timeRange.end) {
          const [endHour, endMin] = filter.timeRange.end.split(':').map(Number);
          const endTime = endHour * 60 + endMin;
          if (currentTime > endTime) {
            return false;
          }
        }
      }
    }

    // Environment variable filtering
    if (filter.environment) {
      for (const [envVar, expectedValue] of Object.entries(filter.environment)) {
        const actualValue = process.env[envVar];

        if (typeof expectedValue === 'string') {
          if (actualValue !== expectedValue) {
            return false;
          }
        } else if (expectedValue instanceof RegExp) {
          if (!actualValue || !expectedValue.test(actualValue)) {
            return false;
          }
        }
      }
    }

    // Custom expression filtering
    if (filter.customExpression) {
      try {
        // Create a safe evaluation context
        const evalContext = {
          context,
          eventData: context.eventData,
          command: context.eventData?.command,
          exitCode: context.eventData?.exitCode,
          workingDirectory: context.workingDirectory,
          sessionId: context.sessionId,
          model: context.model,
          env: process.env,
          Date,
          Math,
          RegExp,
        };

        // Use Function constructor for safer evaluation than eval()
        const func = new Function(
          'context', 'eventData', 'command', 'exitCode', 'workingDirectory',
          'sessionId', 'model', 'env', 'Date', 'Math', 'RegExp',
          `return (${filter.customExpression});`
        );

        const result = func(
          evalContext.context,
          evalContext.eventData,
          evalContext.command,
          evalContext.exitCode,
          evalContext.workingDirectory,
          evalContext.sessionId,
          evalContext.model,
          evalContext.env,
          evalContext.Date,
          evalContext.Math,
          evalContext.RegExp,
        );

        if (!result) {
          return false;
        }
      } catch (error) {
        log(`[hooks] Error evaluating custom expression: ${error}`);
        return false;
      }
    }

    return true;
  }

  /**
   * Execute a hook script with the given context.
   */
  private async executeScript(
    hookConfig: LifecycleHookConfig,
    context: HookContext,
  ): Promise<HookResult> {
    const startTime = Date.now();

    try {
      // Resolve script path
      const scriptPath = this.resolveScriptPath(hookConfig.script);
      if (!existsSync(scriptPath)) {
        return {
          success: false,
          exitCode: 1,
          stdout: "",
          stderr: `Hook script not found: ${scriptPath}`,
          duration: Date.now() - startTime,
          error: `Script file does not exist: ${scriptPath}`,
        };
      }

      // Prepare environment variables
      const environment = this.buildEnvironment(hookConfig, context);

      // Prepare spawn options
      const timeout =
        hookConfig.timeout ?? this.config.timeout ?? 30000;
      const workingDirectory = this.resolveWorkingDirectory();

      const spawnOptions: SpawnOptions = {
        cwd: workingDirectory,
        env: { ...process.env, ...environment },
        stdio: ["pipe", "pipe", "pipe"],
      };

      // Determine command and arguments
      const { command, args } = this.parseScriptCommand(scriptPath);

      // Execute the script
      const result = await this.spawnProcess(
        command,
        args,
        spawnOptions,
        JSON.stringify(context.eventData, null, 2),
        timeout,
      );

      const duration = Date.now() - startTime;

      log(
        `[hooks] Hook ${hookConfig.script} completed in ${duration}ms with exit code ${result.exitCode}`,
      );

      return {
        success: result.exitCode === 0,
        exitCode: result.exitCode,
        stdout: result.stdout,
        stderr: result.stderr,
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      log(`[hooks] Hook ${hookConfig.script} failed: ${errorMessage}`);

      return {
        success: false,
        exitCode: 1,
        stdout: "",
        stderr: errorMessage,
        duration,
        error: errorMessage,
      };
    }
  }

  /**
   * Resolve the absolute path to a hook script.
   */
  private resolveScriptPath(scriptPath: string): string {
    if (isAbsolute(scriptPath)) {
      return scriptPath;
    }

    const workingDirectory = this.resolveWorkingDirectory();
    return resolvePath(workingDirectory, scriptPath);
  }

  /**
   * Resolve the working directory for hook execution.
   */
  private resolveWorkingDirectory(): string {
    const configWorkingDir = this.config.workingDirectory;
    if (isAbsolute(configWorkingDir)) {
      return configWorkingDir;
    }

    return resolvePath(process.cwd(), configWorkingDir);
  }

  /**
   * Build environment variables for hook execution.
   */
  private buildEnvironment(
    hookConfig: LifecycleHookConfig,
    context: HookContext,
  ): HookEnvironment {
    const baseEnv: HookEnvironment = {
      CODEX_EVENT_TYPE: context.eventType,
      CODEX_SESSION_ID: context.sessionId,
      CODEX_MODEL: context.model,
      CODEX_WORKING_DIR: context.workingDirectory,
      CODEX_TIMEOUT: String(
        hookConfig.timeout ?? this.config.timeout ?? 30000,
      ),
    };

    // Add global environment variables from config
    Object.assign(baseEnv, this.config.environment);

    // Add hook-specific environment variables
    if (hookConfig.environment) {
      Object.assign(baseEnv, hookConfig.environment);
    }

    // Add event-specific environment variables
    if (context.eventData) {
      if (context.eventData.command) {
        baseEnv.CODEX_COMMAND = Array.isArray(context.eventData.command)
          ? context.eventData.command.join(" ")
          : context.eventData.command;
      }
      if (context.eventData.exitCode !== undefined) {
        baseEnv.CODEX_EXIT_CODE = String(context.eventData.exitCode);
      }
      if (context.eventData.callId) {
        baseEnv.CODEX_CALL_ID = context.eventData.callId;
      }
    }

    // Perform variable interpolation
    return this.interpolateVariables(baseEnv);
  }

  /**
   * Perform variable interpolation on environment variables.
   */
  private interpolateVariables(env: HookEnvironment): HookEnvironment {
    const interpolated = { ...env };

    // Simple variable interpolation for ${VAR} patterns
    Object.keys(interpolated).forEach((key) => {
      let value = interpolated[key];
      const matches = value.match(/\$\{([^}]+)\}/g);

      if (matches) {
        matches.forEach((match) => {
          const varName = match.slice(2, -1); // Remove ${ and }
          const replacement = process.env[varName] || interpolated[varName] || "";
          value = value.replace(match, replacement);
        });
        interpolated[key] = value;
      }
    });

    return interpolated;
  }

  /**
   * Parse script command to determine executable and arguments.
   */
  private parseScriptCommand(scriptPath: string): { command: string; args: Array<string> } {
    const extension = scriptPath.split(".").pop()?.toLowerCase();

    switch (extension) {
      case "sh":
      case "bash":
        return { command: "bash", args: [scriptPath] };
      case "py":
        return { command: "python3", args: [scriptPath] };
      case "js":
        return { command: "node", args: [scriptPath] };
      case "ts":
        return { command: "npx", args: ["ts-node", scriptPath] };
      default:
        // Assume it's executable
        return { command: scriptPath, args: [] };
    }
  }

  /**
   * Spawn a process and return the result.
   */
  private spawnProcess(
    command: string,
    args: Array<string>,
    options: SpawnOptions,
    stdinData?: string,
    timeout?: number,
  ): Promise<{ exitCode: number; stdout: string; stderr: string }> {
    return new Promise((resolve) => {
      const child = spawn(command, args, options);

      let stdout = "";
      let stderr = "";
      let timeoutId: NodeJS.Timeout | null = null;
      let isResolved = false;

      // Set up timeout if specified
      if (timeout && timeout > 0) {
        timeoutId = setTimeout(() => {
          if (!isResolved) {
            isResolved = true;
            child.kill('SIGTERM');
            resolve({
              exitCode: 1,
              stdout: stdout.trim(),
              stderr: (stderr + '\nProcess timed out').trim(),
            });
          }
        }, timeout);
      }

      if (child.stdout) {
        child.stdout.on("data", (data) => {
          stdout += data.toString();
        });
      }

      if (child.stderr) {
        child.stderr.on("data", (data) => {
          stderr += data.toString();
        });
      }

      // Send event data to stdin if provided
      if (stdinData && child.stdin) {
        try {
          child.stdin.write(stdinData);
          child.stdin.end();
        } catch (error) {
          // Ignore EPIPE errors - the process may have already exited
          // This is common when the process exits quickly
        }
      }

      // Handle stdin errors to prevent unhandled exceptions
      if (child.stdin) {
        child.stdin.on('error', () => {
          // Ignore stdin errors (like EPIPE) - they're common when processes exit quickly
        });
      }

      child.on("close", (code) => {
        if (!isResolved) {
          isResolved = true;
          if (timeoutId) {
            clearTimeout(timeoutId);
          }
          resolve({
            exitCode: code ?? 1,
            stdout: stdout.trim(),
            stderr: stderr.trim(),
          });
        }
      });

      child.on("error", (error) => {
        if (!isResolved) {
          isResolved = true;
          if (timeoutId) {
            clearTimeout(timeoutId);
          }
          resolve({
            exitCode: 1,
            stdout: "",
            stderr: error.message,
          });
        }
      });
    });
  }
}
