//! Custom plugin hook executor for extensible functionality.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::Value;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::process::Command;
use tokio::time::timeout;

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{HookError, HookResult, HookType};

/// Custom plugin hook executor for running external plugins.
#[derive(Debug)]
pub struct CustomPluginExecutor {
    /// Default timeout for plugin operations.
    default_timeout: Duration,
    /// Default plugin directory.
    default_plugin_dir: PathBuf,
}

impl CustomPluginExecutor {
    /// Create a new custom plugin executor.
    pub fn new() -> Self {
        Self {
            default_timeout: Duration::from_secs(30),
            default_plugin_dir: PathBuf::from("~/.codex/plugins"),
        }
    }

    /// Create a new custom plugin executor with custom settings.
    pub fn with_settings(timeout: Duration, plugin_dir: PathBuf) -> Self {
        Self {
            default_timeout: timeout,
            default_plugin_dir: plugin_dir,
        }
    }

    /// Execute a custom plugin.
    async fn execute_plugin(
        &self,
        plugin_name: &str,
        plugin_config: &HashMap<String, Value>,
        plugin_path: Option<&Path>,
        context: &HookContext,
        operation_timeout: Duration,
    ) -> Result<String, HookError> {
        // Determine plugin path
        let plugin_executable = self.resolve_plugin_path(plugin_name, plugin_path)?;

        // Validate plugin exists and is executable
        self.validate_plugin(&plugin_executable)?;

        // Prepare plugin input
        let plugin_input = self.prepare_plugin_input(plugin_config, context)?;

        // Execute the plugin
        self.run_plugin(&plugin_executable, &plugin_input, operation_timeout).await
    }

    /// Resolve the full path to the plugin executable.
    fn resolve_plugin_path(&self, plugin_name: &str, plugin_path: Option<&Path>) -> Result<PathBuf, HookError> {
        if let Some(path) = plugin_path {
            // Use provided path
            Ok(path.to_path_buf())
        } else {
            // Look for plugin in default directory
            let expanded_dir = self.expand_path(&self.default_plugin_dir)?;
            
            // Try different executable extensions
            let possible_names = [
                plugin_name.to_string(),
                format!("{}.sh", plugin_name),
                format!("{}.py", plugin_name),
                format!("{}.js", plugin_name),
                format!("{}.rb", plugin_name),
                format!("{}.exe", plugin_name), // Windows
            ];

            for name in &possible_names {
                let candidate = expanded_dir.join(name);
                if candidate.exists() {
                    return Ok(candidate);
                }
            }

            // Try to find in PATH
            if let Ok(path_var) = std::env::var("PATH") {
                for path_dir in std::env::split_paths(&path_var) {
                    for name in &possible_names {
                        let candidate = path_dir.join(name);
                        if candidate.exists() {
                            return Ok(candidate);
                        }
                    }
                }
            }

            Err(HookError::Configuration(format!(
                "Plugin '{}' not found in plugin directory or PATH",
                plugin_name
            )))
        }
    }

    /// Validate that the plugin exists and is executable.
    fn validate_plugin(&self, plugin_path: &Path) -> Result<(), HookError> {
        if !plugin_path.exists() {
            return Err(HookError::Configuration(format!(
                "Plugin does not exist: {}",
                plugin_path.display()
            )));
        }

        if !plugin_path.is_file() {
            return Err(HookError::Configuration(format!(
                "Plugin path is not a file: {}",
                plugin_path.display()
            )));
        }

        // Check if file is executable (Unix-like systems)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let metadata = std::fs::metadata(plugin_path)
                .map_err(|e| HookError::Configuration(format!("Failed to read plugin metadata: {}", e)))?;
            let permissions = metadata.permissions();
            if permissions.mode() & 0o111 == 0 {
                return Err(HookError::Configuration(format!(
                    "Plugin is not executable: {}",
                    plugin_path.display()
                )));
            }
        }

        Ok(())
    }

    /// Prepare input data for the plugin.
    fn prepare_plugin_input(
        &self,
        plugin_config: &HashMap<String, Value>,
        context: &HookContext,
    ) -> Result<String, HookError> {
        let input_data = serde_json::json!({
            "config": plugin_config,
            "context": {
                "event": {
                    "type": context.event.event_type(),
                    "session_id": context.event.session_id(),
                    "timestamp": chrono::Utc::now().to_rfc3339(),
                },
                "hook": {
                    "id": context.config.id,
                    "description": context.config.description,
                    "tags": context.config.tags,
                },
                "working_directory": context.working_directory,
            },
            "environment": std::env::vars().collect::<HashMap<String, String>>(),
        });

        serde_json::to_string_pretty(&input_data)
            .map_err(|e| HookError::Execution(format!("Failed to serialize plugin input: {}", e)))
    }

    /// Run the plugin executable.
    async fn run_plugin(
        &self,
        plugin_path: &Path,
        input_data: &str,
        operation_timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Executing plugin: {}", plugin_path.display());
        tracing::debug!("Plugin input size: {} bytes", input_data.len());

        // Determine how to execute the plugin based on its extension
        let mut command = self.create_plugin_command(plugin_path)?;

        // Configure the command
        command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true);

        // Spawn the process
        let mut child = command
            .spawn()
            .map_err(|e| HookError::Execution(format!("Failed to spawn plugin process: {}", e)))?;

        // Send input to the plugin
        if let Some(mut stdin) = child.stdin.take() {
            stdin
                .write_all(input_data.as_bytes())
                .await
                .map_err(|e| HookError::Execution(format!("Failed to write to plugin stdin: {}", e)))?;
            stdin
                .shutdown()
                .await
                .map_err(|e| HookError::Execution(format!("Failed to close plugin stdin: {}", e)))?;
        }

        // Wait for the plugin to complete with timeout
        let output_result = timeout(operation_timeout, async {
            let output = child
                .wait_with_output()
                .await
                .map_err(|e| HookError::Execution(format!("Failed to wait for plugin: {}", e)))?;

            Ok::<tokio::process::Output, HookError>(output)
        })
        .await;

        let output = match output_result {
            Ok(Ok(output)) => output,
            Ok(Err(e)) => return Err(e),
            Err(_) => {
                // Kill the process if it's still running
                let _ = child.kill().await;
                return Err(HookError::Execution(format!(
                    "Plugin execution timed out after {:?}",
                    operation_timeout
                )));
            }
        };

        // Process the output
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        if !output.status.success() {
            let error_msg = if stderr.is_empty() {
                format!("Plugin failed with exit code: {}", output.status.code().unwrap_or(-1))
            } else {
                format!("Plugin failed: {}", stderr.trim())
            };
            return Err(HookError::Execution(error_msg));
        }

        // Try to parse the output as JSON for structured results
        if let Ok(json_output) = serde_json::from_str::<Value>(&stdout) {
            if let Some(result) = json_output.get("result") {
                return Ok(result.to_string());
            } else if let Some(message) = json_output.get("message") {
                return Ok(message.to_string());
            }
        }

        // Return raw stdout if not JSON or no structured fields
        Ok(stdout.trim().to_string())
    }

    /// Create the appropriate command for executing the plugin.
    fn create_plugin_command(&self, plugin_path: &Path) -> Result<Command, HookError> {
        let extension = plugin_path
            .extension()
            .and_then(|ext| ext.to_str())
            .unwrap_or("");

        let mut command = match extension {
            "py" => {
                let mut cmd = Command::new("python3");
                cmd.arg(plugin_path);
                cmd
            }
            "js" => {
                let mut cmd = Command::new("node");
                cmd.arg(plugin_path);
                cmd
            }
            "rb" => {
                let mut cmd = Command::new("ruby");
                cmd.arg(plugin_path);
                cmd
            }
            "sh" => {
                let mut cmd = Command::new("bash");
                cmd.arg(plugin_path);
                cmd
            }
            _ => {
                // Try to execute directly
                Command::new(plugin_path)
            }
        };

        // Set environment variables
        command.env("CODEX_PLUGIN_MODE", "true");
        command.env("CODEX_PLUGIN_VERSION", "1.0");

        Ok(command)
    }

    /// Expand path with home directory support.
    fn expand_path(&self, path: &Path) -> Result<PathBuf, HookError> {
        if let Some(path_str) = path.to_str() {
            if path_str.starts_with("~/") {
                if let Some(home) = dirs::home_dir() {
                    return Ok(home.join(&path_str[2..]));
                }
            }
        }
        Ok(path.to_path_buf())
    }

    /// Validate plugin configuration.
    fn validate_config(
        &self,
        plugin_name: &str,
        plugin_config: &HashMap<String, Value>,
    ) -> Result<(), HookError> {
        if plugin_name.trim().is_empty() {
            return Err(HookError::Configuration(
                "Plugin name cannot be empty".to_string(),
            ));
        }

        // Validate plugin name doesn't contain dangerous characters
        if plugin_name.contains("..") || plugin_name.contains('/') || plugin_name.contains('\\') {
            return Err(HookError::Configuration(
                "Plugin name contains invalid characters".to_string(),
            ));
        }

        // Check for reasonable config size
        let config_size = serde_json::to_string(plugin_config)
            .map_err(|e| HookError::Configuration(format!("Invalid plugin config: {}", e)))?
            .len();

        if config_size > 1024 * 1024 {
            // 1MB limit
            return Err(HookError::Configuration(
                "Plugin configuration is too large (>1MB)".to_string(),
            ));
        }

        Ok(())
    }

    /// Get plugin information.
    async fn get_plugin_info(&self, plugin_path: &Path) -> Result<PluginInfo, HookError> {
        // Try to get plugin info by running it with --info flag
        let mut command = self.create_plugin_command(plugin_path)?;
        command.arg("--info");
        command.stdout(Stdio::piped());
        command.stderr(Stdio::piped());

        let output = timeout(Duration::from_secs(5), command.output()).await;

        match output {
            Ok(Ok(output)) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                if let Ok(info) = serde_json::from_str::<PluginInfo>(&stdout) {
                    Ok(info)
                } else {
                    // Fallback to basic info
                    Ok(PluginInfo {
                        name: plugin_path
                            .file_stem()
                            .and_then(|s| s.to_str())
                            .unwrap_or("unknown")
                            .to_string(),
                        version: "unknown".to_string(),
                        description: "Custom plugin".to_string(),
                        author: "unknown".to_string(),
                        supported_events: vec!["*".to_string()],
                    })
                }
            }
            _ => {
                // Fallback to basic info from filename
                Ok(PluginInfo {
                    name: plugin_path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("unknown")
                        .to_string(),
                    version: "unknown".to_string(),
                    description: "Custom plugin".to_string(),
                    author: "unknown".to_string(),
                    supported_events: vec!["*".to_string()],
                })
            }
        }
    }
}

/// Plugin information structure.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PluginInfo {
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub supported_events: Vec<String>,
}

impl Default for CustomPluginExecutor {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl HookExecutor for CustomPluginExecutor {
    fn executor_type(&self) -> &'static str {
        "custom_plugin"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::CustomPlugin { .. })
    }

    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        let (plugin_name, plugin_config, hook_timeout, plugin_path) = match &context.hook_type {
            HookType::CustomPlugin {
                plugin_name,
                plugin_config,
                timeout,
                plugin_path,
            } => (
                plugin_name,
                plugin_config,
                timeout.unwrap_or(self.default_timeout),
                plugin_path.as_deref(),
            ),
            _ => {
                return Ok(HookResult::failure(
                    "Invalid hook type for custom plugin executor".to_string(),
                    start_time.elapsed(),
                ));
            }
        };

        // Validate configuration
        if let Err(e) = self.validate_config(plugin_name, plugin_config) {
            return Ok(HookResult::failure(
                format!("Plugin configuration error: {}", e),
                start_time.elapsed(),
            ));
        }

        tracing::info!("Executing custom plugin: {}", plugin_name);

        // Execute the plugin with timeout
        let plugin_result = timeout(
            hook_timeout,
            self.execute_plugin(plugin_name, plugin_config, plugin_path, context, hook_timeout),
        )
        .await;

        let duration = start_time.elapsed();

        match plugin_result {
            Ok(Ok(output)) => {
                tracing::info!("Plugin executed successfully in {:?}", duration);
                Ok(HookResult::success(Some(output), duration))
            }
            Ok(Err(e)) => {
                tracing::error!("Plugin execution failed: {}", e);
                Ok(HookResult::failure(e.to_string(), duration))
            }
            Err(_) => {
                tracing::error!("Plugin execution timed out after {:?}", hook_timeout);
                Ok(HookResult::failure(
                    format!("Plugin execution timed out after {:?}", hook_timeout),
                    duration,
                ))
            }
        }
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(10))
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: self.default_timeout,
            max_retries: 1,
            isolated: true,
            mode: crate::hooks::types::HookExecutionMode::Async,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::config::HookConfig;
    use crate::hooks::types::{HookExecutionMode, HookPriority, LifecycleEvent, LifecycleEventType};
    use std::fs;
    use tempfile::TempDir;

    fn create_custom_plugin_context(
        plugin_name: &str,
        plugin_config: HashMap<String, Value>,
        plugin_path: Option<PathBuf>,
    ) -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
            model: "gpt-4".to_string(),
            provider: "openai".to_string(),
            timestamp: std::time::SystemTime::now(),
        };

        let hook_type = HookType::CustomPlugin {
            plugin_name: plugin_name.to_string(),
            plugin_config,
            timeout: Some(Duration::from_secs(10)),
            plugin_path,
        };

        let config = HookConfig {
            id: Some("test_plugin_hook".to_string()),
            event: LifecycleEventType::SessionStart,
            hook_type: hook_type.clone(),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            condition: None,
            blocking: false,
            required: false,
            tags: Vec::new(),
            description: Some("Test custom plugin hook".to_string()),
            depends_on: Vec::new(),
            parallel: true,
            max_retries: 0,
            timeout: Some(Duration::from_secs(10)),
        };

        HookContext::new(event, PathBuf::from("/tmp"), hook_type, config)
    }

    #[tokio::test]
    async fn test_custom_plugin_executor_creation() {
        let executor = CustomPluginExecutor::new();
        assert_eq!(executor.executor_type(), "custom_plugin");
        assert_eq!(executor.default_timeout, Duration::from_secs(30));
    }

    #[tokio::test]
    async fn test_can_execute_custom_plugin_hook() {
        let executor = CustomPluginExecutor::new();
        let context = create_custom_plugin_context(
            "test_plugin",
            HashMap::new(),
            None,
        );

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_plugin_path_resolution() {
        let executor = CustomPluginExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        
        // Create a test plugin
        let plugin_path = temp_dir.path().join("test_plugin.sh");
        fs::write(&plugin_path, "#!/bin/bash\necho 'Hello from plugin'").unwrap();
        
        let resolved = executor.resolve_plugin_path("test_plugin", Some(&plugin_path)).unwrap();
        assert_eq!(resolved, plugin_path);
    }

    #[tokio::test]
    async fn test_plugin_input_preparation() {
        let executor = CustomPluginExecutor::new();
        let mut config = HashMap::new();
        config.insert("key1".to_string(), Value::String("value1".to_string()));
        config.insert("key2".to_string(), Value::Number(serde_json::Number::from(42)));
        
        let context = create_custom_plugin_context("test_plugin", config.clone(), None);
        
        let input = executor.prepare_plugin_input(&config, &context).unwrap();
        
        // Verify the input contains expected structure
        assert!(input.contains("\"config\""));
        assert!(input.contains("\"context\""));
        assert!(input.contains("\"environment\""));
        assert!(input.contains("\"key1\""));
        assert!(input.contains("\"value1\""));
    }

    #[tokio::test]
    async fn test_plugin_validation() {
        let executor = CustomPluginExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        
        // Test non-existent plugin
        let non_existent = temp_dir.path().join("non_existent.sh");
        assert!(executor.validate_plugin(&non_existent).is_err());
        
        // Test directory instead of file
        let dir_path = temp_dir.path().join("directory");
        fs::create_dir(&dir_path).unwrap();
        assert!(executor.validate_plugin(&dir_path).is_err());
    }

    #[tokio::test]
    async fn test_create_plugin_command() {
        let executor = CustomPluginExecutor::new();
        
        // Test Python plugin
        let py_path = PathBuf::from("test.py");
        let cmd = executor.create_plugin_command(&py_path).unwrap();
        assert_eq!(cmd.as_std().get_program(), "python3");
        
        // Test Node.js plugin
        let js_path = PathBuf::from("test.js");
        let cmd = executor.create_plugin_command(&js_path).unwrap();
        assert_eq!(cmd.as_std().get_program(), "node");
        
        // Test shell script
        let sh_path = PathBuf::from("test.sh");
        let cmd = executor.create_plugin_command(&sh_path).unwrap();
        assert_eq!(cmd.as_std().get_program(), "bash");
    }

    #[tokio::test]
    async fn test_invalid_plugin_configuration() {
        let executor = CustomPluginExecutor::new();
        
        // Test empty plugin name
        assert!(executor.validate_config("", &HashMap::new()).is_err());
        
        // Test plugin name with invalid characters
        assert!(executor.validate_config("../malicious", &HashMap::new()).is_err());
        assert!(executor.validate_config("plugin/with/slash", &HashMap::new()).is_err());
    }

    #[tokio::test]
    async fn test_plugin_execution_with_mock_script() {
        let executor = CustomPluginExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        
        // Create a simple test plugin that echoes JSON
        let plugin_path = temp_dir.path().join("echo_plugin.sh");
        let plugin_content = r#"#!/bin/bash
echo '{"result": "Plugin executed successfully", "input_received": true}'
"#;
        fs::write(&plugin_path, plugin_content).unwrap();
        
        // Make it executable (Unix only)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&plugin_path).unwrap().permissions();
            perms.set_mode(0o755);
            fs::set_permissions(&plugin_path, perms).unwrap();
        }
        
        let context = create_custom_plugin_context(
            "echo_plugin",
            HashMap::new(),
            Some(plugin_path),
        );

        // Skip this test on Windows or if bash is not available
        if cfg!(unix) && std::process::Command::new("bash").arg("--version").output().is_ok() {
            let result = executor.execute(&context).await.unwrap();
            assert!(result.success);
            assert!(result.output.is_some());
            let output = result.output.unwrap();
            assert!(output.contains("Plugin executed successfully"));
        }
    }

    #[test]
    fn test_plugin_info_serialization() {
        let info = PluginInfo {
            name: "test_plugin".to_string(),
            version: "1.0.0".to_string(),
            description: "A test plugin".to_string(),
            author: "Test Author".to_string(),
            supported_events: vec!["session.start".to_string(), "task.complete".to_string()],
        };

        let serialized = serde_json::to_string(&info).unwrap();
        let deserialized: PluginInfo = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(deserialized.name, "test_plugin");
        assert_eq!(deserialized.version, "1.0.0");
        assert_eq!(deserialized.supported_events.len(), 2);
    }
}
