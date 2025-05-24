//! Unit tests for individual hook executors.

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

use crate::hooks::config::HookConfig;
use crate::hooks::context::HookContext;
use crate::hooks::executor::HookExecutor;
use crate::hooks::executors::{ScriptExecutor, WebhookExecutor, McpToolExecutor};
use crate::hooks::types::{
    HookExecutionMode, HookPriority, HookType, LifecycleEvent, HttpMethod,
};

/// Helper function to create a test context for script execution.
fn create_script_context(command: Vec<String>) -> HookContext {
    let event = LifecycleEvent::SessionStart {
        session_id: "test_session".to_string(),
        user_id: Some("test_user".to_string()),
    };
    
    let working_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp"));
    
    let hook_type = HookType::Script {
        command,
        cwd: None,
        environment: HashMap::new(),
        timeout: Some(Duration::from_secs(5)),
    };
    
    let config = HookConfig {
        event: "session.start".to_string(),
        hook_type: hook_type.clone(),
        description: Some("Test script hook".to_string()),
        enabled: true,
        required: false,
        timeout: Some(Duration::from_secs(10)),
        mode: HookExecutionMode::Async,
        priority: HookPriority::NORMAL,
        conditions: HashMap::new(),
    };
    
    HookContext::new(event, working_dir, hook_type, config)
}

/// Helper function to create a test context for webhook execution.
fn create_webhook_context(url: String, method: HttpMethod) -> HookContext {
    let event = LifecycleEvent::SessionStart {
        session_id: "test_session".to_string(),
        user_id: Some("test_user".to_string()),
    };
    
    let working_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp"));
    
    let hook_type = HookType::Webhook {
        url,
        method,
        headers: HashMap::new(),
        timeout: Some(Duration::from_secs(10)),
        retry_count: Some(3),
    };
    
    let config = HookConfig {
        event: "session.start".to_string(),
        hook_type: hook_type.clone(),
        description: Some("Test webhook hook".to_string()),
        enabled: true,
        required: false,
        timeout: Some(Duration::from_secs(15)),
        mode: HookExecutionMode::Async,
        priority: HookPriority::NORMAL,
        conditions: HashMap::new(),
    };
    
    HookContext::new(event, working_dir, hook_type, config)
}

/// Helper function to create a test context for MCP tool execution.
fn create_mcp_context(server: String, tool: String) -> HookContext {
    let event = LifecycleEvent::SessionStart {
        session_id: "test_session".to_string(),
        user_id: Some("test_user".to_string()),
    };
    
    let working_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp"));
    
    let hook_type = HookType::McpTool {
        server,
        tool,
        timeout: Some(Duration::from_secs(15)),
    };
    
    let config = HookConfig {
        event: "session.start".to_string(),
        hook_type: hook_type.clone(),
        description: Some("Test MCP hook".to_string()),
        enabled: true,
        required: false,
        timeout: Some(Duration::from_secs(20)),
        mode: HookExecutionMode::Async,
        priority: HookPriority::NORMAL,
        conditions: HashMap::new(),
    };
    
    HookContext::new(event, working_dir, hook_type, config)
}

#[cfg(test)]
mod script_executor_tests {
    use super::*;

    #[tokio::test]
    async fn test_script_executor_creation() {
        let executor = ScriptExecutor::new();
        assert_eq!(executor.executor_type(), "script");
        assert!(executor.default_shell.contains("sh") || executor.default_shell.contains("bash"));
    }

    #[tokio::test]
    async fn test_script_executor_can_execute() {
        let executor = ScriptExecutor::new();
        let context = create_script_context(vec!["echo".to_string(), "test".to_string()]);
        
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_script_executor_cannot_execute_webhook() {
        let executor = ScriptExecutor::new();
        let context = create_webhook_context(
            "https://example.com".to_string(),
            HttpMethod::Post,
        );
        
        assert!(!executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_script_executor_simple_command() {
        let executor = ScriptExecutor::new();
        let context = create_script_context(vec!["echo".to_string(), "hello world".to_string()]);
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        assert!(hook_result.success);
        assert!(hook_result.output.is_some());
        
        let output = hook_result.output.unwrap();
        assert!(output.contains("hello world"));
    }

    #[tokio::test]
    async fn test_script_executor_command_with_exit_code() {
        let executor = ScriptExecutor::new();
        let context = create_script_context(vec!["exit".to_string(), "1".to_string()]);
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        assert!(!hook_result.success); // Should fail due to non-zero exit code
        assert!(hook_result.error.is_some());
    }

    #[tokio::test]
    async fn test_script_executor_nonexistent_command() {
        let executor = ScriptExecutor::new();
        let context = create_script_context(vec!["nonexistent_command_xyz123".to_string()]);
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        assert!(!hook_result.success);
        assert!(hook_result.error.is_some());
    }

    #[tokio::test]
    async fn test_script_executor_with_environment() {
        let executor = ScriptExecutor::new();
        let mut context = create_script_context(vec!["echo".to_string(), "$TEST_VAR".to_string()]);
        
        // Add environment variable to the hook type
        if let HookType::Script { ref mut environment, .. } = context.hook_type {
            environment.insert("TEST_VAR".to_string(), "test_value".to_string());
        }
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        assert!(hook_result.success);
        assert!(hook_result.output.is_some());
        
        let output = hook_result.output.unwrap();
        assert!(output.contains("test_value"));
    }

    #[tokio::test]
    async fn test_script_executor_timeout() {
        let executor = ScriptExecutor::new();
        let mut context = create_script_context(vec!["sleep".to_string(), "10".to_string()]);
        
        // Set a short timeout
        if let HookType::Script { ref mut timeout, .. } = context.hook_type {
            *timeout = Some(Duration::from_secs(1));
        }
        
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
    async fn test_script_executor_estimated_duration() {
        let executor = ScriptExecutor::new();
        let estimated = executor.estimated_duration();
        
        assert!(estimated.is_some());
        assert!(estimated.unwrap() > Duration::from_secs(0));
    }
}

#[cfg(test)]
mod webhook_executor_tests {
    use super::*;

    #[tokio::test]
    async fn test_webhook_executor_creation() {
        let executor = WebhookExecutor::new();
        assert_eq!(executor.executor_type(), "webhook");
    }

    #[tokio::test]
    async fn test_webhook_executor_can_execute() {
        let executor = WebhookExecutor::new();
        let context = create_webhook_context(
            "https://example.com/webhook".to_string(),
            HttpMethod::Post,
        );
        
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_webhook_executor_cannot_execute_script() {
        let executor = WebhookExecutor::new();
        let context = create_script_context(vec!["echo".to_string(), "test".to_string()]);
        
        assert!(!executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_webhook_executor_estimated_duration() {
        let executor = WebhookExecutor::new();
        let estimated = executor.estimated_duration();
        
        assert!(estimated.is_some());
        assert!(estimated.unwrap() >= Duration::from_secs(5));
    }

    #[tokio::test]
    async fn test_webhook_executor_default_config() {
        let executor = WebhookExecutor::new();
        let config = executor.default_config();
        
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert!(config.isolated);
        assert!(config.max_retries > 0);
    }

    // Note: We can't easily test actual webhook execution without a test server
    // In a real test environment, you might use wiremock or similar for HTTP mocking
}

#[cfg(test)]
mod mcp_executor_tests {
    use super::*;

    #[tokio::test]
    async fn test_mcp_executor_creation() {
        let executor = McpToolExecutor::new();
        assert_eq!(executor.executor_type(), "mcp_tool");
    }

    #[tokio::test]
    async fn test_mcp_executor_can_execute() {
        let executor = McpToolExecutor::new();
        let context = create_mcp_context(
            "test_server".to_string(),
            "test_tool".to_string(),
        );
        
        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_mcp_executor_cannot_execute_script() {
        let executor = McpToolExecutor::new();
        let context = create_script_context(vec!["echo".to_string(), "test".to_string()]);
        
        assert!(!executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_mcp_executor_execution() {
        let executor = McpToolExecutor::new();
        let context = create_mcp_context(
            "test_server".to_string(),
            "test_tool".to_string(),
        );
        
        let result = executor.execute(&context).await;
        assert!(result.is_ok());
        
        let hook_result = result.unwrap();
        // MCP executor currently simulates success
        assert!(hook_result.success);
        assert!(hook_result.output.is_some());
    }

    #[tokio::test]
    async fn test_mcp_executor_estimated_duration() {
        let executor = McpToolExecutor::new();
        let estimated = executor.estimated_duration();
        
        assert!(estimated.is_some());
        assert!(estimated.unwrap() >= Duration::from_secs(5));
    }

    #[tokio::test]
    async fn test_mcp_executor_default_config() {
        let executor = McpToolExecutor::new();
        let config = executor.default_config();
        
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert!(config.isolated);
        assert!(config.max_retries > 0);
    }
}

#[cfg(test)]
mod executor_trait_tests {
    use super::*;
    use crate::hooks::executor::ExecutionConfig;

    #[tokio::test]
    async fn test_all_executors_implement_trait() {
        let script_executor = ScriptExecutor::new();
        let webhook_executor = WebhookExecutor::new();
        let mcp_executor = McpToolExecutor::new();
        
        // Test that all executors implement the trait methods
        assert!(!script_executor.executor_type().is_empty());
        assert!(!webhook_executor.executor_type().is_empty());
        assert!(!mcp_executor.executor_type().is_empty());
        
        // Test that all have estimated durations
        assert!(script_executor.estimated_duration().is_some());
        assert!(webhook_executor.estimated_duration().is_some());
        assert!(mcp_executor.estimated_duration().is_some());
    }

    #[tokio::test]
    async fn test_executor_default_configs() {
        let script_executor = ScriptExecutor::new();
        let webhook_executor = WebhookExecutor::new();
        let mcp_executor = McpToolExecutor::new();
        
        let script_config = script_executor.default_config();
        let webhook_config = webhook_executor.default_config();
        let mcp_config = mcp_executor.default_config();
        
        // All should have reasonable defaults
        assert!(script_config.timeout > Duration::from_secs(0));
        assert!(webhook_config.timeout > Duration::from_secs(0));
        assert!(mcp_config.timeout > Duration::from_secs(0));
        
        // All should have retry capabilities
        assert!(script_config.max_retries >= 0);
        assert!(webhook_config.max_retries >= 0);
        assert!(mcp_config.max_retries >= 0);
    }
}
