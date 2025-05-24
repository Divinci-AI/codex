//! Comprehensive unit tests for the hooks system.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use tempfile::TempDir;
use tokio::time::sleep;

use crate::hooks::config::{HookConfig, HooksConfig, GlobalHooksConfig};
use crate::hooks::context::{HookContext, HookExecutionContext};
use crate::hooks::executor::{HookExecutor, HookExecutorResult, ExecutionResult, HookExecutionResults};
use crate::hooks::manager::HookManager;
use crate::hooks::types::{
    HookError, HookResult, HookType, LifecycleEvent, HookExecutionMode, HookPriority,
};

/// Helper function to create a test configuration.
fn create_test_config() -> HooksConfig {
    HooksConfig {
        hooks: GlobalHooksConfig {
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

/// Helper function to create a test configuration with hooks.
fn create_test_config_with_hooks() -> HooksConfig {
    HooksConfig {
        hooks: GlobalHooksConfig {
            enabled: true,
            timeout_seconds: 30,
            parallel_execution: true,
            session: vec![
                HookConfig {
                    event: "session.start".to_string(),
                    hook_type: HookType::Script {
                        command: vec!["echo".to_string(), "session started".to_string()],
                        cwd: None,
                        environment: HashMap::new(),
                        timeout: Some(Duration::from_secs(5)),
                    },
                    description: Some("Test session start hook".to_string()),
                    enabled: true,
                    required: false,
                    timeout: Some(Duration::from_secs(10)),
                    mode: HookExecutionMode::Async,
                    priority: HookPriority::NORMAL,
                    conditions: HashMap::new(),
                },
            ],
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

/// Helper function to create a test event.
fn create_test_event() -> LifecycleEvent {
    LifecycleEvent::SessionStart {
        session_id: "test_session_123".to_string(),
        user_id: Some("test_user".to_string()),
    }
}

/// Helper function to create a test context.
fn create_test_context() -> HookContext {
    let event = create_test_event();
    let working_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp"));
    
    HookContext::new(
        event,
        working_dir,
        HookType::Script {
            command: vec!["echo".to_string(), "test".to_string()],
            cwd: None,
            environment: HashMap::new(),
            timeout: Some(Duration::from_secs(5)),
        },
        HookConfig {
            event: "session.start".to_string(),
            hook_type: HookType::Script {
                command: vec!["echo".to_string(), "test".to_string()],
                cwd: None,
                environment: HashMap::new(),
                timeout: Some(Duration::from_secs(5)),
            },
            description: Some("Test hook".to_string()),
            enabled: true,
            required: false,
            timeout: Some(Duration::from_secs(10)),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            conditions: HashMap::new(),
        },
    )
}

mod manager_tests {
    use super::*;

    #[tokio::test]
    async fn test_hook_manager_creation() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();

        assert!(manager.is_enabled());
        assert_eq!(manager.executors.len(), 4); // script, webhook, mcp_tool, executable
    }

    #[tokio::test]
    async fn test_hook_manager_creation_with_working_directory() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config();
        
        let manager = HookManager::new_with_working_directory(
            config,
            temp_dir.path().to_path_buf(),
        ).await.unwrap();

        assert!(manager.is_enabled());
        assert_eq!(manager.working_directory, temp_dir.path());
    }

    #[tokio::test]
    async fn test_hook_manager_disabled() {
        let mut config = create_test_config();
        config.hooks.enabled = false;
        
        let manager = HookManager::new(config).await.unwrap();
        assert!(!manager.is_enabled());
    }

    #[tokio::test]
    async fn test_trigger_event_when_disabled() {
        let mut config = create_test_config();
        config.hooks.enabled = false;
        
        let manager = HookManager::new(config).await.unwrap();
        let event = create_test_event();
        
        // Should succeed but do nothing when disabled
        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_trigger_event_with_no_matching_hooks() {
        let config = create_test_config(); // No hooks configured
        let manager = HookManager::new(config).await.unwrap();
        let event = create_test_event();
        
        // Should succeed with no hooks to execute
        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_get_executor_for_hook_script() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();
        
        let hook_type = HookType::Script {
            command: vec!["echo".to_string(), "test".to_string()],
            cwd: None,
            environment: HashMap::new(),
            timeout: Some(Duration::from_secs(5)),
        };
        
        let executor = manager.get_executor_for_hook(&hook_type);
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().executor_type(), "script");
    }

    #[tokio::test]
    async fn test_get_executor_for_hook_webhook() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();
        
        let hook_type = HookType::Webhook {
            url: "https://example.com/webhook".to_string(),
            method: crate::hooks::types::HttpMethod::Post,
            headers: HashMap::new(),
            timeout: Some(Duration::from_secs(10)),
            retry_count: Some(3),
        };
        
        let executor = manager.get_executor_for_hook(&hook_type);
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().executor_type(), "webhook");
    }

    #[tokio::test]
    async fn test_get_executor_for_hook_mcp() {
        let config = create_test_config();
        let manager = HookManager::new(config).await.unwrap();
        
        let hook_type = HookType::McpTool {
            server: "test_server".to_string(),
            tool: "test_tool".to_string(),
            timeout: Some(Duration::from_secs(15)),
        };
        
        let executor = manager.get_executor_for_hook(&hook_type);
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().executor_type(), "mcp_tool");
    }
}

mod executor_tests {
    use super::*;
    use crate::hooks::executors::{ScriptExecutor, WebhookExecutor, McpToolExecutor};

    #[tokio::test]
    async fn test_script_executor_basic() {
        let executor = ScriptExecutor::new();
        assert_eq!(executor.executor_type(), "script");
        
        let context = create_test_context();
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_script_executor_execution() {
        let executor = ScriptExecutor::new();
        let mut context = create_test_context();
        
        // Set up a simple echo command
        context.hook_type = HookType::Script {
            command: vec!["echo".to_string(), "hello world".to_string()],
            cwd: None,
            environment: HashMap::new(),
            timeout: Some(Duration::from_secs(5)),
        };
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        assert!(hook_result.success);
        assert!(hook_result.output.is_some());
        assert!(hook_result.output.unwrap().contains("hello world"));
    }

    #[tokio::test]
    async fn test_script_executor_invalid_command() {
        let executor = ScriptExecutor::new();
        let mut context = create_test_context();
        
        // Set up an invalid command
        context.hook_type = HookType::Script {
            command: vec!["nonexistent_command_12345".to_string()],
            cwd: None,
            environment: HashMap::new(),
            timeout: Some(Duration::from_secs(5)),
        };
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok()); // Executor should handle the error gracefully
        
        let hook_result = result.unwrap();
        assert!(!hook_result.success); // But the hook should fail
    }

    #[tokio::test]
    async fn test_webhook_executor_basic() {
        let executor = WebhookExecutor::new();
        assert_eq!(executor.executor_type(), "webhook");
        
        let mut context = create_test_context();
        context.hook_type = HookType::Webhook {
            url: "https://example.com/webhook".to_string(),
            method: crate::hooks::types::HttpMethod::Post,
            headers: HashMap::new(),
            timeout: Some(Duration::from_secs(10)),
            retry_count: Some(3),
        };
        
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_webhook_executor_invalid_context() {
        let executor = WebhookExecutor::new();
        let context = create_test_context(); // Script context, not webhook
        
        assert!(!executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_mcp_executor_basic() {
        let executor = McpToolExecutor::new();
        assert_eq!(executor.executor_type(), "mcp_tool");
        
        let mut context = create_test_context();
        context.hook_type = HookType::McpTool {
            server: "test_server".to_string(),
            tool: "test_tool".to_string(),
            timeout: Some(Duration::from_secs(15)),
        };
        
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_mcp_executor_execution() {
        let executor = McpToolExecutor::new();
        let mut context = create_test_context();
        
        context.hook_type = HookType::McpTool {
            server: "test_server".to_string(),
            tool: "test_tool".to_string(),
            timeout: Some(Duration::from_secs(15)),
        };
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        // MCP executor currently simulates success
        assert!(hook_result.success);
    }
}

mod timeout_and_error_tests {
    use super::*;
    use crate::hooks::executors::ScriptExecutor;

    #[tokio::test]
    async fn test_script_timeout() {
        let executor = ScriptExecutor::new();
        let mut context = create_test_context();
        
        // Set up a command that will timeout (sleep for longer than timeout)
        context.hook_type = HookType::Script {
            command: vec!["sleep".to_string(), "10".to_string()], // Sleep for 10 seconds
            cwd: None,
            environment: HashMap::new(),
            timeout: Some(Duration::from_secs(1)), // But timeout after 1 second
        };
        
        let start = std::time::Instant::now();
        let result = executor.execute(&context).await;
        let duration = start.elapsed();
        
        assert!(result.is_ok());
        let hook_result = result.unwrap();
        
        // Should fail due to timeout
        assert!(!hook_result.success);
        // Should not take much longer than the timeout
        assert!(duration < Duration::from_secs(3));
    }

    #[tokio::test]
    async fn test_hook_error_types() {
        // Test different error types
        let execution_error = HookError::Execution("Test execution error".to_string());
        assert!(matches!(execution_error, HookError::Execution(_)));
        
        let timeout_error = HookError::Timeout("Test timeout".to_string());
        assert!(matches!(timeout_error, HookError::Timeout(_)));
        
        let config_error = HookError::Configuration("Test config error".to_string());
        assert!(matches!(config_error, HookError::Configuration(_)));
    }

    #[tokio::test]
    async fn test_hook_result_success() {
        let result = HookResult::success(
            Some("Test output".to_string()),
            Duration::from_millis(100),
        );
        
        assert!(result.success);
        assert_eq!(result.output, Some("Test output".to_string()));
        assert_eq!(result.duration, Duration::from_millis(100));
        assert!(result.error.is_none());
    }

    #[tokio::test]
    async fn test_hook_result_failure() {
        let result = HookResult::failure(
            "Test error".to_string(),
            Duration::from_millis(50),
        );
        
        assert!(!result.success);
        assert_eq!(result.error, Some("Test error".to_string()));
        assert_eq!(result.duration, Duration::from_millis(50));
        assert!(result.output.is_none());
    }
}

mod execution_results_tests {
    use super::*;
    use crate::hooks::config::HookConfig;

    fn create_test_execution_result(success: bool, required: bool) -> ExecutionResult {
        ExecutionResult {
            execution_id: "test_id".to_string(),
            result: if success {
                HookResult::success(Some("success".to_string()), Duration::from_millis(100))
            } else {
                HookResult::failure("failure".to_string(), Duration::from_millis(100))
            },
            config: HookConfig {
                event: "test.event".to_string(),
                hook_type: HookType::Script {
                    command: vec!["echo".to_string(), "test".to_string()],
                    cwd: None,
                    environment: HashMap::new(),
                    timeout: Some(Duration::from_secs(5)),
                },
                description: Some("Test hook".to_string()),
                enabled: true,
                required,
                timeout: Some(Duration::from_secs(10)),
                mode: HookExecutionMode::Async,
                priority: HookPriority::NORMAL,
                conditions: HashMap::new(),
            },
            duration: Duration::from_millis(100),
            retry_attempts: 0,
            cancelled: false,
            error_details: if success { None } else { Some("failure".to_string()) },
        }
    }

    #[tokio::test]
    async fn test_hook_execution_results_all_success() {
        let results = vec![
            create_test_execution_result(true, false),
            create_test_execution_result(true, true),
        ];
        
        let execution_results = HookExecutionResults::new(results);
        
        assert_eq!(execution_results.successful.len(), 2);
        assert_eq!(execution_results.failed.len(), 0);
        assert_eq!(execution_results.cancelled.len(), 0);
        assert_eq!(execution_results.success_rate, 1.0);
        assert!(!execution_results.has_critical_failures());
    }

    #[tokio::test]
    async fn test_hook_execution_results_with_failures() {
        let results = vec![
            create_test_execution_result(true, false),
            create_test_execution_result(false, false),
            create_test_execution_result(false, true), // Critical failure
        ];
        
        let execution_results = HookExecutionResults::new(results);
        
        assert_eq!(execution_results.successful.len(), 1);
        assert_eq!(execution_results.failed.len(), 2);
        assert_eq!(execution_results.cancelled.len(), 0);
        assert!((execution_results.success_rate - 0.333).abs() < 0.01); // ~33.3%
        assert!(execution_results.has_critical_failures());
    }

    #[tokio::test]
    async fn test_hook_execution_results_summary() {
        let results = vec![
            create_test_execution_result(true, false),
            create_test_execution_result(false, false),
        ];
        
        let execution_results = HookExecutionResults::new(results);
        let summary = execution_results.summary();
        
        assert!(summary.contains("Executed 2 hooks"));
        assert!(summary.contains("1 successful"));
        assert!(summary.contains("1 failed"));
        assert!(summary.contains("0 cancelled"));
        assert!(summary.contains("success rate: 50.0%"));
    }
}

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_end_to_end_hook_execution() {
        let config = create_test_config_with_hooks();
        let manager = HookManager::new(config).await.unwrap();
        
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session_123".to_string(),
            user_id: Some("test_user".to_string()),
        };
        
        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_hook_execution_with_environment_variables() {
        let mut config = create_test_config();
        
        // Add a hook that uses environment variables
        let mut env = HashMap::new();
        env.insert("TEST_VAR".to_string(), "test_value".to_string());
        
        config.hooks.session.push(HookConfig {
            event: "session.start".to_string(),
            hook_type: HookType::Script {
                command: vec!["echo".to_string(), "$TEST_VAR".to_string()],
                cwd: None,
                environment: env,
                timeout: Some(Duration::from_secs(5)),
            },
            description: Some("Test environment hook".to_string()),
            enabled: true,
            required: false,
            timeout: Some(Duration::from_secs(10)),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            conditions: HashMap::new(),
        });
        
        let manager = HookManager::new(config).await.unwrap();
        
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session_123".to_string(),
            user_id: Some("test_user".to_string()),
        };
        
        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }
}
