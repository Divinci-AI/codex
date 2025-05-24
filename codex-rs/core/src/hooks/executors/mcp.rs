//! MCP tool executor for calling MCP tools as hooks.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::{json, Value};
use tracing::{debug, error, info, warn};

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{HookError, HookExecutionMode, HookPriority, HookResult, HookType};

/// Executor for calling MCP tools as hooks.
#[derive(Debug, Clone)]
pub struct McpToolExecutor {
    /// Default timeout for MCP tool calls.
    default_timeout: Duration,
    /// Maximum response size to capture.
    max_response_size: usize,
    /// Default server configuration.
    default_server: Option<String>,
}

impl Default for McpToolExecutor {
    fn default() -> Self {
        Self::new()
    }
}

impl McpToolExecutor {
    /// Create a new MCP tool executor with default settings.
    pub fn new() -> Self {
        Self {
            default_timeout: Duration::from_secs(60),
            max_response_size: 1024 * 1024, // 1MB default
            default_server: None,
        }
    }

    /// Create an MCP tool executor with custom timeout.
    pub fn with_timeout(timeout: Duration) -> Self {
        Self {
            default_timeout: timeout,
            max_response_size: 1024 * 1024,
            default_server: None,
        }
    }

    /// Set default MCP server to use.
    pub fn with_default_server<S: Into<String>>(mut self, server: S) -> Self {
        self.default_server = Some(server.into());
        self
    }

    /// Set maximum response size to capture.
    pub fn with_max_response_size(mut self, size: usize) -> Self {
        self.max_response_size = size;
        self
    }

    /// Extract MCP tool configuration from hook context.
    fn extract_mcp_config(&self, context: &HookContext) -> Result<McpConfig, HookError> {
        match &context.hook_type {
            HookType::McpTool { server, tool, timeout: _ } => {
                if tool.is_empty() {
                    return Err(HookError::Configuration("MCP tool name cannot be empty".to_string()));
                }

                let server_name = if server.is_empty() {
                    self.default_server.clone()
                        .ok_or_else(|| HookError::Configuration(
                            "MCP server must be specified either in hook config or executor default".to_string()
                        ))?
                } else {
                    server.clone()
                };

                Ok(McpConfig {
                    tool_name: tool.clone(),
                    server: server_name,
                    arguments: HashMap::new(), // No arguments in the hook type, use empty map
                })
            }
            _ => Err(HookError::Configuration(
                "McpToolExecutor can only execute McpTool hooks".to_string(),
            )),
        }
    }

    /// Build arguments for MCP tool call from hook context.
    fn build_tool_arguments(&self, context: &HookContext, base_args: &HashMap<String, Value>) -> HashMap<String, Value> {
        let mut args = base_args.clone();

        // Add context information as arguments
        args.insert("codex_event_type".to_string(), json!(context.event.event_type().to_string()));
        args.insert("codex_timestamp".to_string(), json!(chrono::Utc::now().to_rfc3339()));
        args.insert("codex_working_dir".to_string(), json!(context.working_directory.to_string_lossy()));

        // Add event-specific arguments
        match &context.event {
            crate::hooks::types::LifecycleEvent::SessionStart { session_id, model, cwd, .. } => {
                args.insert("session_id".to_string(), json!(session_id));
                args.insert("model".to_string(), json!(model));
                args.insert("cwd".to_string(), json!(cwd.to_string_lossy()));
            }
            crate::hooks::types::LifecycleEvent::SessionEnd { session_id, duration, .. } => {
                args.insert("session_id".to_string(), json!(session_id));
                args.insert("duration_ms".to_string(), json!(duration.as_millis()));
            }
            crate::hooks::types::LifecycleEvent::TaskStart { task_id, session_id, prompt, .. } => {
                args.insert("task_id".to_string(), json!(task_id));
                args.insert("session_id".to_string(), json!(session_id));
                args.insert("prompt".to_string(), json!(prompt));
            }
            crate::hooks::types::LifecycleEvent::TaskComplete { task_id, session_id, success, duration, .. } => {
                args.insert("task_id".to_string(), json!(task_id));
                args.insert("session_id".to_string(), json!(session_id));
                args.insert("success".to_string(), json!(success));
                args.insert("duration_ms".to_string(), json!(duration.as_millis()));
            }
            crate::hooks::types::LifecycleEvent::ExecBefore { command, cwd, .. } => {
                args.insert("command".to_string(), json!(command));
                args.insert("exec_cwd".to_string(), json!(cwd.to_string_lossy()));
            }
            crate::hooks::types::LifecycleEvent::ExecAfter { command, exit_code, duration, .. } => {
                args.insert("command".to_string(), json!(command));
                args.insert("exit_code".to_string(), json!(exit_code));
                args.insert("duration_ms".to_string(), json!(duration.as_millis()));
            }
            crate::hooks::types::LifecycleEvent::PatchBefore { changes, .. } => {
                args.insert("changes".to_string(), json!(changes));
            }
            crate::hooks::types::LifecycleEvent::PatchAfter { applied_files, success, .. } => {
                args.insert("applied_files".to_string(), json!(applied_files));
                args.insert("success".to_string(), json!(success));
            }
            crate::hooks::types::LifecycleEvent::McpToolBefore { server, tool, .. } => {
                args.insert("server".to_string(), json!(server));
                args.insert("tool".to_string(), json!(tool));
            }
            crate::hooks::types::LifecycleEvent::McpToolAfter { server, tool, success, duration, .. } => {
                args.insert("server".to_string(), json!(server));
                args.insert("tool".to_string(), json!(tool));
                args.insert("success".to_string(), json!(success));
                args.insert("duration_ms".to_string(), json!(duration.as_millis()));
            }
            crate::hooks::types::LifecycleEvent::AgentMessage { message, reasoning, .. } => {
                args.insert("message".to_string(), json!(message));
                if let Some(reasoning) = reasoning {
                    args.insert("reasoning".to_string(), json!(reasoning));
                }
            }
            crate::hooks::types::LifecycleEvent::ErrorOccurred { error, context: error_context, .. } => {
                args.insert("error".to_string(), json!(error));
                args.insert("error_context".to_string(), json!(error_context));
            }
        }

        // Add environment variables as arguments
        for (key, value) in &context.environment {
            args.insert(format!("env_{}", key.to_lowercase()), json!(value));
        }

        args
    }

    /// Execute MCP tool call.
    async fn execute_mcp_tool(&self, config: McpConfig, arguments: HashMap<String, Value>) -> Result<McpResult, HookError> {
        let start_time = Instant::now();

        debug!("Calling MCP tool: {} on server: {}", config.tool_name, config.server);

        // TODO: This is a placeholder implementation. In a real implementation, this would:
        // 1. Connect to the specified MCP server
        // 2. Call the tool with the provided arguments
        // 3. Handle the response and any errors
        // 4. Return the result

        // For now, we'll simulate the MCP tool call
        let result = self.simulate_mcp_call(&config, &arguments).await?;

        let duration = start_time.elapsed();

        debug!(
            "MCP tool call completed: tool={}, success={}, duration={:?}",
            config.tool_name, result.success, duration
        );

        Ok(McpResult {
            tool_name: config.tool_name,
            server: config.server,
            success: result.success,
            result: result.result,
            error: result.error,
            duration,
            arguments,
        })
    }

    /// Simulate MCP tool call (placeholder implementation).
    async fn simulate_mcp_call(&self, config: &McpConfig, arguments: &HashMap<String, Value>) -> Result<SimulatedMcpResult, HookError> {
        // This is a placeholder that simulates different MCP tool behaviors
        // In a real implementation, this would be replaced with actual MCP client calls

        tokio::time::sleep(Duration::from_millis(100)).await; // Simulate network delay

        match config.tool_name.as_str() {
            "log_event" => {
                // Simulate a logging tool that always succeeds
                Ok(SimulatedMcpResult {
                    success: true,
                    result: Some(json!({
                        "logged": true,
                        "event_type": arguments.get("codex_event_type"),
                        "timestamp": arguments.get("codex_timestamp")
                    })),
                    error: None,
                })
            }
            "validate_data" => {
                // Simulate a validation tool that sometimes fails
                let has_required_field = arguments.contains_key("task_id") || arguments.contains_key("session_id");
                if has_required_field {
                    Ok(SimulatedMcpResult {
                        success: true,
                        result: Some(json!({"validation": "passed", "fields_checked": arguments.len()})),
                        error: None,
                    })
                } else {
                    Ok(SimulatedMcpResult {
                        success: false,
                        result: None,
                        error: Some("Missing required fields for validation".to_string()),
                    })
                }
            }
            "send_notification" => {
                // Simulate a notification tool
                Ok(SimulatedMcpResult {
                    success: true,
                    result: Some(json!({
                        "notification_sent": true,
                        "recipient": "default",
                        "message": format!("Codex event: {}", arguments.get("codex_event_type").unwrap_or(&json!("unknown")))
                    })),
                    error: None,
                })
            }
            "failing_tool" => {
                // Simulate a tool that always fails
                Ok(SimulatedMcpResult {
                    success: false,
                    result: None,
                    error: Some("This tool is designed to fail for testing purposes".to_string()),
                })
            }
            _ => {
                // Unknown tool
                Err(HookError::Execution(format!("Unknown MCP tool: {}", config.tool_name)))
            }
        }
    }
}

#[async_trait]
impl HookExecutor for McpToolExecutor {
    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        info!("Executing MCP tool hook for event: {:?}", context.event.event_type());

        // Extract MCP configuration
        let mcp_config = self.extract_mcp_config(context)?;

        // Build tool arguments
        let arguments = self.build_tool_arguments(context, &mcp_config.arguments);

        // Execute the MCP tool
        match self.execute_mcp_tool(mcp_config, arguments).await {
            Ok(result) => {
                if result.success {
                    info!(
                        "MCP tool hook executed successfully: tool={}, duration={:?}",
                        result.tool_name, result.duration
                    );

                    let output = Some(format!(
                        "MCP tool '{}' executed successfully on server '{}': {:?}",
                        result.tool_name, result.server, result.result
                    ));

                    Ok(HookResult::success(output, start_time.elapsed()))
                } else {
                    warn!(
                        "MCP tool hook failed: tool={}, error={}",
                        result.tool_name,
                        result.error.as_deref().unwrap_or("Unknown error")
                    );

                    let error_msg = format!(
                        "MCP tool '{}' failed: {}",
                        result.tool_name,
                        result.error.as_deref().unwrap_or("Unknown error")
                    );

                    Ok(HookResult::failure(error_msg, start_time.elapsed()))
                }
            }
            Err(e) => {
                error!("MCP tool hook execution error: {}", e);
                Ok(HookResult::failure(e.to_string(), start_time.elapsed()))
            }
        }
    }

    fn executor_type(&self) -> &'static str {
        "mcp_tool"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::McpTool { .. })
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(15)) // MCP tools can be complex
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: Duration::from_secs(120),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            required: false,
            max_retries: 2,
            retry_delay: Duration::from_secs(2),
            isolated: true,
        }
    }

    async fn prepare(&self, context: &HookContext) -> Result<(), HookError> {
        // Validate MCP configuration
        let _config = self.extract_mcp_config(context)?;

        // TODO: In a real implementation, this would:
        // 1. Check if the MCP server is available
        // 2. Verify that the tool exists on the server
        // 3. Validate the tool's schema if available

        Ok(())
    }

    async fn cleanup(&self, _context: &HookContext) -> Result<(), HookError> {
        // TODO: In a real implementation, this might:
        // 1. Close any open MCP connections
        // 2. Clean up temporary resources
        // 3. Log cleanup completion

        Ok(())
    }
}

/// Configuration for MCP tool execution.
#[derive(Debug, Clone)]
struct McpConfig {
    /// Name of the MCP tool to call.
    tool_name: String,
    /// MCP server to call the tool on.
    server: String,
    /// Arguments to pass to the tool.
    arguments: HashMap<String, Value>,
}

/// Result of MCP tool execution.
#[derive(Debug, Clone)]
struct McpResult {
    /// Name of the tool that was called.
    tool_name: String,
    /// Server the tool was called on.
    server: String,
    /// Whether the tool call was successful.
    success: bool,
    /// Result data from the tool.
    result: Option<Value>,
    /// Error message if the tool failed.
    error: Option<String>,
    /// Duration of the tool call.
    duration: Duration,
    /// Arguments that were passed to the tool.
    arguments: HashMap<String, Value>,
}

/// Simulated MCP result (placeholder).
#[derive(Debug, Clone)]
struct SimulatedMcpResult {
    success: bool,
    result: Option<Value>,
    error: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::types::LifecycleEvent;
    use std::path::PathBuf;

    fn create_test_context(tool_name: String, server: Option<String>) -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp")),
            timestamp: chrono::Utc::now(),
        };

        let hook_type = HookType::McpTool {
            server: server.unwrap_or_default(),
            tool: tool_name,
            timeout: None,
        };

        HookContext::new(event, PathBuf::from("/tmp"))
            .with_hook_type(hook_type)
    }

    #[tokio::test]
    async fn test_mcp_executor_creation() {
        let executor = McpToolExecutor::new();
        assert_eq!(executor.executor_type(), "mcp_tool");
        assert_eq!(executor.default_timeout, Duration::from_secs(60));
        assert_eq!(executor.max_response_size, 1024 * 1024);
    }

    #[tokio::test]
    async fn test_mcp_executor_with_default_server() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        assert_eq!(executor.default_server, Some("test-server".to_string()));
    }

    #[tokio::test]
    async fn test_mcp_executor_can_execute() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("log_event".to_string(), None);

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_successful_mcp_tool_execution() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("log_event".to_string(), None);

        let result = executor.execute(&context).await.unwrap();

        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("log_event"));
    }

    #[tokio::test]
    async fn test_failed_mcp_tool_execution() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("failing_tool".to_string(), None);

        let result = executor.execute(&context).await.unwrap();

        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.error.unwrap().contains("designed to fail"));
    }

    #[tokio::test]
    async fn test_mcp_tool_with_validation() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("validate_data".to_string(), None);

        let result = executor.execute(&context).await.unwrap();

        // Should succeed because SessionStart event includes session_id
        assert!(result.success);
        assert!(result.output.is_some());
    }

    #[tokio::test]
    async fn test_mcp_tool_arguments_building() {
        let executor = McpToolExecutor::new();
        let context = create_test_context("log_event".to_string(), Some("test-server".to_string()));

        let base_args = HashMap::new();
        let args = executor.build_tool_arguments(&context, &base_args);

        assert!(args.contains_key("codex_event_type"));
        assert!(args.contains_key("codex_timestamp"));
        assert!(args.contains_key("session_id"));
        assert!(args.contains_key("model"));
        assert_eq!(args["session_id"], json!("test-session"));
        assert_eq!(args["model"], json!("test-model"));
    }

    #[tokio::test]
    async fn test_mcp_preparation() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("log_event".to_string(), None);

        let result = executor.prepare(&context).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_mcp_cleanup() {
        let executor = McpToolExecutor::new().with_default_server("test-server");
        let context = create_test_context("log_event".to_string(), None);

        let result = executor.cleanup(&context).await;
        assert!(result.is_ok());
    }

    #[test]
    fn test_mcp_executor_default_config() {
        let executor = McpToolExecutor::new();
        let config = executor.default_config();

        assert_eq!(config.timeout, Duration::from_secs(120));
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert_eq!(config.max_retries, 2);
        assert!(config.isolated);
    }

    #[tokio::test]
    async fn test_missing_server_configuration() {
        let executor = McpToolExecutor::new(); // No default server
        let context = create_test_context("log_event".to_string(), None); // No server in hook

        let result = executor.extract_mcp_config(&context);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("server must be specified"));
    }
}
