import { log } from "../logger/log.js";
import type { AppConfig } from "../config.js";
import type { 
  LifecycleEvent, 
  HookExecutionResult,
  SessionStartEvent,
  SessionEndEvent,
  TaskStartEvent,
  TaskEndEvent,
  CommandStartEvent,
  CommandEndEvent,
  ErrorEvent
} from "./types.js";

/**
 * Emit a lifecycle event to the hook system
 */
export async function emitLifecycleEvent(
  event: LifecycleEvent,
  config?: AppConfig
): Promise<HookExecutionResult | null> {
  // Check if hooks are enabled
  if (!config?.hooks?.enabled) {
    return null;
  }

  try {
    log(`[hooks] Emitting lifecycle event: ${event.type}`);
    
    // For now, we'll just log the event
    // In the future, this will integrate with the Rust hook system
    log(`[hooks] Event data: ${JSON.stringify(event, null, 2)}`);
    
    // TODO: Integrate with Rust hook execution system
    // This would involve calling the Rust binary or using FFI
    
    return {
      success: true,
      results: [],
      errors: []
    };
  } catch (error) {
    log(`[hooks] Error emitting lifecycle event: ${error}`);
    return {
      success: false,
      results: [],
      errors: [error instanceof Error ? error.message : String(error)]
    };
  }
}

/**
 * Create a session start event
 */
export function createSessionStartEvent(
  sessionId: string,
  model: string,
  provider?: string
): SessionStartEvent {
  return {
    type: "session_start",
    sessionId,
    model,
    provider,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a session end event
 */
export function createSessionEndEvent(
  sessionId: string,
  duration?: number
): SessionEndEvent {
  return {
    type: "session_end",
    sessionId,
    duration,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a task start event
 */
export function createTaskStartEvent(
  sessionId: string,
  taskId: string,
  prompt: string
): TaskStartEvent {
  return {
    type: "task_start",
    sessionId,
    taskId,
    prompt,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a task end event
 */
export function createTaskEndEvent(
  sessionId: string,
  taskId: string,
  success: boolean,
  duration?: number
): TaskEndEvent {
  return {
    type: "task_end",
    sessionId,
    taskId,
    success,
    duration,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a command start event
 */
export function createCommandStartEvent(
  sessionId: string,
  command: string[],
  workdir?: string
): CommandStartEvent {
  return {
    type: "command_start",
    sessionId,
    command,
    workdir,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create a command end event
 */
export function createCommandEndEvent(
  sessionId: string,
  command: string[],
  exitCode: number,
  duration?: number
): CommandEndEvent {
  return {
    type: "command_end",
    sessionId,
    command,
    exitCode,
    duration,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create an error event
 */
export function createErrorEvent(
  sessionId: string,
  error: string,
  context?: string
): ErrorEvent {
  return {
    type: "error",
    sessionId,
    error,
    context,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Display hook execution status in CLI output
 */
export function displayHookStatus(result: HookExecutionResult): void {
  if (!result.success && result.errors.length > 0) {
    log(`[hooks] Hook execution failed: ${result.errors.join(", ")}`);
  } else if (result.results.length > 0) {
    log(`[hooks] Executed ${result.results.length} hooks successfully`);
  }
}
