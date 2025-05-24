//! Webhook executor for sending HTTP requests as hooks.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use reqwest::{Client, Method, RequestBuilder};
use serde_json::{json, Value};
use tracing::{debug, error, info, warn};

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{HookError, HookExecutionMode, HookPriority, HookResult, HookType};

/// Executor for sending HTTP webhook requests.
#[derive(Debug, Clone)]
pub struct WebhookExecutor {
    /// HTTP client for making requests.
    client: Client,
    /// Default timeout for HTTP requests.
    default_timeout: Duration,
    /// Maximum response size to capture.
    max_response_size: usize,
    /// Default headers to include in all requests.
    default_headers: HashMap<String, String>,
}

impl Default for WebhookExecutor {
    fn default() -> Self {
        Self::new()
    }
}

impl WebhookExecutor {
    /// Create a new webhook executor with default settings.
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(60))
            .user_agent("Codex-Hooks/1.0")
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            default_timeout: Duration::from_secs(30),
            max_response_size: 1024 * 1024, // 1MB default
            default_headers: HashMap::new(),
        }
    }

    /// Create a webhook executor with custom timeout.
    pub fn with_timeout(timeout: Duration) -> Self {
        let client = Client::builder()
            .timeout(timeout)
            .user_agent("Codex-Hooks/1.0")
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            default_timeout: timeout,
            max_response_size: 1024 * 1024,
            default_headers: HashMap::new(),
        }
    }

    /// Add default headers to include in all requests.
    pub fn with_default_headers(mut self, headers: HashMap<String, String>) -> Self {
        self.default_headers = headers;
        self
    }

    /// Set maximum response size to capture.
    pub fn with_max_response_size(mut self, size: usize) -> Self {
        self.max_response_size = size;
        self
    }

    /// Extract webhook configuration from hook context.
    fn extract_webhook_config(&self, context: &HookContext) -> Result<WebhookConfig, HookError> {
        match &context.hook_type {
            HookType::Webhook { url, method, headers, timeout: _, retry_count: _ } => {
                if url.is_empty() {
                    return Err(HookError::Configuration("Webhook URL cannot be empty".to_string()));
                }

                // Convert HttpMethod to reqwest::Method
                let http_method = match method {
                    crate::hooks::types::HttpMethod::Get => Method::GET,
                    crate::hooks::types::HttpMethod::Post => Method::POST,
                    crate::hooks::types::HttpMethod::Put => Method::PUT,
                    crate::hooks::types::HttpMethod::Patch => Method::PATCH,
                    crate::hooks::types::HttpMethod::Delete => Method::DELETE,
                };

                Ok(WebhookConfig {
                    url: url.clone(),
                    method: http_method,
                    headers: headers.clone(),
                    body: None, // We'll use the generated payload
                    auth: None, // TODO: Add auth support later
                })
            }
            _ => Err(HookError::Configuration(
                "WebhookExecutor can only execute Webhook hooks".to_string(),
            )),
        }
    }

    /// Build the request payload from hook context.
    fn build_payload(&self, context: &HookContext) -> Value {
        let mut payload = json!({
            "event": {
                "type": context.event.event_type().to_string(),
                "timestamp": chrono::Utc::now().to_rfc3339(),
            },
            "hook": {
                "type": "webhook",
                "working_dir": context.working_directory.to_string_lossy(),
            },
            "environment": context.environment,
        });

        // Add event-specific data
        match &context.event {
            crate::hooks::types::LifecycleEvent::SessionStart { session_id, model, cwd, .. } => {
                payload["event"]["session_id"] = json!(session_id);
                payload["event"]["model"] = json!(model);
                payload["event"]["cwd"] = json!(cwd.to_string_lossy());
            }
            crate::hooks::types::LifecycleEvent::SessionEnd { session_id, duration, .. } => {
                payload["event"]["session_id"] = json!(session_id);
                payload["event"]["duration_ms"] = json!(duration.as_millis());
            }
            crate::hooks::types::LifecycleEvent::TaskStart { task_id, session_id, prompt, .. } => {
                payload["event"]["task_id"] = json!(task_id);
                payload["event"]["session_id"] = json!(session_id);
                payload["event"]["prompt"] = json!(prompt);
            }
            crate::hooks::types::LifecycleEvent::TaskComplete { task_id, session_id, success, duration, .. } => {
                payload["event"]["task_id"] = json!(task_id);
                payload["event"]["session_id"] = json!(session_id);
                payload["event"]["success"] = json!(success);
                payload["event"]["duration_ms"] = json!(duration.as_millis());
            }
            crate::hooks::types::LifecycleEvent::ExecBefore { command, cwd, .. } => {
                payload["event"]["command"] = json!(command);
                payload["event"]["cwd"] = json!(cwd.to_string_lossy());
            }
            crate::hooks::types::LifecycleEvent::ExecAfter { command, exit_code, duration, .. } => {
                payload["event"]["command"] = json!(command);
                payload["event"]["exit_code"] = json!(exit_code);
                payload["event"]["duration_ms"] = json!(duration.as_millis());
            }
            crate::hooks::types::LifecycleEvent::PatchBefore { changes, .. } => {
                payload["event"]["changes"] = json!(changes);
            }
            crate::hooks::types::LifecycleEvent::PatchAfter { applied_files, success, .. } => {
                payload["event"]["applied_files"] = json!(applied_files);
                payload["event"]["success"] = json!(success);
            }
            crate::hooks::types::LifecycleEvent::McpToolBefore { server, tool, .. } => {
                payload["event"]["server"] = json!(server);
                payload["event"]["tool"] = json!(tool);
            }
            crate::hooks::types::LifecycleEvent::McpToolAfter { server, tool, success, duration, .. } => {
                payload["event"]["server"] = json!(server);
                payload["event"]["tool"] = json!(tool);
                payload["event"]["success"] = json!(success);
                payload["event"]["duration_ms"] = json!(duration.as_millis());
            }
            crate::hooks::types::LifecycleEvent::AgentMessage { message, reasoning, .. } => {
                payload["event"]["message"] = json!(message);
                if let Some(reasoning) = reasoning {
                    payload["event"]["reasoning"] = json!(reasoning);
                }
            }
            crate::hooks::types::LifecycleEvent::ErrorOccurred { error, context: error_context, .. } => {
                payload["event"]["error"] = json!(error);
                payload["event"]["error_context"] = json!(error_context);
            }
        }

        payload
    }

    /// Build HTTP request with configuration and payload.
    fn build_request(&self, config: &WebhookConfig, payload: Value) -> Result<RequestBuilder, HookError> {
        let mut request = self.client.request(config.method.clone(), &config.url);

        // Add default headers
        for (key, value) in &self.default_headers {
            request = request.header(key, value);
        }

        // Add webhook-specific headers
        for (key, value) in &config.headers {
            request = request.header(key, value);
        }

        // Set content type if not specified
        if !config.headers.contains_key("content-type") && !self.default_headers.contains_key("content-type") {
            request = request.header("content-type", "application/json");
        }

        // Add authentication
        if let Some(auth) = &config.auth {
            request = match auth {
                WebhookAuth::Bearer { token } => request.bearer_auth(token),
                WebhookAuth::Basic { username, password } => request.basic_auth(username, password.as_ref()),
                WebhookAuth::Header { name, value } => request.header(name, value),
            };
        }

        // Add body
        let body_value = if let Some(custom_body) = &config.body {
            // Use custom body if provided
            custom_body.clone()
        } else {
            // Use generated payload
            payload
        };

        request = request.json(&body_value);

        Ok(request)
    }

    /// Execute webhook request and handle response.
    async fn execute_webhook(&self, config: WebhookConfig, payload: Value) -> Result<WebhookResult, HookError> {
        let start_time = Instant::now();

        debug!("Sending webhook to: {} {}", config.method, config.url);

        // Build request
        let request = self.build_request(&config, payload)?;

        // Send request
        let response = request.send().await.map_err(|e| {
            HookError::Execution(format!("Failed to send webhook request: {}", e))
        })?;

        let status = response.status();
        let headers = response.headers().clone();

        // Read response body with size limit
        let response_text = if response.content_length().unwrap_or(0) > self.max_response_size as u64 {
            "[Response too large, truncated]".to_string()
        } else {
            response.text().await.map_err(|e| {
                HookError::Execution(format!("Failed to read response body: {}", e))
            })?
        };

        let duration = start_time.elapsed();
        let success = status.is_success();

        debug!(
            "Webhook response: status={}, success={}, duration={:?}",
            status, success, duration
        );

        Ok(WebhookResult {
            status_code: status.as_u16(),
            success,
            response_body: response_text,
            response_headers: headers.iter()
                .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
                .collect(),
            duration,
            url: config.url,
            method: config.method,
        })
    }
}

#[async_trait]
impl HookExecutor for WebhookExecutor {
    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        info!("Executing webhook hook for event: {:?}", context.event.event_type());

        // Extract webhook configuration
        let webhook_config = self.extract_webhook_config(context)?;

        // Build payload
        let payload = self.build_payload(context);

        // Execute the webhook
        match self.execute_webhook(webhook_config, payload).await {
            Ok(result) => {
                if result.success {
                    info!(
                        "Webhook hook executed successfully: status={}, duration={:?}",
                        result.status_code, result.duration
                    );

                    let output = Some(format!(
                        "Webhook sent successfully: {} {} (status: {})",
                        result.method, result.url, result.status_code
                    ));

                    Ok(HookResult::success(output, start_time.elapsed()))
                } else {
                    warn!(
                        "Webhook hook failed: status={}, response={}",
                        result.status_code,
                        result.response_body.chars().take(200).collect::<String>()
                    );

                    let error_msg = format!(
                        "Webhook failed with status {}: {}",
                        result.status_code,
                        result.response_body.chars().take(500).collect::<String>()
                    );

                    Ok(HookResult::failure(error_msg, start_time.elapsed()))
                }
            }
            Err(e) => {
                error!("Webhook hook execution error: {}", e);
                Ok(HookResult::failure(e.to_string(), start_time.elapsed()))
            }
        }
    }

    fn executor_type(&self) -> &'static str {
        "webhook"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::Webhook { .. })
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(10)) // Network requests can be slower
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: Duration::from_secs(60),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            required: false,
            max_retries: 3, // Retry network failures
            retry_delay: Duration::from_secs(1),
            isolated: true,
        }
    }

    async fn prepare(&self, context: &HookContext) -> Result<(), HookError> {
        // Validate webhook configuration
        let _config = self.extract_webhook_config(context)?;

        // Additional validation could be added here (e.g., URL format validation)
        Ok(())
    }

    async fn cleanup(&self, _context: &HookContext) -> Result<(), HookError> {
        // No cleanup needed for webhook execution
        Ok(())
    }
}

/// Configuration for webhook execution.
#[derive(Debug, Clone)]
struct WebhookConfig {
    /// URL to send the webhook to.
    url: String,
    /// HTTP method to use.
    method: Method,
    /// Headers to include in the request.
    headers: HashMap<String, String>,
    /// Custom body to send (if None, uses generated payload).
    body: Option<Value>,
    /// Authentication configuration.
    auth: Option<WebhookAuth>,
}

/// Authentication methods for webhooks.
#[derive(Debug, Clone)]
enum WebhookAuth {
    /// Bearer token authentication.
    Bearer { token: String },
    /// Basic authentication.
    Basic { username: String, password: Option<String> },
    /// Custom header authentication.
    Header { name: String, value: String },
}

/// Result of webhook execution.
#[derive(Debug, Clone)]
struct WebhookResult {
    /// HTTP status code.
    status_code: u16,
    /// Whether the request was successful.
    success: bool,
    /// Response body.
    response_body: String,
    /// Response headers.
    response_headers: HashMap<String, String>,
    /// Duration of the request.
    duration: Duration,
    /// URL that was called.
    url: String,
    /// HTTP method used.
    method: Method,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::types::LifecycleEvent;
    use std::path::PathBuf;

    fn create_test_context(url: String) -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp")),
            timestamp: chrono::Utc::now(),
        };

        let hook_type = HookType::Webhook {
            url,
            method: crate::hooks::types::HttpMethod::Post,
            headers: HashMap::new(),
            timeout: None,
            retry_count: None,
        };

        HookContext::new(event, PathBuf::from("/tmp"))
            .with_hook_type(hook_type)
    }

    #[tokio::test]
    async fn test_webhook_executor_creation() {
        let executor = WebhookExecutor::new();
        assert_eq!(executor.executor_type(), "webhook");
        assert_eq!(executor.default_timeout, Duration::from_secs(30));
        assert_eq!(executor.max_response_size, 1024 * 1024);
    }

    #[tokio::test]
    async fn test_webhook_executor_with_timeout() {
        let timeout = Duration::from_secs(120);
        let executor = WebhookExecutor::with_timeout(timeout);
        assert_eq!(executor.default_timeout, timeout);
    }

    #[tokio::test]
    async fn test_webhook_executor_can_execute() {
        let executor = WebhookExecutor::new();
        let context = create_test_context("https://example.com/webhook".to_string());

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_webhook_payload_generation() {
        let executor = WebhookExecutor::new();
        let context = create_test_context("https://example.com/webhook".to_string());

        let payload = executor.build_payload(&context);

        assert!(payload["event"]["type"].is_string());
        assert!(payload["event"]["timestamp"].is_string());
        assert!(payload["hook"]["type"] == "webhook");
        assert!(payload["event"]["session_id"] == "test-session");
        assert!(payload["event"]["model"] == "test-model");
    }

    #[tokio::test]
    async fn test_webhook_preparation() {
        let executor = WebhookExecutor::new();
        let context = create_test_context("https://example.com/webhook".to_string());

        let result = executor.prepare(&context).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_webhook_cleanup() {
        let executor = WebhookExecutor::new();
        let context = create_test_context("https://example.com/webhook".to_string());

        let result = executor.cleanup(&context).await;
        assert!(result.is_ok());
    }

    #[test]
    fn test_webhook_executor_default_config() {
        let executor = WebhookExecutor::new();
        let config = executor.default_config();

        assert_eq!(config.timeout, Duration::from_secs(60));
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert_eq!(config.max_retries, 3);
        assert!(config.isolated);
    }

    #[tokio::test]
    async fn test_invalid_webhook_url() {
        let executor = WebhookExecutor::new();
        let context = create_test_context("".to_string()); // Empty URL

        let result = executor.extract_webhook_config(&context);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("cannot be empty"));
    }
}
