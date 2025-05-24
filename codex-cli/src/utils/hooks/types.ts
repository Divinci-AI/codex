// Lifecycle event types for client-side hook integration
export interface LifecycleEvent {
  type: string;
  sessionId: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

export interface SessionStartEvent extends LifecycleEvent {
  type: "session_start";
  model: string;
  provider?: string;
}

export interface SessionEndEvent extends LifecycleEvent {
  type: "session_end";
  duration?: number;
}

export interface TaskStartEvent extends LifecycleEvent {
  type: "task_start";
  taskId: string;
  prompt: string;
}

export interface TaskEndEvent extends LifecycleEvent {
  type: "task_end";
  taskId: string;
  success: boolean;
  duration?: number;
}

export interface CommandStartEvent extends LifecycleEvent {
  type: "command_start";
  command: string[];
  workdir?: string;
}

export interface CommandEndEvent extends LifecycleEvent {
  type: "command_end";
  command: string[];
  exitCode: number;
  duration?: number;
}

export interface ErrorEvent extends LifecycleEvent {
  type: "error";
  error: string;
  context?: string;
}

// Hook execution status
export interface HookExecutionStatus {
  hookId: string;
  status: "pending" | "running" | "success" | "error" | "timeout";
  startTime: number;
  endTime?: number;
  error?: string;
  output?: string;
}

// Hook execution result
export interface HookExecutionResult {
  success: boolean;
  results: HookExecutionStatus[];
  errors: string[];
}
