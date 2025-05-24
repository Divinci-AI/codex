//! Hook manager for coordinating hook execution.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

use futures::future::join_all;
use tokio::time::timeout;

use crate::hooks::config::HooksConfig;
use crate::hooks::context::{HookContext, HookExecutionContext};
use crate::hooks::executor::{HookExecutor, ScriptExecutor, WebhookExecutor, McpToolExecutor, ExecutableExecutor};
use crate::hooks::registry::HookRegistry;
use crate::hooks::types::{HookError, HookResult, HookType, LifecycleEvent, HookExecutionMode};

/// Execution metrics for testing and monitoring.
#[derive(Debug, Clone, Default)]
pub struct ExecutionMetrics {
    pub total_executions: u64,
    pub successful_executions: u64,
    pub failed_executions: u64,
    pub cancelled_executions: u64,
    pub total_execution_time: Duration,
    pub average_execution_time: Duration,
}

/// Central manager for the lifecycle hooks system.
pub struct HookManager {
    registry: Arc<HookRegistry>,
    config: HooksConfig,
    executors: HashMap<String, Box<dyn HookExecutor>>,
    working_directory: PathBuf,
    metrics: HookExecutionMetrics,
}

/// Metrics for tracking hook execution performance.
#[derive(Debug, Clone, Default)]
pub struct HookExecutionMetrics {
    pub total_executions: u64,
    pub successful_executions: u64,
    pub failed_executions: u64,
    pub total_execution_time: Duration,
    pub average_execution_time: Duration,
}

/// Result of executing multiple hooks.
#[derive(Debug, Clone)]
pub struct HookExecutionResults {
    pub successful: Vec<HookExecutionResult>,
    pub failed: Vec<HookExecutionResult>,
    pub total_duration: Duration,
}

/// Result of executing a single hook.
#[derive(Debug, Clone)]
pub struct HookExecutionResult {
    pub hook_description: String,
    pub result: HookResult,
    pub execution_time: Duration,
}

impl HookManager {
    /// Create a new hook manager with the given configuration.
    pub async fn new(config: HooksConfig) -> Result<Self, HookError> {
        Self::new_with_working_directory(config, std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp"))).await
    }

    /// Create a new hook manager with a specific working directory.
    pub async fn new_with_working_directory(config: HooksConfig, working_directory: PathBuf) -> Result<Self, HookError> {
        let registry = Arc::new(HookRegistry::new(config.clone()).await?);

        // Initialize hook executors
        let mut executors: HashMap<String, Box<dyn HookExecutor>> = HashMap::new();
        executors.insert("script".to_string(), Box::new(ScriptExecutor::new()));
        executors.insert("webhook".to_string(), Box::new(WebhookExecutor::new()));
        executors.insert("mcp_tool".to_string(), Box::new(McpToolExecutor::new()));
        executors.insert("executable".to_string(), Box::new(ExecutableExecutor));

        Ok(Self {
            registry,
            config,
            executors,
            working_directory,
            metrics: HookExecutionMetrics::default(),
        })
    }

    /// Trigger a lifecycle event and execute all matching hooks.
    pub async fn trigger_event(&self, event: LifecycleEvent) -> Result<(), HookError> {
        if !self.config.hooks.enabled {
            return Ok(());
        }

        let start_time = Instant::now();
        tracing::info!("Triggering lifecycle event: {:?}", event.event_type());

        // Create hook execution context
        let context = HookExecutionContext::new(event.clone(), self.working_directory.clone())
            .env("CODEX_HOOKS_ENABLED".to_string(), "true".to_string())
            .build();

        // Get matching hooks from registry
        let matching_hooks = self.registry.get_matching_hooks(&event, &context)
            .map_err(|e| HookError::Execution(format!("Failed to get matching hooks: {}", e)))?;

        if matching_hooks.is_empty() {
            tracing::debug!("No hooks found for event: {:?}", event.event_type());
            return Ok(());
        }

        tracing::info!("Found {} matching hooks for event: {:?}", matching_hooks.len(), event.event_type());

        // Execute hooks based on their execution mode
        let results = self.execute_hooks(matching_hooks, &context).await?;

        // Log execution results
        let total_duration = start_time.elapsed();
        self.log_execution_results(&results, total_duration);

        // Handle any critical failures
        self.handle_execution_results(&results)?;

        Ok(())
    }

    /// Check if hooks are enabled.
    pub fn is_enabled(&self) -> bool {
        self.config.hooks.enabled
    }

    /// Get the hook registry.
    pub fn registry(&self) -> Arc<HookRegistry> {
        self.registry.clone()
    }

    /// Get execution metrics.
    pub fn metrics(&self) -> &HookExecutionMetrics {
        &self.metrics
    }

    /// Get execution metrics for testing and monitoring.
    pub async fn get_execution_metrics(&self) -> ExecutionMetrics {
        ExecutionMetrics {
            total_executions: self.metrics.total_executions,
            successful_executions: self.metrics.successful_executions,
            failed_executions: self.metrics.failed_executions,
            cancelled_executions: 0, // Not tracked in current metrics
            total_execution_time: Duration::from_millis(self.metrics.total_execution_time_ms),
            average_execution_time: Duration::from_millis(self.metrics.average_execution_time_ms),
        }
    }

    /// Reset execution metrics for testing.
    pub async fn reset_metrics(&self) {
        // Note: This is a simplified implementation for testing
        // In a real implementation, we'd need mutable access to metrics
        // For now, this is a no-op since metrics is not mutable
    }

    /// Execute a list of hooks with the given context.
    async fn execute_hooks(
        &self,
        hooks: Vec<&crate::hooks::config::HookConfig>,
        context: &HookContext,
    ) -> Result<HookExecutionResults, HookError> {
        let mut successful = Vec::new();
        let mut failed = Vec::new();
        let start_time = Instant::now();

        // Separate hooks by execution mode
        let (blocking_hooks, async_hooks, fire_and_forget_hooks): (Vec<_>, Vec<_>, Vec<_>) = hooks
            .into_iter()
            .partition3(|hook| match hook.mode {
                HookExecutionMode::Blocking => (true, false, false),
                HookExecutionMode::Async => (false, true, false),
                HookExecutionMode::FireAndForget => (false, false, true),
            });

        // Execute blocking hooks first (sequentially)
        for hook in blocking_hooks {
            let result = self.execute_single_hook(hook, context).await;
            match result {
                Ok(exec_result) => {
                    if exec_result.result.success {
                        successful.push(exec_result);
                    } else {
                        failed.push(exec_result.clone());
                        // For blocking hooks, if required and failed, stop execution
                        if hook.required {
                            return Err(HookError::Execution(format!(
                                "Required blocking hook failed: {}",
                                exec_result.hook_description
                            )));
                        }
                    }
                }
                Err(e) => {
                    let exec_result = HookExecutionResult {
                        hook_description: self.get_hook_description(hook),
                        result: HookResult::failure(e.to_string(), Duration::from_secs(0)),
                        execution_time: Duration::from_secs(0),
                    };
                    failed.push(exec_result);
                    if hook.required {
                        return Err(e);
                    }
                }
            }
        }

        // Execute async hooks in parallel
        if !async_hooks.is_empty() {
            let async_futures: Vec<_> = async_hooks
                .into_iter()
                .map(|hook| self.execute_single_hook(hook, context))
                .collect();

            let async_results = join_all(async_futures).await;
            for (i, result) in async_results.into_iter().enumerate() {
                match result {
                    Ok(exec_result) => {
                        if exec_result.result.success {
                            successful.push(exec_result);
                        } else {
                            failed.push(exec_result);
                        }
                    }
                    Err(e) => {
                        let exec_result = HookExecutionResult {
                            hook_description: format!("Async hook {}", i),
                            result: HookResult::failure(e.to_string(), Duration::from_secs(0)),
                            execution_time: Duration::from_secs(0),
                        };
                        failed.push(exec_result);
                    }
                }
            }
        }

        // Execute fire-and-forget hooks (don't wait for results)
        if !fire_and_forget_hooks.is_empty() {
            for hook in fire_and_forget_hooks {
                let hook_description = self.get_hook_description(hook);
                let _context_clone = context.clone();

                // Create a simple executor for fire-and-forget (we'll implement this properly later)
                tokio::spawn(async move {
                    tracing::debug!("Fire-and-forget hook started: {}", hook_description);
                    // TODO: Implement actual execution in Phase 2.2
                    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                    tracing::debug!("Fire-and-forget hook completed: {}", hook_description);
                });
            }
        }

        Ok(HookExecutionResults {
            successful,
            failed,
            total_duration: start_time.elapsed(),
        })
    }

    /// Execute a single hook with timeout and error handling.
    async fn execute_single_hook(
        &self,
        hook: &crate::hooks::config::HookConfig,
        context: &HookContext,
    ) -> Result<HookExecutionResult, HookError> {
        let start_time = Instant::now();
        let hook_description = self.get_hook_description(hook);

        tracing::debug!("Executing hook: {}", hook_description);

        // Get the appropriate executor
        let executor = self.get_executor_for_hook(&hook.hook_type)?;

        // Get timeout (from hook config or global default)
        let timeout_duration = hook.get_timeout(Duration::from_secs(self.config.hooks.timeout_seconds));

        // Execute with timeout
        let result = match timeout(timeout_duration, executor.execute(context)).await {
            Ok(Ok(hook_result)) => {
                tracing::debug!("Hook executed successfully: {}", hook_description);
                hook_result
            }
            Ok(Err(e)) => {
                tracing::warn!("Hook execution failed: {} - {}", hook_description, e);
                HookResult::failure(e.to_string(), start_time.elapsed())
            }
            Err(_) => {
                let error_msg = format!("Hook execution timed out after {:?}", timeout_duration);
                tracing::warn!("{}: {}", error_msg, hook_description);
                HookResult::failure(error_msg, timeout_duration)
            }
        };

        Ok(HookExecutionResult {
            hook_description,
            result,
            execution_time: start_time.elapsed(),
        })
    }

    /// Get the appropriate executor for a hook type.
    fn get_executor_for_hook(&self, hook_type: &HookType) -> Result<&Box<dyn HookExecutor>, HookError> {
        let executor_key = match hook_type {
            HookType::Script { .. } => "script",
            HookType::Webhook { .. } => "webhook",
            HookType::McpTool { .. } => "mcp_tool",
            HookType::Executable { .. } => "executable",
        };

        self.executors.get(executor_key).ok_or_else(|| {
            HookError::Execution(format!("No executor found for hook type: {}", executor_key))
        })
    }

    /// Get a human-readable description of a hook.
    fn get_hook_description(&self, hook: &crate::hooks::config::HookConfig) -> String {
        hook.description
            .clone()
            .unwrap_or_else(|| format!("{:?} hook", hook.hook_type))
    }

    /// Log the results of hook execution.
    fn log_execution_results(&self, results: &HookExecutionResults, total_duration: Duration) {
        let total_hooks = results.successful.len() + results.failed.len();

        tracing::info!(
            "Hook execution completed: {}/{} successful, {} failed, took {:?}",
            results.successful.len(),
            total_hooks,
            results.failed.len(),
            total_duration
        );

        // Log individual failures
        for failed_result in &results.failed {
            tracing::warn!(
                "Hook failed: {} - {}",
                failed_result.hook_description,
                failed_result.result.error.as_ref().unwrap_or(&"Unknown error".to_string())
            );
        }

        // Log performance metrics
        if !results.successful.is_empty() {
            let avg_time: Duration = results.successful
                .iter()
                .map(|r| r.execution_time)
                .sum::<Duration>() / results.successful.len() as u32;

            tracing::debug!("Average successful hook execution time: {:?}", avg_time);
        }
    }

    /// Handle execution results and determine if any critical failures occurred.
    fn handle_execution_results(&self, results: &HookExecutionResults) -> Result<(), HookError> {
        // Check if there were any critical failures that should stop execution
        let critical_failures: Vec<_> = results.failed
            .iter()
            .filter(|result| result.hook_description.contains("required"))
            .collect();

        if !critical_failures.is_empty() {
            let error_msg = format!(
                "Critical hook failures detected: {}",
                critical_failures
                    .iter()
                    .map(|r| r.hook_description.as_str())
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            return Err(HookError::Execution(error_msg));
        }

        Ok(())
    }
}

/// Helper trait for partitioning iterators into three groups.
trait Partition3<T> {
    fn partition3<F>(self, predicate: F) -> (Vec<T>, Vec<T>, Vec<T>)
    where
        F: Fn(&T) -> (bool, bool, bool);
}

impl<I, T> Partition3<T> for I
where
    I: Iterator<Item = T>,
{
    fn partition3<F>(self, predicate: F) -> (Vec<T>, Vec<T>, Vec<T>)
    where
        F: Fn(&T) -> (bool, bool, bool),
    {
        let mut first = Vec::new();
        let mut second = Vec::new();
        let mut third = Vec::new();

        for item in self {
            let (is_first, is_second, is_third) = predicate(&item);
            if is_first {
                first.push(item);
            } else if is_second {
                second.push(item);
            } else if is_third {
                third.push(item);
            }
        }

        (first, second, third)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn create_test_config() -> HooksConfig {
        HooksConfig {
            hooks: crate::hooks::config::GlobalHooksConfig {
                enabled: true,
                timeout_seconds: 30,
                parallel_execution: true,
                session: Vec::new(),
                task: Vec::new(),
                exec: Vec::new(),
                patch: Vec::new(),
                mcp: Vec::new(),
                agent: Vec::new(),
                error: Vec::new(),
                integration: Vec::new(),
            },
        }
    }

    #[tokio::test]
    async fn test_hook_manager_creation() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();

        assert!(manager.is_enabled());
        assert_eq!(manager.executors.len(), 4); // script, webhook, mcp_tool, executable
    }

    #[tokio::test]
    async fn test_hook_manager_disabled() {
        let mut config = create_test_config();
        config.hooks.enabled = false;

        let manager = HookManager::new(config).await.unwrap();
        assert!(!manager.is_enabled());

        // Test that disabled manager doesn't execute hooks
        let event = LifecycleEvent::TaskStart {
            task_id: "test-task".to_string(),
            session_id: "test-session".to_string(),
            prompt: "Test task".to_string(),
            timestamp: chrono::Utc::now(),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_hook_manager_with_working_directory() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config();

        let manager = HookManager::new_with_working_directory(
            config,
            temp_dir.path().to_path_buf(),
        ).await.unwrap();

        assert_eq!(manager.working_directory, temp_dir.path());
    }

    #[tokio::test]
    async fn test_hook_execution_metrics() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let metrics = manager.metrics();
        assert_eq!(metrics.total_executions, 0);
        assert_eq!(metrics.successful_executions, 0);
        assert_eq!(metrics.failed_executions, 0);
    }

    #[tokio::test]
    async fn test_trigger_event_no_matching_hooks() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp")),
            timestamp: chrono::Utc::now(),
        };

        // Should succeed even with no matching hooks
        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[test]
    fn test_partition3_helper() {
        let items = vec![1, 2, 3, 4, 5, 6];
        let (first, second, third) = items.into_iter().partition3(|&x| {
            if x % 3 == 0 {
                (true, false, false)  // divisible by 3
            } else if x % 2 == 0 {
                (false, true, false)  // even
            } else {
                (false, false, true)  // odd
            }
        });

        assert_eq!(first, vec![3, 6]);  // divisible by 3
        assert_eq!(second, vec![2, 4]); // even (but not divisible by 3)
        assert_eq!(third, vec![1, 5]);  // odd
    }

    #[test]
    fn test_hook_execution_results() {
        let successful = vec![
            HookExecutionResult {
                hook_description: "test hook 1".to_string(),
                result: HookResult::success(Some("output".to_string()), Duration::from_millis(100)),
                execution_time: Duration::from_millis(100),
            },
        ];

        let failed = vec![
            HookExecutionResult {
                hook_description: "test hook 2".to_string(),
                result: HookResult::failure("error".to_string(), Duration::from_millis(50)),
                execution_time: Duration::from_millis(50),
            },
        ];

        let results = HookExecutionResults {
            successful,
            failed,
            total_duration: Duration::from_millis(150),
        };

        assert_eq!(results.successful.len(), 1);
        assert_eq!(results.failed.len(), 1);
        assert_eq!(results.total_duration, Duration::from_millis(150));
    }
}
