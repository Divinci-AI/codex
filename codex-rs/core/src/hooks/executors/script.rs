//! Script executor for running shell scripts and commands as hooks.

use std::collections::HashMap;

use std::path::PathBuf;
use std::process::Stdio;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tracing::{debug, error, info, warn};

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{HookError, HookExecutionMode, HookPriority, HookResult, HookType};

/// Executor for running shell scripts and commands.
#[derive(Debug, Clone)]
pub struct ScriptExecutor {
    /// Default shell to use for script execution.
    pub default_shell: String,
    /// Default working directory for script execution.
    pub default_working_dir: Option<PathBuf>,
    /// Environment variables to always include.
    pub base_environment: HashMap<String, String>,
    /// Maximum output size to capture (in bytes).
    pub max_output_size: usize,
}

impl Default for ScriptExecutor {
    fn default() -> Self {
        Self::new()
    }
}

impl ScriptExecutor {
    /// Create a new script executor with default settings.
    pub fn new() -> Self {
        let default_shell = if cfg!(windows) {
            "cmd".to_string()
        } else {
            "bash".to_string()
        };

        Self {
            default_shell,
            default_working_dir: None,
            base_environment: HashMap::new(),
            max_output_size: 1024 * 1024, // 1MB default
        }
    }

    /// Create a script executor with custom shell.
    pub fn with_shell<S: Into<String>>(shell: S) -> Self {
        Self {
            default_shell: shell.into(),
            ..Self::new()
        }
    }

    /// Set the default working directory.
    pub fn with_working_dir<P: Into<PathBuf>>(mut self, dir: P) -> Self {
        self.default_working_dir = Some(dir.into());
        self
    }

    /// Add base environment variables.
    pub fn with_environment(mut self, env: HashMap<String, String>) -> Self {
        self.base_environment = env;
        self
    }

    /// Set maximum output size to capture.
    pub fn with_max_output_size(mut self, size: usize) -> Self {
        self.max_output_size = size;
        self
    }

    /// Extract script configuration from hook context.
    fn extract_script_config(&self, context: &HookContext) -> Result<ScriptConfig, HookError> {
        match &context.hook_type {
            HookType::Script { command, cwd, environment, timeout: _ } => {
                if command.is_empty() {
                    return Err(HookError::Configuration("Script command cannot be empty".to_string()));
                }

                Ok(ScriptConfig {
                    command: command.clone(),
                    environment: environment.clone(),
                    working_dir: cwd.clone(),
                    shell: self.default_shell.clone(),
                })
            }
            _ => Err(HookError::Configuration(
                "ScriptExecutor can only execute Script hooks".to_string(),
            )),
        }
    }

    /// Build the complete environment for script execution.
    fn build_environment(&self, context: &HookContext, script_env: &HashMap<String, String>) -> HashMap<String, String> {
        let mut env = self.base_environment.clone();

        // Add context environment variables
        for (key, value) in &context.environment {
            env.insert(key.clone(), value.clone());
        }

        // Add script-specific environment variables
        for (key, value) in script_env {
            env.insert(key.clone(), value.clone());
        }

        // Add hook execution metadata
        env.insert("CODEX_HOOK_TYPE".to_string(), "script".to_string());
        env.insert("CODEX_EVENT_TYPE".to_string(), context.event.event_type().to_string());
        env.insert("CODEX_WORKING_DIR".to_string(), context.working_directory.to_string_lossy().to_string());

        // Add timestamp
        env.insert("CODEX_TIMESTAMP".to_string(), chrono::Utc::now().to_rfc3339());

        env
    }

    /// Execute a script command with the given configuration.
    async fn execute_script(&self, config: ScriptConfig, environment: HashMap<String, String>) -> Result<ScriptResult, HookError> {
        let start_time = Instant::now();

        debug!("Executing script command: {:?}", config.command);

        // Determine working directory
        let working_dir = config.working_dir
            .or_else(|| self.default_working_dir.clone())
            .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/")));

        // Build command
        let mut cmd = if cfg!(windows) {
            let mut cmd = Command::new("cmd");
            cmd.args(["/C"]);
            cmd.args(&config.command);
            cmd
        } else {
            let mut cmd = Command::new(&config.shell);
            cmd.arg("-c");
            cmd.arg(config.command.join(" "));
            cmd
        };

        // Set working directory and environment
        cmd.current_dir(&working_dir);
        cmd.envs(&environment);

        // Configure stdio
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());
        cmd.stdin(Stdio::null());

        // Spawn the process
        let mut child = cmd.spawn().map_err(|e| {
            HookError::Execution(format!("Failed to spawn script process: {}", e))
        })?;

        // Capture output
        let stdout = child.stdout.take().ok_or_else(|| {
            HookError::Execution("Failed to capture stdout".to_string())
        })?;
        let stderr = child.stderr.take().ok_or_else(|| {
            HookError::Execution("Failed to capture stderr".to_string())
        })?;

        // Read output streams
        let stdout_task = tokio::spawn(Self::read_stream(stdout, self.max_output_size));
        let stderr_task = tokio::spawn(Self::read_stream(stderr, self.max_output_size));

        // Wait for process completion
        let exit_status = child.wait().await.map_err(|e| {
            HookError::Execution(format!("Failed to wait for script process: {}", e))
        })?;

        // Collect output
        let stdout_output = stdout_task.await.map_err(|e| {
            HookError::Execution(format!("Failed to read stdout: {}", e))
        })??;
        let stderr_output = stderr_task.await.map_err(|e| {
            HookError::Execution(format!("Failed to read stderr: {}", e))
        })??;

        let duration = start_time.elapsed();
        let exit_code = exit_status.code().unwrap_or(-1);
        let success = exit_status.success();

        debug!(
            "Script execution completed: exit_code={}, success={}, duration={:?}",
            exit_code, success, duration
        );

        Ok(ScriptResult {
            exit_code,
            success,
            stdout: stdout_output,
            stderr: stderr_output,
            duration,
            command: config.command,
            working_dir,
        })
    }

    /// Read from a stream with size limit.
    async fn read_stream<R>(reader: R, max_size: usize) -> Result<String, HookError>
    where
        R: tokio::io::AsyncRead + Unpin,
    {
        let mut buf_reader = BufReader::new(reader);
        let mut output = String::new();
        let mut line = String::new();

        while buf_reader.read_line(&mut line).await.map_err(|e| {
            HookError::Execution(format!("Failed to read line: {}", e))
        })? > 0 {
            if output.len() + line.len() > max_size {
                output.push_str("... [output truncated due to size limit]\n");
                break;
            }
            output.push_str(&line);
            line.clear();
        }

        Ok(output)
    }
}

#[async_trait]
impl HookExecutor for ScriptExecutor {
    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        info!("Executing script hook for event: {:?}", context.event.event_type());

        // Extract script configuration
        let script_config = self.extract_script_config(context)?;

        // Build environment
        let environment = self.build_environment(context, &script_config.environment);

        // Execute the script
        match self.execute_script(script_config, environment).await {
            Ok(result) => {
                if result.success {
                    info!(
                        "Script hook executed successfully: exit_code={}, duration={:?}",
                        result.exit_code, result.duration
                    );

                    let output = if !result.stdout.is_empty() {
                        Some(result.stdout)
                    } else if !result.stderr.is_empty() {
                        Some(result.stderr)
                    } else {
                        Some(format!("Script completed with exit code {}", result.exit_code))
                    };

                    Ok(HookResult::success(output, start_time.elapsed()))
                } else {
                    warn!(
                        "Script hook failed: exit_code={}, stderr={}",
                        result.exit_code,
                        result.stderr.trim()
                    );

                    let error_msg = if !result.stderr.is_empty() {
                        format!("Script failed with exit code {}: {}", result.exit_code, result.stderr.trim())
                    } else {
                        format!("Script failed with exit code {}", result.exit_code)
                    };

                    Ok(HookResult::failure(error_msg, start_time.elapsed()))
                }
            }
            Err(e) => {
                error!("Script hook execution error: {}", e);
                Ok(HookResult::failure(e.to_string(), start_time.elapsed()))
            }
        }
    }

    fn executor_type(&self) -> &'static str {
        "script"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::Script { .. })
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(5)) // Scripts typically run quickly
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: Duration::from_secs(30),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            required: false,
            max_retries: 1,
            retry_delay: Duration::from_millis(500),
            isolated: true,
        }
    }

    async fn prepare(&self, context: &HookContext) -> Result<(), HookError> {
        // Validate script configuration
        let _config = self.extract_script_config(context)?;

        // Check if shell exists (basic validation)
        if !cfg!(windows) {
            let shell_check = Command::new("which")
                .arg(&self.default_shell)
                .output()
                .await;

            if let Ok(output) = shell_check {
                if !output.status.success() {
                    return Err(HookError::Configuration(
                        format!("Shell '{}' not found in PATH", self.default_shell)
                    ));
                }
            }
        }

        Ok(())
    }

    async fn cleanup(&self, _context: &HookContext) -> Result<(), HookError> {
        // No cleanup needed for script execution
        Ok(())
    }
}

/// Configuration for script execution.
#[derive(Debug, Clone)]
struct ScriptConfig {
    /// Command to execute (as array of arguments).
    command: Vec<String>,
    /// Environment variables for the script.
    environment: HashMap<String, String>,
    /// Working directory for script execution.
    working_dir: Option<PathBuf>,
    /// Shell to use for execution.
    shell: String,
}

/// Result of script execution.
#[derive(Debug, Clone)]
struct ScriptResult {
    /// Exit code of the script.
    exit_code: i32,
    /// Whether the script executed successfully.
    success: bool,
    /// Standard output from the script.
    stdout: String,
    /// Standard error from the script.
    stderr: String,
    /// Duration of script execution.
    duration: Duration,
    /// Command that was executed.
    command: Vec<String>,
    /// Working directory where script was executed.
    working_dir: PathBuf,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::types::LifecycleEvent;
    use std::collections::HashMap;

    fn create_test_context(command: Vec<String>) -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/tmp")),
            timestamp: chrono::Utc::now(),
        };

        let hook_type = HookType::Script {
            command,
            cwd: None,
            environment: HashMap::new(),
            timeout: None,
        };

        HookContext::new(event, PathBuf::from("/tmp"))
            .with_hook_type(hook_type)
    }

    #[tokio::test]
    async fn test_script_executor_creation() {
        let executor = ScriptExecutor::new();
        assert_eq!(executor.executor_type(), "script");
        assert_eq!(executor.max_output_size, 1024 * 1024);

        if cfg!(windows) {
            assert_eq!(executor.default_shell, "cmd");
        } else {
            assert_eq!(executor.default_shell, "bash");
        }
    }

    #[tokio::test]
    async fn test_script_executor_with_custom_shell() {
        let executor = ScriptExecutor::with_shell("zsh");
        assert_eq!(executor.default_shell, "zsh");
    }

    #[tokio::test]
    async fn test_script_executor_can_execute() {
        let executor = ScriptExecutor::new();
        let context = create_test_context(vec!["echo".to_string(), "test".to_string()]);

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_successful_script_execution() {
        let executor = ScriptExecutor::new();
        let command = if cfg!(windows) {
            vec!["echo".to_string(), "Hello World".to_string()]
        } else {
            vec!["echo".to_string(), "Hello World".to_string()]
        };
        let context = create_test_context(command);

        let result = executor.execute(&context).await.unwrap();

        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Hello World"));
    }

    #[tokio::test]
    async fn test_failed_script_execution() {
        let executor = ScriptExecutor::new();
        let command = if cfg!(windows) {
            vec!["cmd".to_string(), "/C".to_string(), "exit".to_string(), "1".to_string()]
        } else {
            vec!["false".to_string()] // Command that always fails
        };
        let context = create_test_context(command);

        let result = executor.execute(&context).await.unwrap();

        assert!(!result.success);
        assert!(result.error.is_some());
    }

    #[tokio::test]
    async fn test_script_environment_variables() {
        let executor = ScriptExecutor::new();
        let command = if cfg!(windows) {
            vec!["echo".to_string(), "%CODEX_HOOK_TYPE%".to_string()]
        } else {
            vec!["echo".to_string(), "$CODEX_HOOK_TYPE".to_string()]
        };
        let context = create_test_context(command);

        let result = executor.execute(&context).await.unwrap();

        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("script"));
    }

    #[tokio::test]
    async fn test_script_preparation() {
        let executor = ScriptExecutor::new();
        let context = create_test_context(vec!["echo".to_string(), "test".to_string()]);

        let result = executor.prepare(&context).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_script_cleanup() {
        let executor = ScriptExecutor::new();
        let context = create_test_context(vec!["echo".to_string(), "test".to_string()]);

        let result = executor.cleanup(&context).await;
        assert!(result.is_ok());
    }

    #[test]
    fn test_script_executor_default_config() {
        let executor = ScriptExecutor::new();
        let config = executor.default_config();

        assert_eq!(config.timeout, Duration::from_secs(30));
        assert_eq!(config.mode, HookExecutionMode::Async);
        assert_eq!(config.max_retries, 1);
        assert!(config.isolated);
    }
}
