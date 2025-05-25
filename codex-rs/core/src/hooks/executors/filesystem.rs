//! File system hook executor for file operations and monitoring.

use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use async_trait::async_trait;
use tokio::time::timeout;

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{FileSystemOperation, HookError, HookResult, HookType};

/// File system hook executor for performing file operations.
#[derive(Debug)]
pub struct FileSystemExecutor {
    /// Default timeout for file operations.
    default_timeout: Duration,
}

impl FileSystemExecutor {
    /// Create a new file system executor.
    pub fn new() -> Self {
        Self {
            default_timeout: Duration::from_secs(10),
        }
    }

    /// Create a new file system executor with custom timeout.
    pub fn with_timeout(timeout: Duration) -> Self {
        Self {
            default_timeout: timeout,
        }
    }

    /// Execute a file system operation.
    async fn execute_filesystem_operation(
        &self,
        operation: &FileSystemOperation,
        path: &Path,
        target_path: Option<&Path>,
        content: Option<&str>,
        permissions: Option<u32>,
    ) -> Result<String, HookError> {
        match operation {
            FileSystemOperation::Create => {
                self.create_file_or_directory(path, content).await
            }
            FileSystemOperation::Read => {
                self.read_file(path).await
            }
            FileSystemOperation::Write => {
                self.write_file(path, content.unwrap_or("")).await
            }
            FileSystemOperation::Append => {
                self.append_to_file(path, content.unwrap_or("")).await
            }
            FileSystemOperation::Delete => {
                self.delete_file_or_directory(path).await
            }
            FileSystemOperation::Copy => {
                let target = target_path.ok_or_else(|| {
                    HookError::Configuration("Target path required for copy operation".to_string())
                })?;
                self.copy_file_or_directory(path, target).await
            }
            FileSystemOperation::Move => {
                let target = target_path.ok_or_else(|| {
                    HookError::Configuration("Target path required for move operation".to_string())
                })?;
                self.move_file_or_directory(path, target).await
            }
            FileSystemOperation::Chmod => {
                let perms = permissions.ok_or_else(|| {
                    HookError::Configuration("Permissions required for chmod operation".to_string())
                })?;
                self.change_permissions(path, perms).await
            }
            FileSystemOperation::Watch => {
                self.watch_file_or_directory(path).await
            }
        }
    }

    /// Create a file or directory.
    async fn create_file_or_directory(&self, path: &Path, content: Option<&str>) -> Result<String, HookError> {
        tracing::info!("Creating file/directory: {}", path.display());

        // Determine if we should create a file or directory
        let is_directory = path.extension().is_none() && content.is_none();

        if is_directory {
            // Create directory
            tokio::fs::create_dir_all(path)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create directory: {}", e)))?;
            
            Ok(format!("Directory created successfully: {}", path.display()))
        } else {
            // Create file
            if let Some(parent) = path.parent() {
                tokio::fs::create_dir_all(parent)
                    .await
                    .map_err(|e| HookError::Execution(format!("Failed to create parent directory: {}", e)))?;
            }

            let file_content = content.unwrap_or("");
            tokio::fs::write(path, file_content)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create file: {}", e)))?;

            Ok(format!(
                "File created successfully: {} ({} bytes)",
                path.display(),
                file_content.len()
            ))
        }
    }

    /// Read file contents.
    async fn read_file(&self, path: &Path) -> Result<String, HookError> {
        tracing::info!("Reading file: {}", path.display());

        if !path.exists() {
            return Err(HookError::Execution(format!("File does not exist: {}", path.display())));
        }

        if path.is_dir() {
            return Err(HookError::Execution(format!("Path is a directory, not a file: {}", path.display())));
        }

        let content = tokio::fs::read_to_string(path)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to read file: {}", e)))?;

        Ok(format!(
            "File read successfully: {} ({} bytes)\nContent preview: {}",
            path.display(),
            content.len(),
            if content.len() > 100 {
                format!("{}...", &content[..100])
            } else {
                content.clone()
            }
        ))
    }

    /// Write content to a file.
    async fn write_file(&self, path: &Path, content: &str) -> Result<String, HookError> {
        tracing::info!("Writing to file: {}", path.display());

        if let Some(parent) = path.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create parent directory: {}", e)))?;
        }

        tokio::fs::write(path, content)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to write file: {}", e)))?;

        Ok(format!(
            "File written successfully: {} ({} bytes)",
            path.display(),
            content.len()
        ))
    }

    /// Append content to a file.
    async fn append_to_file(&self, path: &Path, content: &str) -> Result<String, HookError> {
        tracing::info!("Appending to file: {}", path.display());

        if let Some(parent) = path.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create parent directory: {}", e)))?;
        }

        // Use blocking I/O for append operation
        let path_clone = path.to_path_buf();
        let content_clone = content.to_string();
        
        tokio::task::spawn_blocking(move || {
            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&path_clone)
                .map_err(|e| HookError::Execution(format!("Failed to open file for append: {}", e)))?;

            file.write_all(content_clone.as_bytes())
                .map_err(|e| HookError::Execution(format!("Failed to append to file: {}", e)))?;

            Ok::<String, HookError>(format!(
                "Content appended successfully to: {} ({} bytes added)",
                path_clone.display(),
                content_clone.len()
            ))
        })
        .await
        .map_err(|e| HookError::Execution(format!("Task join error: {}", e)))?
    }

    /// Delete a file or directory.
    async fn delete_file_or_directory(&self, path: &Path) -> Result<String, HookError> {
        tracing::info!("Deleting: {}", path.display());

        if !path.exists() {
            return Err(HookError::Execution(format!("Path does not exist: {}", path.display())));
        }

        if path.is_dir() {
            tokio::fs::remove_dir_all(path)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to delete directory: {}", e)))?;
            
            Ok(format!("Directory deleted successfully: {}", path.display()))
        } else {
            tokio::fs::remove_file(path)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to delete file: {}", e)))?;
            
            Ok(format!("File deleted successfully: {}", path.display()))
        }
    }

    /// Copy a file or directory.
    async fn copy_file_or_directory(&self, source: &Path, target: &Path) -> Result<String, HookError> {
        tracing::info!("Copying from {} to {}", source.display(), target.display());

        if !source.exists() {
            return Err(HookError::Execution(format!("Source path does not exist: {}", source.display())));
        }

        if let Some(parent) = target.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create target parent directory: {}", e)))?;
        }

        if source.is_dir() {
            self.copy_directory_recursive(source, target).await?;
            Ok(format!("Directory copied successfully from {} to {}", source.display(), target.display()))
        } else {
            tokio::fs::copy(source, target)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to copy file: {}", e)))?;
            
            Ok(format!("File copied successfully from {} to {}", source.display(), target.display()))
        }
    }

    /// Recursively copy a directory.
    async fn copy_directory_recursive(&self, source: &Path, target: &Path) -> Result<(), HookError> {
        tokio::fs::create_dir_all(target)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to create target directory: {}", e)))?;

        let mut entries = tokio::fs::read_dir(source)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to read source directory: {}", e)))?;

        while let Some(entry) = entries.next_entry()
            .await
            .map_err(|e| HookError::Execution(format!("Failed to read directory entry: {}", e)))? {
            
            let source_path = entry.path();
            let target_path = target.join(entry.file_name());

            if source_path.is_dir() {
                self.copy_directory_recursive(&source_path, &target_path).await?;
            } else {
                tokio::fs::copy(&source_path, &target_path)
                    .await
                    .map_err(|e| HookError::Execution(format!("Failed to copy file: {}", e)))?;
            }
        }

        Ok(())
    }

    /// Move/rename a file or directory.
    async fn move_file_or_directory(&self, source: &Path, target: &Path) -> Result<String, HookError> {
        tracing::info!("Moving from {} to {}", source.display(), target.display());

        if !source.exists() {
            return Err(HookError::Execution(format!("Source path does not exist: {}", source.display())));
        }

        if let Some(parent) = target.parent() {
            tokio::fs::create_dir_all(parent)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to create target parent directory: {}", e)))?;
        }

        tokio::fs::rename(source, target)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to move/rename: {}", e)))?;

        Ok(format!("Successfully moved from {} to {}", source.display(), target.display()))
    }

    /// Change file permissions.
    async fn change_permissions(&self, path: &Path, permissions: u32) -> Result<String, HookError> {
        tracing::info!("Changing permissions for {} to {:o}", path.display(), permissions);

        if !path.exists() {
            return Err(HookError::Execution(format!("Path does not exist: {}", path.display())));
        }

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let perms = std::fs::Permissions::from_mode(permissions);
            tokio::fs::set_permissions(path, perms)
                .await
                .map_err(|e| HookError::Execution(format!("Failed to change permissions: {}", e)))?;
        }

        #[cfg(not(unix))]
        {
            tracing::warn!("Permission changes are only supported on Unix-like systems");
            return Err(HookError::Execution(
                "Permission changes are only supported on Unix-like systems".to_string(),
            ));
        }

        Ok(format!("Permissions changed successfully for {} to {:o}", path.display(), permissions))
    }

    /// Watch a file or directory for changes.
    async fn watch_file_or_directory(&self, path: &Path) -> Result<String, HookError> {
        tracing::info!("Setting up watch for: {}", path.display());

        if !path.exists() {
            return Err(HookError::Execution(format!("Path does not exist: {}", path.display())));
        }

        // For now, we'll simulate file watching
        // In a real implementation, you would use notify crate or similar
        tokio::time::sleep(Duration::from_millis(100)).await;

        Ok(format!(
            "File system watch established for: {} (Note: This is a simulated watch)",
            path.display()
        ))
    }

    /// Validate file system operation configuration.
    fn validate_config(
        &self,
        operation: &FileSystemOperation,
        path: &Path,
        target_path: Option<&Path>,
        content: Option<&str>,
        permissions: Option<u32>,
    ) -> Result<(), HookError> {
        // Check if path is provided
        if path.as_os_str().is_empty() {
            return Err(HookError::Configuration("Path cannot be empty".to_string()));
        }

        // Operation-specific validation
        match operation {
            FileSystemOperation::Copy | FileSystemOperation::Move => {
                if target_path.is_none() {
                    return Err(HookError::Configuration(format!(
                        "Target path is required for {:?} operation",
                        operation
                    )));
                }
            }
            FileSystemOperation::Write | FileSystemOperation::Append => {
                if content.is_none() {
                    return Err(HookError::Configuration(format!(
                        "Content is required for {:?} operation",
                        operation
                    )));
                }
            }
            FileSystemOperation::Chmod => {
                if permissions.is_none() {
                    return Err(HookError::Configuration(
                        "Permissions are required for chmod operation".to_string(),
                    ));
                }
                
                // Validate permission value (should be valid octal)
                if let Some(perms) = permissions {
                    if *perms > 0o777 {
                        return Err(HookError::Configuration(
                            "Invalid permissions value (must be <= 0o777)".to_string(),
                        ));
                    }
                }
            }
            _ => {} // Other operations don't need additional validation
        }

        // Security check: prevent operations outside of allowed directories
        if let Ok(canonical_path) = path.canonicalize() {
            let path_str = canonical_path.to_string_lossy();
            
            // Prevent operations on system directories
            let dangerous_paths = ["/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/boot"];
            for dangerous in &dangerous_paths {
                if path_str.starts_with(dangerous) {
                    return Err(HookError::Configuration(format!(
                        "Operation not allowed on system directory: {}",
                        dangerous
                    )));
                }
            }
        }

        Ok(())
    }

    /// Get file/directory information.
    async fn get_path_info(&self, path: &Path) -> Result<String, HookError> {
        if !path.exists() {
            return Ok(format!("Path does not exist: {}", path.display()));
        }

        let metadata = tokio::fs::metadata(path)
            .await
            .map_err(|e| HookError::Execution(format!("Failed to get metadata: {}", e)))?;

        let file_type = if metadata.is_dir() {
            "directory"
        } else if metadata.is_file() {
            "file"
        } else {
            "other"
        };

        Ok(format!(
            "Path: {} | Type: {} | Size: {} bytes | Modified: {:?}",
            path.display(),
            file_type,
            metadata.len(),
            metadata.modified().unwrap_or(std::time::SystemTime::UNIX_EPOCH)
        ))
    }
}

impl Default for FileSystemExecutor {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl HookExecutor for FileSystemExecutor {
    fn executor_type(&self) -> &'static str {
        "filesystem"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::FileSystem { .. })
    }

    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        let (operation, path, target_path, content, hook_timeout, permissions) = match &context.hook_type {
            HookType::FileSystem {
                operation,
                path,
                target_path,
                content,
                timeout,
                permissions,
            } => (
                operation,
                path,
                target_path.as_deref(),
                content.as_deref(),
                timeout.unwrap_or(self.default_timeout),
                *permissions,
            ),
            _ => {
                return Ok(HookResult::failure(
                    "Invalid hook type for file system executor".to_string(),
                    start_time.elapsed(),
                ));
            }
        };

        // Validate configuration
        if let Err(e) = self.validate_config(operation, path, target_path, content, permissions) {
            return Ok(HookResult::failure(
                format!("File system configuration error: {}", e),
                start_time.elapsed(),
            ));
        }

        tracing::info!(
            "Executing file system operation: {:?} on {}",
            operation,
            path.display()
        );

        // Execute the file system operation with timeout
        let operation_result = timeout(
            hook_timeout,
            self.execute_filesystem_operation(operation, path, target_path, content, permissions),
        )
        .await;

        let duration = start_time.elapsed();

        match operation_result {
            Ok(Ok(output)) => {
                tracing::info!("File system operation completed successfully in {:?}", duration);
                Ok(HookResult::success(Some(output), duration))
            }
            Ok(Err(e)) => {
                tracing::error!("File system operation failed: {}", e);
                Ok(HookResult::failure(e.to_string(), duration))
            }
            Err(_) => {
                tracing::error!("File system operation timed out after {:?}", hook_timeout);
                Ok(HookResult::failure(
                    format!("File system operation timed out after {:?}", hook_timeout),
                    duration,
                ))
            }
        }
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(2))
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: self.default_timeout,
            max_retries: 1,
            isolated: false, // File operations might need access to the file system
            mode: crate::hooks::types::HookExecutionMode::Sync, // File operations are typically synchronous
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::config::HookConfig;
    use crate::hooks::types::{HookExecutionMode, HookPriority, LifecycleEvent, LifecycleEventType};
    use tempfile::TempDir;

    fn create_filesystem_context(
        operation: FileSystemOperation,
        path: PathBuf,
        target_path: Option<PathBuf>,
        content: Option<String>,
    ) -> HookContext {
        let event = LifecycleEvent::SessionEnd {
            session_id: "test_session".to_string(),
            duration: Duration::from_secs(10),
            timestamp: std::time::SystemTime::now(),
        };

        let hook_type = HookType::FileSystem {
            operation,
            path,
            target_path,
            content,
            timeout: Some(Duration::from_secs(5)),
            permissions: Some(0o644),
        };

        let config = HookConfig {
            id: Some("test_fs_hook".to_string()),
            event: LifecycleEventType::SessionEnd,
            hook_type: hook_type.clone(),
            mode: HookExecutionMode::Sync,
            priority: HookPriority::NORMAL,
            condition: None,
            blocking: false,
            required: false,
            tags: Vec::new(),
            description: Some("Test file system hook".to_string()),
            depends_on: Vec::new(),
            parallel: true,
            max_retries: 0,
            timeout: Some(Duration::from_secs(5)),
        };

        HookContext::new(event, PathBuf::from("/tmp"), hook_type, config)
    }

    #[tokio::test]
    async fn test_filesystem_executor_creation() {
        let executor = FileSystemExecutor::new();
        assert_eq!(executor.executor_type(), "filesystem");
        assert_eq!(executor.default_timeout, Duration::from_secs(10));
    }

    #[tokio::test]
    async fn test_can_execute_filesystem_hook() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("test.txt");
        
        let context = create_filesystem_context(
            FileSystemOperation::Create,
            test_file,
            None,
            Some("test content".to_string()),
        );

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_create_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("test.txt");
        
        let context = create_filesystem_context(
            FileSystemOperation::Create,
            test_file.clone(),
            None,
            Some("Hello, World!".to_string()),
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("File created successfully"));
        
        // Verify file was actually created
        assert!(test_file.exists());
        let content = std::fs::read_to_string(&test_file).unwrap();
        assert_eq!(content, "Hello, World!");
    }

    #[tokio::test]
    async fn test_create_directory_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_dir = temp_dir.path().join("test_directory");
        
        let context = create_filesystem_context(
            FileSystemOperation::Create,
            test_dir.clone(),
            None,
            None,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Directory created successfully"));
        
        // Verify directory was actually created
        assert!(test_dir.exists());
        assert!(test_dir.is_dir());
    }

    #[tokio::test]
    async fn test_read_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("read_test.txt");
        
        // Create a file first
        std::fs::write(&test_file, "Content to read").unwrap();
        
        let context = create_filesystem_context(
            FileSystemOperation::Read,
            test_file,
            None,
            None,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        let output = result.output.unwrap();
        assert!(output.contains("File read successfully"));
        assert!(output.contains("Content to read"));
    }

    #[tokio::test]
    async fn test_write_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("write_test.txt");
        
        let context = create_filesystem_context(
            FileSystemOperation::Write,
            test_file.clone(),
            None,
            Some("New content".to_string()),
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("File written successfully"));
        
        // Verify content was written
        let content = std::fs::read_to_string(&test_file).unwrap();
        assert_eq!(content, "New content");
    }

    #[tokio::test]
    async fn test_append_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("append_test.txt");
        
        // Create initial file
        std::fs::write(&test_file, "Initial content").unwrap();
        
        let context = create_filesystem_context(
            FileSystemOperation::Append,
            test_file.clone(),
            None,
            Some("\nAppended content".to_string()),
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Content appended successfully"));
        
        // Verify content was appended
        let content = std::fs::read_to_string(&test_file).unwrap();
        assert_eq!(content, "Initial content\nAppended content");
    }

    #[tokio::test]
    async fn test_copy_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let source_file = temp_dir.path().join("source.txt");
        let target_file = temp_dir.path().join("target.txt");
        
        // Create source file
        std::fs::write(&source_file, "Content to copy").unwrap();
        
        let context = create_filesystem_context(
            FileSystemOperation::Copy,
            source_file.clone(),
            Some(target_file.clone()),
            None,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("File copied successfully"));
        
        // Verify file was copied
        assert!(target_file.exists());
        let content = std::fs::read_to_string(&target_file).unwrap();
        assert_eq!(content, "Content to copy");
    }

    #[tokio::test]
    async fn test_delete_file_operation() {
        let executor = FileSystemExecutor::new();
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("delete_test.txt");
        
        // Create file to delete
        std::fs::write(&test_file, "To be deleted").unwrap();
        assert!(test_file.exists());
        
        let context = create_filesystem_context(
            FileSystemOperation::Delete,
            test_file.clone(),
            None,
            None,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("File deleted successfully"));
        
        // Verify file was deleted
        assert!(!test_file.exists());
    }

    #[tokio::test]
    async fn test_invalid_configuration() {
        let executor = FileSystemExecutor::new();
        
        let context = create_filesystem_context(
            FileSystemOperation::Copy,
            PathBuf::from("/tmp/source.txt"),
            None, // Missing target path
            None,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.error.unwrap().contains("Target path is required"));
    }

    #[test]
    fn test_filesystem_operation_serialization() {
        let operation = FileSystemOperation::Create;
        let serialized = serde_json::to_string(&operation).unwrap();
        assert_eq!(serialized, "\"create\"");

        let deserialized: FileSystemOperation = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized, FileSystemOperation::Create);
    }
}
