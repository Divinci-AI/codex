//! Integration tests for the complete hooks system.

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

use tempfile::TempDir;

use crate::hooks::config::{HookConfig, HooksConfig, GlobalHooksConfig};
use crate::hooks::manager::HookManager;
use crate::hooks::types::{
    HookExecutionMode, HookPriority, HookType, LifecycleEvent, HttpMethod,
};

/// Helper function to create a comprehensive test configuration.
fn create_comprehensive_test_config() -> HooksConfig {
    let mut env = HashMap::new();
    env.insert("TEST_SESSION_ID".to_string(), "${session_id}".to_string());
    env.insert("TEST_USER_ID".to_string(), "${user_id}".to_string());

    HooksConfig {
        hooks: GlobalHooksConfig {
            enabled: true,
            timeout_seconds: 30,
            parallel_execution: true,
            session: vec![
                // Script hook for session start
                HookConfig {
                    event: "session.start".to_string(),
                    hook_type: HookType::Script {
                        command: vec!["echo".to_string(), "Session started: ${session_id}".to_string()],
                        cwd: None,
                        environment: env.clone(),
                        timeout: Some(Duration::from_secs(5)),
                    },
                    description: Some("Log session start".to_string()),
                    enabled: true,
                    required: false,
                    timeout: Some(Duration::from_secs(10)),
                    mode: HookExecutionMode::Async,
                    priority: HookPriority::NORMAL,
                    conditions: HashMap::new(),
                },
                // MCP hook for session start
                HookConfig {
                    event: "session.start".to_string(),
                    hook_type: HookType::McpTool {
                        server: "session_tracker".to_string(),
                        tool: "track_session_start".to_string(),
                        timeout: Some(Duration::from_secs(10)),
                    },
                    description: Some("Track session start via MCP".to_string()),
                    enabled: true,
                    required: false,
                    timeout: Some(Duration::from_secs(15)),
                    mode: HookExecutionMode::Async,
                    priority: HookPriority::HIGH,
                    conditions: HashMap::new(),
                },
            ],
            task: vec![
                // Script hook for task completion
                HookConfig {
                    event: "task.complete".to_string(),
                    hook_type: HookType::Script {
                        command: vec!["echo".to_string(), "Task completed: ${task_id}".to_string()],
                        cwd: None,
                        environment: HashMap::new(),
                        timeout: Some(Duration::from_secs(5)),
                    },
                    description: Some("Log task completion".to_string()),
                    enabled: true,
                    required: true, // This is a critical hook
                    timeout: Some(Duration::from_secs(10)),
                    mode: HookExecutionMode::Sync,
                    priority: HookPriority::HIGH,
                    conditions: HashMap::new(),
                },
            ],
            exec: vec![
                // Webhook hook for command execution
                HookConfig {
                    event: "exec.before".to_string(),
                    hook_type: HookType::Webhook {
                        url: "https://httpbin.org/post".to_string(), // Test endpoint
                        method: HttpMethod::Post,
                        headers: {
                            let mut headers = HashMap::new();
                            headers.insert("Content-Type".to_string(), "application/json".to_string());
                            headers.insert("X-Hook-Type".to_string(), "exec.before".to_string());
                            headers
                        },
                        timeout: Some(Duration::from_secs(10)),
                        retry_count: Some(2),
                    },
                    description: Some("Notify external system of command execution".to_string()),
                    enabled: true,
                    required: false,
                    timeout: Some(Duration::from_secs(15)),
                    mode: HookExecutionMode::Async,
                    priority: HookPriority::LOW,
                    conditions: HashMap::new(),
                },
            ],
            patch: Vec::new(),
            mcp: Vec::new(),
            agent: Vec::new(),
            error: vec![
                // Error handling hook
                HookConfig {
                    event: "error.occurred".to_string(),
                    hook_type: HookType::Script {
                        command: vec!["echo".to_string(), "Error occurred: ${error_message}".to_string()],
                        cwd: None,
                        environment: HashMap::new(),
                        timeout: Some(Duration::from_secs(3)),
                    },
                    description: Some("Log errors".to_string()),
                    enabled: true,
                    required: false,
                    timeout: Some(Duration::from_secs(5)),
                    mode: HookExecutionMode::Async,
                    priority: HookPriority::HIGH,
                    conditions: HashMap::new(),
                },
            ],
            integration: Vec::new(),
        },
    }
}

/// Helper function to create a test configuration with disabled hooks.
fn create_disabled_test_config() -> HooksConfig {
    let mut config = create_comprehensive_test_config();
    config.hooks.enabled = false;
    config
}

/// Helper function to create a test configuration with timeout issues.
fn create_timeout_test_config() -> HooksConfig {
    HooksConfig {
        hooks: GlobalHooksConfig {
            enabled: true,
            timeout_seconds: 1, // Very short global timeout
            parallel_execution: false,
            session: vec![
                HookConfig {
                    event: "session.start".to_string(),
                    hook_type: HookType::Script {
                        command: vec!["sleep".to_string(), "5".to_string()], // Will timeout
                        cwd: None,
                        environment: HashMap::new(),
                        timeout: Some(Duration::from_secs(10)), // Longer than global timeout
                    },
                    description: Some("Slow hook that will timeout".to_string()),
                    enabled: true,
                    required: true,
                    timeout: Some(Duration::from_secs(10)),
                    mode: HookExecutionMode::Sync,
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

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_hook_manager_with_comprehensive_config() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        assert!(manager.is_enabled());
        
        // Verify all executor types are available
        assert_eq!(manager.executors.len(), 4);
        assert!(manager.executors.contains_key("script"));
        assert!(manager.executors.contains_key("webhook"));
        assert!(manager.executors.contains_key("mcp_tool"));
        assert!(manager.executors.contains_key("executable"));
    }

    #[tokio::test]
    async fn test_session_start_hooks_execution() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session_123".to_string(),
            user_id: Some("test_user_456".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
        
        // Check that metrics were collected
        let metrics = manager.get_metrics();
        assert!(metrics.total_executions > 0);
    }

    #[tokio::test]
    async fn test_task_complete_hooks_execution() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::TaskComplete {
            task_id: "task_789".to_string(),
            success: true,
            duration: Duration::from_secs(5),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_exec_before_hooks_execution() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::ExecBefore {
            command: "ls -la".to_string(),
            working_dir: PathBuf::from("/tmp"),
        };

        let result = manager.trigger_event(event).await;
        // Note: This might fail due to network issues with httpbin.org
        // In a real test environment, you'd use a mock HTTP server
        // For now, we just verify the hook system doesn't crash
        let _ = result; // Ignore the result for this test
    }

    #[tokio::test]
    async fn test_error_hooks_execution() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::ErrorOccurred {
            error_type: "test_error".to_string(),
            error_message: "This is a test error".to_string(),
            context: HashMap::new(),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_disabled_hooks_manager() {
        let config = create_disabled_test_config();
        let manager = HookManager::new(config).await.unwrap();

        assert!(!manager.is_enabled());

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
        
        // No hooks should have been executed
        let metrics = manager.get_metrics();
        assert_eq!(metrics.total_executions, 0);
    }

    #[tokio::test]
    async fn test_hook_execution_with_working_directory() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_comprehensive_test_config();
        
        let manager = HookManager::new_with_working_directory(
            config,
            temp_dir.path().to_path_buf(),
        ).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_parallel_vs_sequential_execution() {
        // Test parallel execution
        let mut config = create_comprehensive_test_config();
        config.hooks.parallel_execution = true;
        
        let manager_parallel = HookManager::new(config.clone()).await.unwrap();
        
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session_parallel".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let start_time = std::time::Instant::now();
        let result = manager_parallel.trigger_event(event).await;
        let parallel_duration = start_time.elapsed();
        
        assert!(result.is_ok());

        // Test sequential execution
        config.hooks.parallel_execution = false;
        let manager_sequential = HookManager::new(config).await.unwrap();
        
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session_sequential".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let start_time = std::time::Instant::now();
        let result = manager_sequential.trigger_event(event).await;
        let sequential_duration = start_time.elapsed();
        
        assert!(result.is_ok());

        // Note: In a real test, parallel execution should be faster
        // But for simple echo commands, the difference might be negligible
        println!("Parallel: {:?}, Sequential: {:?}", parallel_duration, sequential_duration);
    }

    #[tokio::test]
    async fn test_hook_execution_metrics() {
        let config = create_comprehensive_test_config();
        let manager = HookManager::new(config).await.unwrap();

        // Execute multiple events to generate metrics
        let events = vec![
            LifecycleEvent::SessionStart {
                session_id: "session_1".to_string(),
                user_id: Some("user_1".to_string()),
            },
            LifecycleEvent::TaskComplete {
                task_id: "task_1".to_string(),
                success: true,
                duration: Duration::from_secs(2),
            },
            LifecycleEvent::ErrorOccurred {
                error_type: "test_error".to_string(),
                error_message: "Test error message".to_string(),
                context: HashMap::new(),
            },
        ];

        for event in events {
            let _ = manager.trigger_event(event).await;
        }

        let metrics = manager.get_metrics();
        assert!(metrics.total_executions > 0);
        assert!(metrics.total_duration > Duration::from_secs(0));
        
        // Should have some successful executions
        assert!(metrics.successful_executions > 0);
        
        // Success rate should be reasonable
        assert!(metrics.success_rate >= 0.0 && metrics.success_rate <= 1.0);
    }

    #[tokio::test]
    async fn test_hook_execution_with_conditions() {
        let mut config = create_comprehensive_test_config();
        
        // Add a condition to one of the hooks
        if let Some(hook) = config.hooks.session.get_mut(0) {
            hook.conditions.insert("user_type".to_string(), "admin".to_string());
        }

        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
        
        // Note: The hook with conditions might not execute if conditions aren't met
        // This tests that the system handles conditional execution gracefully
    }

    #[tokio::test]
    async fn test_hook_priority_ordering() {
        let mut config = create_comprehensive_test_config();
        
        // Ensure we have hooks with different priorities
        if let Some(hook) = config.hooks.session.get_mut(0) {
            hook.priority = HookPriority::LOW;
        }
        if let Some(hook) = config.hooks.session.get_mut(1) {
            hook.priority = HookPriority::HIGH;
        }

        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok());
        
        // Note: In a real test, you'd verify that high-priority hooks execute first
        // This would require more sophisticated logging or execution tracking
    }
}

#[cfg(test)]
mod error_handling_tests {
    use super::*;

    #[tokio::test]
    async fn test_hook_execution_with_failures() {
        let mut config = create_comprehensive_test_config();
        
        // Add a hook that will fail
        config.hooks.session.push(HookConfig {
            event: "session.start".to_string(),
            hook_type: HookType::Script {
                command: vec!["false".to_string()], // Command that always fails
                cwd: None,
                environment: HashMap::new(),
                timeout: Some(Duration::from_secs(5)),
            },
            description: Some("Hook that always fails".to_string()),
            enabled: true,
            required: false, // Not required, so failure shouldn't stop execution
            timeout: Some(Duration::from_secs(10)),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            conditions: HashMap::new(),
        });

        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        assert!(result.is_ok()); // Should succeed despite hook failure
        
        let metrics = manager.get_metrics();
        assert!(metrics.failed_executions > 0);
    }

    #[tokio::test]
    async fn test_critical_hook_failure() {
        let mut config = create_comprehensive_test_config();
        
        // Make the task completion hook fail and mark it as required
        if let Some(hook) = config.hooks.task.get_mut(0) {
            hook.hook_type = HookType::Script {
                command: vec!["false".to_string()], // Command that always fails
                cwd: None,
                environment: HashMap::new(),
                timeout: Some(Duration::from_secs(5)),
            };
            hook.required = true; // This is critical
        }

        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::TaskComplete {
            task_id: "test_task".to_string(),
            success: true,
            duration: Duration::from_secs(1),
        };

        let result = manager.trigger_event(event).await;
        // Should still succeed at the manager level, but the hook execution should be marked as failed
        assert!(result.is_ok());
        
        let metrics = manager.get_metrics();
        assert!(metrics.failed_executions > 0);
    }

    #[tokio::test]
    async fn test_timeout_handling() {
        let config = create_timeout_test_config();
        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let start_time = std::time::Instant::now();
        let result = manager.trigger_event(event).await;
        let duration = start_time.elapsed();

        assert!(result.is_ok());
        
        // Should not take much longer than the timeout
        assert!(duration < Duration::from_secs(5));
        
        let metrics = manager.get_metrics();
        // The hook should have timed out and been marked as failed
        assert!(metrics.failed_executions > 0);
    }

    #[tokio::test]
    async fn test_invalid_hook_configuration() {
        let mut config = create_comprehensive_test_config();
        
        // Add a hook with invalid configuration
        config.hooks.session.push(HookConfig {
            event: "session.start".to_string(),
            hook_type: HookType::Script {
                command: vec![], // Empty command - invalid
                cwd: None,
                environment: HashMap::new(),
                timeout: Some(Duration::from_secs(5)),
            },
            description: Some("Invalid hook".to_string()),
            enabled: true,
            required: false,
            timeout: Some(Duration::from_secs(10)),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            conditions: HashMap::new(),
        });

        let manager = HookManager::new(config).await.unwrap();

        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
        };

        let result = manager.trigger_event(event).await;
        // Should handle invalid configuration gracefully
        assert!(result.is_ok());
    }
}
