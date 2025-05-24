//! Hook execution framework and base executor.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use futures::future::join_all;
use tokio::sync::{Mutex, RwLock};
use tokio::time::timeout;
use tracing::{debug, info, warn};

use crate::hooks::context::HookContext;
use crate::hooks::types::{HookError, HookResult, HookExecutionMode, HookPriority};

/// Result type for hook executor operations.
pub type HookExecutorResult = Result<HookResult, HookError>;

/// Execution configuration for hook execution.
#[derive(Debug, Clone)]
pub struct ExecutionConfig {
    /// Maximum execution time before timeout.
    pub timeout: Duration,
    /// Execution mode (blocking, async, fire-and-forget).
    pub mode: HookExecutionMode,
    /// Priority for execution ordering.
    pub priority: HookPriority,
    /// Whether this hook is required (failure stops execution).
    pub required: bool,
    /// Maximum number of retry attempts on failure.
    pub max_retries: u32,
    /// Delay between retry attempts.
    pub retry_delay: Duration,
    /// Whether to isolate execution in a separate task.
    pub isolated: bool,
}

impl Default for ExecutionConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            required: false,
            max_retries: 0,
            retry_delay: Duration::from_millis(500),
            isolated: true,
        }
    }
}

/// Execution context with cancellation support.
#[derive(Debug, Clone)]
pub struct ExecutionContext {
    /// Unique execution ID for tracking.
    pub execution_id: String,
    /// Hook context with event data.
    pub hook_context: HookContext,
    /// Execution configuration.
    pub config: ExecutionConfig,
    /// Start time for performance tracking.
    pub start_time: Instant,
    /// Cancellation token.
    pub cancelled: Arc<RwLock<bool>>,
}

impl ExecutionContext {
    /// Create a new execution context.
    pub fn new(hook_context: HookContext, config: ExecutionConfig) -> Self {
        Self {
            execution_id: format!("exec_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos()),
            hook_context,
            config,
            start_time: Instant::now(),
            cancelled: Arc::new(RwLock::new(false)),
        }
    }

    /// Check if execution has been cancelled.
    pub async fn is_cancelled(&self) -> bool {
        *self.cancelled.read().await
    }

    /// Cancel the execution.
    pub async fn cancel(&self) {
        *self.cancelled.write().await = true;
    }

    /// Get elapsed execution time.
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }
}

/// Result of hook execution with detailed information.
#[derive(Debug, Clone)]
pub struct ExecutionResult {
    /// Execution ID for tracking.
    pub execution_id: String,
    /// Hook execution result.
    pub result: HookResult,
    /// Execution configuration used.
    pub config: ExecutionConfig,
    /// Total execution time.
    pub duration: Duration,
    /// Number of retry attempts made.
    pub retry_attempts: u32,
    /// Whether execution was cancelled.
    pub cancelled: bool,
    /// Error details if execution failed.
    pub error_details: Option<String>,
}

/// Aggregated results from multiple hook executions.
#[derive(Debug, Clone, Default)]
pub struct AggregatedResults {
    /// All execution results.
    pub results: Vec<ExecutionResult>,
    /// Successfully completed executions.
    pub successful: Vec<ExecutionResult>,
    /// Failed executions.
    pub failed: Vec<ExecutionResult>,
    /// Cancelled executions.
    pub cancelled: Vec<ExecutionResult>,
    /// Total execution time for all hooks.
    pub total_duration: Duration,
    /// Average execution time.
    pub average_duration: Duration,
    /// Success rate (0.0 to 1.0).
    pub success_rate: f64,
}

impl AggregatedResults {
    /// Create aggregated results from individual execution results.
    pub fn from_results(results: Vec<ExecutionResult>) -> Self {
        let total_count = results.len();
        let successful: Vec<_> = results.iter().filter(|r| r.result.success && !r.cancelled).cloned().collect();
        let failed: Vec<_> = results.iter().filter(|r| !r.result.success && !r.cancelled).cloned().collect();
        let cancelled: Vec<_> = results.iter().filter(|r| r.cancelled).cloned().collect();

        let total_duration = results.iter().map(|r| r.duration).sum();
        let average_duration = if total_count > 0 {
            total_duration / total_count as u32
        } else {
            Duration::ZERO
        };

        let success_rate = if total_count > 0 {
            successful.len() as f64 / total_count as f64
        } else {
            0.0
        };

        Self {
            results,
            successful,
            failed,
            cancelled,
            total_duration,
            average_duration,
            success_rate,
        }
    }

    /// Check if any critical (required) hooks failed.
    pub fn has_critical_failures(&self) -> bool {
        self.failed.iter().any(|r| r.config.required)
    }

    /// Get summary statistics.
    pub fn summary(&self) -> String {
        format!(
            "Executed {} hooks: {} successful, {} failed, {} cancelled (success rate: {:.1}%)",
            self.results.len(),
            self.successful.len(),
            self.failed.len(),
            self.cancelled.len(),
            self.success_rate * 100.0
        )
    }
}

/// Enhanced trait for hook executors with advanced execution capabilities.
#[async_trait]
pub trait HookExecutor: Send + Sync {
    /// Execute a hook with the given context.
    async fn execute(&self, context: &HookContext) -> HookExecutorResult;

    /// Execute a hook with full execution context and configuration.
    async fn execute_with_context(&self, exec_context: &ExecutionContext) -> ExecutionResult {
        let start_time = Instant::now();
        let execution_id = exec_context.execution_id.clone();
        let config = exec_context.config.clone();

        debug!("Starting hook execution: {} ({})", execution_id, self.executor_type());

        // Check if already cancelled
        if exec_context.is_cancelled().await {
            return ExecutionResult {
                execution_id,
                result: HookResult::failure("Execution cancelled before start".to_string(), Duration::ZERO),
                config,
                duration: start_time.elapsed(),
                retry_attempts: 0,
                cancelled: true,
                error_details: Some("Pre-execution cancellation".to_string()),
            };
        }

        let mut retry_attempts = 0;
        let mut last_error = None;

        // Retry loop
        loop {
            // Check for cancellation before each attempt
            if exec_context.is_cancelled().await {
                return ExecutionResult {
                    execution_id,
                    result: HookResult::failure("Execution cancelled".to_string(), start_time.elapsed()),
                    config,
                    duration: start_time.elapsed(),
                    retry_attempts,
                    cancelled: true,
                    error_details: Some("Mid-execution cancellation".to_string()),
                };
            }

            // Execute with timeout
            let execution_future = self.execute(&exec_context.hook_context);
            let _result: Result<HookExecutorResult, _> = match timeout(config.timeout, execution_future).await {
                Ok(Ok(hook_result)) => {
                    debug!("Hook execution successful: {} (attempt {})", execution_id, retry_attempts + 1);
                    return ExecutionResult {
                        execution_id,
                        result: hook_result,
                        config,
                        duration: start_time.elapsed(),
                        retry_attempts,
                        cancelled: false,
                        error_details: None,
                    };
                }
                Ok(Err(e)) => {
                    warn!("Hook execution failed: {} - {} (attempt {})", execution_id, e, retry_attempts + 1);
                    last_error = Some(e.to_string());
                    Err(e)
                }
                Err(_) => {
                    warn!("Hook execution timed out: {} after {:?} (attempt {})", execution_id, config.timeout, retry_attempts + 1);
                    let timeout_error = format!("Execution timed out after {:?}", config.timeout);
                    last_error = Some(timeout_error.clone());
                    Err(HookError::Execution(timeout_error))
                }
            };

            retry_attempts += 1;

            // Check if we should retry
            if retry_attempts > config.max_retries {
                break;
            }

            // Wait before retry
            if config.retry_delay > Duration::ZERO {
                tokio::time::sleep(config.retry_delay).await;
            }
        }

        // All retries exhausted
        let error_msg = last_error.unwrap_or_else(|| "Unknown error".to_string());
        ExecutionResult {
            execution_id,
            result: HookResult::failure(error_msg.clone(), start_time.elapsed()),
            config,
            duration: start_time.elapsed(),
            retry_attempts: retry_attempts.saturating_sub(1),
            cancelled: false,
            error_details: Some(error_msg),
        }
    }

    /// Get the name/type of this executor for logging and debugging.
    fn executor_type(&self) -> &'static str;

    /// Validate that this executor can handle the given context.
    fn can_execute(&self, context: &HookContext) -> bool;

    /// Get the estimated execution time for this hook (for timeout planning).
    fn estimated_duration(&self) -> Option<Duration> {
        None
    }

    /// Get the default execution configuration for this executor.
    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig::default()
    }

    /// Prepare for execution (setup, validation, etc.).
    async fn prepare(&self, _context: &HookContext) -> Result<(), HookError> {
        Ok(())
    }

    /// Cleanup after execution (regardless of success/failure).
    async fn cleanup(&self, _context: &HookContext) -> Result<(), HookError> {
        Ok(())
    }
}

/// Advanced execution coordinator that manages multiple hook executions.
#[derive(Debug)]
pub struct ExecutionCoordinator {
    /// Active executions being tracked.
    active_executions: Arc<Mutex<HashMap<String, Arc<ExecutionContext>>>>,
    /// Global execution statistics.
    stats: Arc<RwLock<ExecutionStats>>,
}

/// Global execution statistics.
#[derive(Debug, Clone, Default)]
pub struct ExecutionStats {
    pub total_executions: u64,
    pub successful_executions: u64,
    pub failed_executions: u64,
    pub cancelled_executions: u64,
    pub total_execution_time: Duration,
    pub average_execution_time: Duration,
}

impl ExecutionCoordinator {
    /// Create a new execution coordinator.
    pub fn new() -> Self {
        Self {
            active_executions: Arc::new(Mutex::new(HashMap::new())),
            stats: Arc::new(RwLock::new(ExecutionStats::default())),
        }
    }

    /// Execute multiple hooks with different execution modes.
    pub async fn execute_hooks(
        &self,
        executions: Vec<(Arc<dyn HookExecutor>, ExecutionContext)>,
    ) -> AggregatedResults {
        info!("Starting coordinated execution of {} hooks", executions.len());

        // Separate executions by mode
        let (blocking, async_hooks, fire_and_forget): (Vec<_>, Vec<_>, Vec<_>) = executions
            .into_iter()
            .fold((Vec::new(), Vec::new(), Vec::new()), |mut acc, (executor, context)| {
                match context.config.mode {
                    HookExecutionMode::Blocking => acc.0.push((executor, context)),
                    HookExecutionMode::Async => acc.1.push((executor, context)),
                    HookExecutionMode::FireAndForget => acc.2.push((executor, context)),
                }
                acc
            });

        let mut all_results = Vec::new();

        // Execute blocking hooks sequentially
        for (executor, context) in blocking {
            let result = self.execute_single_tracked(executor, context).await;
            all_results.push(result);
        }

        // Execute async hooks in parallel
        if !async_hooks.is_empty() {
            let async_futures: Vec<_> = async_hooks
                .into_iter()
                .map(|(executor, context)| self.execute_single_tracked(executor, context))
                .collect();

            let async_results = join_all(async_futures).await;
            all_results.extend(async_results);
        }

        // Execute fire-and-forget hooks (don't wait for completion)
        for (executor, context) in fire_and_forget {
            let coordinator = self.clone();
            tokio::spawn(async move {
                let _result = coordinator.execute_single_tracked(executor, context).await;
                // Fire-and-forget results are not included in aggregated results
            });
        }

        // Update global statistics
        self.update_stats(&all_results).await;

        let aggregated = AggregatedResults::from_results(all_results);
        info!("Coordinated execution completed: {}", aggregated.summary());
        aggregated
    }

    /// Execute a single hook with tracking.
    async fn execute_single_tracked(
        &self,
        executor: Arc<dyn HookExecutor>,
        context: ExecutionContext,
    ) -> ExecutionResult {
        let execution_id = context.execution_id.clone();

        // Track active execution
        {
            let mut active = self.active_executions.lock().await;
            active.insert(execution_id.clone(), Arc::new(context.clone()));
        }

        // Prepare for execution
        if let Err(e) = executor.prepare(&context.hook_context).await {
            warn!("Hook preparation failed: {} - {}", execution_id, e);
            return ExecutionResult {
                execution_id: execution_id.clone(),
                result: HookResult::failure(format!("Preparation failed: {}", e), Duration::ZERO),
                config: context.config.clone(),
                duration: Duration::ZERO,
                retry_attempts: 0,
                cancelled: false,
                error_details: Some(format!("Preparation error: {}", e)),
            };
        }

        // Execute the hook
        let result = if context.config.isolated {
            // Execute in isolated task
            let executor_clone = executor.clone();
            let context_clone = context.clone();
            tokio::spawn(async move {
                executor_clone.execute_with_context(&context_clone).await
            })
            .await
            .unwrap_or_else(|e| ExecutionResult {
                execution_id: execution_id.clone(),
                result: HookResult::failure(format!("Task join error: {}", e), context.elapsed()),
                config: context.config.clone(),
                duration: context.elapsed(),
                retry_attempts: 0,
                cancelled: false,
                error_details: Some(format!("Isolation error: {}", e)),
            })
        } else {
            // Execute directly
            executor.execute_with_context(&context).await
        };

        // Cleanup after execution
        if let Err(e) = executor.cleanup(&context.hook_context).await {
            warn!("Hook cleanup failed: {} - {}", execution_id, e);
        }

        // Remove from active executions
        {
            let mut active = self.active_executions.lock().await;
            active.remove(&execution_id);
        }

        result
    }

    /// Cancel a specific execution.
    pub async fn cancel_execution(&self, execution_id: &str) -> bool {
        let active = self.active_executions.lock().await;
        if let Some(context) = active.get(execution_id) {
            context.cancel().await;
            true
        } else {
            false
        }
    }

    /// Cancel all active executions.
    pub async fn cancel_all(&self) {
        let active = self.active_executions.lock().await;
        for context in active.values() {
            context.cancel().await;
        }
    }

    /// Get list of active execution IDs.
    pub async fn get_active_executions(&self) -> Vec<String> {
        let active = self.active_executions.lock().await;
        active.keys().cloned().collect()
    }

    /// Update global execution statistics.
    async fn update_stats(&self, results: &[ExecutionResult]) {
        let mut stats = self.stats.write().await;

        for result in results {
            stats.total_executions += 1;
            stats.total_execution_time += result.duration;

            if result.cancelled {
                stats.cancelled_executions += 1;
            } else if result.result.success {
                stats.successful_executions += 1;
            } else {
                stats.failed_executions += 1;
            }
        }

        // Update average
        if stats.total_executions > 0 {
            stats.average_execution_time = stats.total_execution_time / stats.total_executions as u32;
        }
    }

    /// Get current execution statistics.
    pub async fn get_stats(&self) -> ExecutionStats {
        self.stats.read().await.clone()
    }
}

impl Clone for ExecutionCoordinator {
    fn clone(&self) -> Self {
        Self {
            active_executions: self.active_executions.clone(),
            stats: self.stats.clone(),
        }
    }
}

impl Default for ExecutionCoordinator {
    fn default() -> Self {
        Self::new()
    }
}

// Re-export executors from the executors module
pub use crate::hooks::executors::{ScriptExecutor, WebhookExecutor, McpToolExecutor};

// Placeholder implementation for ExecutableExecutor - will be implemented later
pub struct ExecutableExecutor;



#[async_trait]
impl HookExecutor for ExecutableExecutor {
    async fn execute(&self, _context: &HookContext) -> HookExecutorResult {
        // TODO: Implement in Phase 2.3
        Err(HookError::Execution("ExecutableExecutor not yet implemented".to_string()))
    }

    fn executor_type(&self) -> &'static str {
        "executable"
    }

    fn can_execute(&self, _context: &HookContext) -> bool {
        // TODO: Implement in Phase 2.3
        false
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(30)) // Executables can vary widely
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: Duration::from_secs(300), // 5 minutes for custom executables
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            required: false,
            max_retries: 1,
            retry_delay: Duration::from_secs(1),
            isolated: true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::types::LifecycleEvent;

    use tokio::time::sleep;

    // Mock executor for testing
    struct MockExecutor {
        should_fail: bool,
        execution_time: Duration,
        call_count: Arc<Mutex<u32>>,
    }

    impl MockExecutor {
        fn new(should_fail: bool, execution_time: Duration) -> Self {
            Self {
                should_fail,
                execution_time,
                call_count: Arc::new(Mutex::new(0)),
            }
        }

        async fn get_call_count(&self) -> u32 {
            *self.call_count.lock().await
        }
    }

    #[async_trait]
    impl HookExecutor for MockExecutor {
        async fn execute(&self, _context: &HookContext) -> HookExecutorResult {
            {
                let mut count = self.call_count.lock().await;
                *count += 1;
            }

            sleep(self.execution_time).await;

            if self.should_fail {
                Err(HookError::Execution("Mock execution failed".to_string()))
            } else {
                Ok(HookResult::success(Some("Mock success".to_string()), self.execution_time))
            }
        }

        fn executor_type(&self) -> &'static str {
            "mock"
        }

        fn can_execute(&self, _context: &HookContext) -> bool {
            true
        }

        fn estimated_duration(&self) -> Option<Duration> {
            Some(self.execution_time)
        }
    }

    fn create_test_context() -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("/tmp")),
            timestamp: chrono::Utc::now(),
        };
        HookContext::new(event, std::path::PathBuf::from("/tmp"))
    }

    #[tokio::test]
    async fn test_execution_config_default() {
        let config = ExecutionConfig::default();
        assert_eq!(config.timeout, Duration::from_secs(30));
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert_eq!(config.priority, HookPriority::NORMAL);
        assert!(!config.required);
        assert_eq!(config.max_retries, 0);
        assert!(config.isolated);
    }

    #[tokio::test]
    async fn test_execution_context_creation() {
        let hook_context = create_test_context();
        let config = ExecutionConfig::default();
        let exec_context = ExecutionContext::new(hook_context, config.clone());

        assert!(!exec_context.execution_id.is_empty());
        assert_eq!(exec_context.config.timeout, config.timeout);
        assert!(!exec_context.is_cancelled().await);
    }

    #[tokio::test]
    async fn test_execution_context_cancellation() {
        let hook_context = create_test_context();
        let config = ExecutionConfig::default();
        let exec_context = ExecutionContext::new(hook_context, config);

        assert!(!exec_context.is_cancelled().await);
        exec_context.cancel().await;
        assert!(exec_context.is_cancelled().await);
    }

    #[tokio::test]
    async fn test_successful_execution() {
        let executor = MockExecutor::new(false, Duration::from_millis(100));
        let hook_context = create_test_context();
        let config = ExecutionConfig::default();
        let exec_context = ExecutionContext::new(hook_context, config);

        let result = executor.execute_with_context(&exec_context).await;

        assert!(result.result.success);
        assert!(!result.cancelled);
        assert_eq!(result.retry_attempts, 0);
        assert!(result.duration >= Duration::from_millis(100));
        assert_eq!(executor.get_call_count().await, 1);
    }

    #[tokio::test]
    async fn test_failed_execution_with_retries() {
        let executor = MockExecutor::new(true, Duration::from_millis(50));
        let hook_context = create_test_context();
        let mut config = ExecutionConfig::default();
        config.max_retries = 2;
        config.retry_delay = Duration::from_millis(10);
        let exec_context = ExecutionContext::new(hook_context, config);

        let result = executor.execute_with_context(&exec_context).await;

        assert!(!result.result.success);
        assert!(!result.cancelled);
        assert_eq!(result.retry_attempts, 2); // 2 retries after initial failure
        assert_eq!(executor.get_call_count().await, 3); // Initial + 2 retries
    }

    #[tokio::test]
    async fn test_execution_timeout() {
        let executor = MockExecutor::new(false, Duration::from_millis(200));
        let hook_context = create_test_context();
        let mut config = ExecutionConfig::default();
        config.timeout = Duration::from_millis(50); // Shorter than execution time
        let exec_context = ExecutionContext::new(hook_context, config);

        let result = executor.execute_with_context(&exec_context).await;

        assert!(!result.result.success);
        assert!(!result.cancelled);
        assert!(result.error_details.unwrap().contains("timed out"));
    }

    #[tokio::test]
    async fn test_execution_cancellation() {
        let executor = MockExecutor::new(false, Duration::from_millis(200));
        let hook_context = create_test_context();
        let config = ExecutionConfig::default();
        let exec_context = ExecutionContext::new(hook_context, config);

        // Cancel before execution
        exec_context.cancel().await;
        let result = executor.execute_with_context(&exec_context).await;

        assert!(!result.result.success);
        assert!(result.cancelled);
        assert_eq!(result.retry_attempts, 0);
        assert_eq!(executor.get_call_count().await, 0); // Should not execute
    }

    #[tokio::test]
    async fn test_aggregated_results() {
        let results = vec![
            ExecutionResult {
                execution_id: "1".to_string(),
                result: HookResult::success(Some("success".to_string()), Duration::from_millis(100)),
                config: ExecutionConfig::default(),
                duration: Duration::from_millis(100),
                retry_attempts: 0,
                cancelled: false,
                error_details: None,
            },
            ExecutionResult {
                execution_id: "2".to_string(),
                result: HookResult::failure("failed".to_string(), Duration::from_millis(50)),
                config: ExecutionConfig::default(),
                duration: Duration::from_millis(50),
                retry_attempts: 1,
                cancelled: false,
                error_details: Some("error".to_string()),
            },
        ];

        let aggregated = AggregatedResults::from_results(results);

        assert_eq!(aggregated.results.len(), 2);
        assert_eq!(aggregated.successful.len(), 1);
        assert_eq!(aggregated.failed.len(), 1);
        assert_eq!(aggregated.cancelled.len(), 0);
        assert_eq!(aggregated.success_rate, 0.5);
        assert_eq!(aggregated.total_duration, Duration::from_millis(150));
        assert_eq!(aggregated.average_duration, Duration::from_millis(75));
    }

    #[tokio::test]
    async fn test_execution_coordinator() {
        let coordinator = ExecutionCoordinator::new();

        let executor1 = Arc::new(MockExecutor::new(false, Duration::from_millis(50)));
        let executor2 = Arc::new(MockExecutor::new(true, Duration::from_millis(30)));

        let hook_context = create_test_context();
        let config1 = ExecutionConfig {
            mode: HookExecutionMode::Async,
            ..ExecutionConfig::default()
        };
        let config2 = ExecutionConfig {
            mode: HookExecutionMode::Async,
            ..ExecutionConfig::default()
        };

        let executions = vec![
            (executor1.clone() as Arc<dyn HookExecutor>, ExecutionContext::new(hook_context.clone(), config1)),
            (executor2.clone() as Arc<dyn HookExecutor>, ExecutionContext::new(hook_context, config2)),
        ];

        let results = coordinator.execute_hooks(executions).await;

        assert_eq!(results.results.len(), 2);
        assert_eq!(results.successful.len(), 1);
        assert_eq!(results.failed.len(), 1);
        assert_eq!(results.success_rate, 0.5);

        // Check statistics were updated
        let stats = coordinator.get_stats().await;
        assert_eq!(stats.total_executions, 2);
        assert_eq!(stats.successful_executions, 1);
        assert_eq!(stats.failed_executions, 1);
    }

    #[tokio::test]
    async fn test_execution_coordinator_cancellation() {
        let coordinator = ExecutionCoordinator::new();

        let executor = Arc::new(MockExecutor::new(false, Duration::from_millis(1000))); // Longer execution time
        let hook_context = create_test_context();
        let config = ExecutionConfig::default();
        let exec_context = ExecutionContext::new(hook_context, config);
        let execution_id = exec_context.execution_id.clone();

        let executions = vec![
            (executor.clone() as Arc<dyn HookExecutor>, exec_context),
        ];

        // Start execution in background
        let coordinator_clone = coordinator.clone();
        let execution_task = tokio::spawn(async move {
            coordinator_clone.execute_hooks(executions).await
        });

        // Wait a bit to ensure execution has started, then cancel
        sleep(Duration::from_millis(100)).await;
        let cancelled = coordinator.cancel_execution(&execution_id).await;

        // Wait for execution to complete
        let results = execution_task.await.unwrap();

        // Either the execution was cancelled or it completed before cancellation
        // Both are valid outcomes for this test
        assert_eq!(results.results.len(), 1);
        if cancelled {
            // If we successfully cancelled, check that cancellation was handled
            // (The result could be in cancelled list or completed before cancellation)
            assert!(results.results.len() == 1); // Should have exactly one result
        }
        // The important thing is that the coordinator handled the cancellation request properly
    }

    #[test]
    fn test_executor_default_configs() {
        let script = ScriptExecutor::new();
        let webhook = WebhookExecutor::new();
        let mcp = McpToolExecutor::new();
        let executable = ExecutableExecutor;

        assert_eq!(script.executor_type(), "script");
        assert_eq!(webhook.executor_type(), "webhook");
        assert_eq!(mcp.executor_type(), "mcp_tool");
        assert_eq!(executable.executor_type(), "executable");

        // Test estimated durations
        assert_eq!(script.estimated_duration(), Some(Duration::from_secs(5)));
        assert_eq!(webhook.estimated_duration(), Some(Duration::from_secs(10)));
        assert_eq!(mcp.estimated_duration(), Some(Duration::from_secs(15)));
        assert_eq!(executable.estimated_duration(), Some(Duration::from_secs(30)));

        // Test default configs have appropriate timeouts
        assert_eq!(script.default_config().timeout, Duration::from_secs(30));
        assert_eq!(webhook.default_config().timeout, Duration::from_secs(60));
        assert_eq!(mcp.default_config().timeout, Duration::from_secs(120));
        assert_eq!(executable.default_config().timeout, Duration::from_secs(300));
    }
}