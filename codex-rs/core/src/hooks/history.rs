//! Hook execution history and logging system.

use std::collections::VecDeque;
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use std::time::SystemTime;

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use crate::hooks::types::{HookError, HookResult, LifecycleEventType};

/// Configuration for hook execution history and logging.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryConfig {
    /// Whether to enable history logging.
    pub enabled: bool,
    /// Maximum number of execution records to keep in memory.
    pub max_memory_records: usize,
    /// Whether to persist history to disk.
    pub persist_to_disk: bool,
    /// Directory for storing history files.
    pub history_directory: PathBuf,
    /// Maximum size of a single history file in bytes.
    pub max_file_size: u64,
    /// Maximum number of history files to keep.
    pub max_files: usize,
    /// Log level for hook execution details.
    pub log_level: LogLevel,
    /// Whether to include hook output in history.
    pub include_output: bool,
    /// Whether to include environment variables in history.
    pub include_environment: bool,
}

impl Default for HistoryConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_memory_records: 10000,
            persist_to_disk: true,
            history_directory: PathBuf::from("~/.codex/hooks/history"),
            max_file_size: 10 * 1024 * 1024, // 10MB
            max_files: 10,
            log_level: LogLevel::Info,
            include_output: true,
            include_environment: false,
        }
    }
}

/// Log levels for hook execution history.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum LogLevel {
    Error,
    Warn,
    Info,
    Debug,
    Trace,
}

/// Detailed execution record for history tracking.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionHistoryRecord {
    /// Unique identifier for this execution.
    pub execution_id: String,
    /// Hook identifier.
    pub hook_id: String,
    /// Event type that triggered the hook.
    pub event_type: LifecycleEventType,
    /// When the execution started.
    pub started_at: DateTime<Utc>,
    /// When the execution completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Execution duration.
    pub duration: std::time::Duration,
    /// Whether the execution was successful.
    pub success: bool,
    /// Exit code (for script hooks).
    pub exit_code: Option<i32>,
    /// Hook output (if enabled).
    pub output: Option<String>,
    /// Error message (if failed).
    pub error_message: Option<String>,
    /// Number of retry attempts.
    pub retry_attempts: u32,
    /// Whether the execution was cancelled.
    pub cancelled: bool,
    /// Environment variables (if enabled).
    pub environment: Option<std::collections::HashMap<String, String>>,
    /// Hook configuration snapshot.
    pub hook_config: serde_json::Value,
    /// Additional metadata.
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

/// Summary statistics for execution history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistorySummary {
    /// Total number of executions recorded.
    pub total_executions: usize,
    /// Number of successful executions.
    pub successful_executions: usize,
    /// Number of failed executions.
    pub failed_executions: usize,
    /// Number of cancelled executions.
    pub cancelled_executions: usize,
    /// Date range of recorded executions.
    pub date_range: Option<(DateTime<Utc>, DateTime<Utc>)>,
    /// Most active hook by execution count.
    pub most_active_hook: Option<String>,
    /// Hook with highest failure rate.
    pub least_reliable_hook: Option<String>,
    /// Average execution time.
    pub average_execution_time: std::time::Duration,
}

/// Filter criteria for querying execution history.
#[derive(Debug, Clone, Default)]
pub struct HistoryFilter {
    /// Filter by hook ID.
    pub hook_id: Option<String>,
    /// Filter by event type.
    pub event_type: Option<LifecycleEventType>,
    /// Filter by success status.
    pub success: Option<bool>,
    /// Filter by date range.
    pub date_range: Option<(DateTime<Utc>, DateTime<Utc>)>,
    /// Maximum number of records to return.
    pub limit: Option<usize>,
    /// Skip this many records (for pagination).
    pub offset: Option<usize>,
}

/// Hook execution history manager.
#[derive(Debug)]
pub struct HistoryManager {
    config: HistoryConfig,
    memory_records: Arc<RwLock<VecDeque<ExecutionHistoryRecord>>>,
    current_file: Arc<RwLock<Option<BufWriter<File>>>>,
    current_file_size: Arc<RwLock<u64>>,
    file_counter: Arc<RwLock<usize>>,
}

impl HistoryManager {
    /// Create a new history manager with the given configuration.
    pub fn new(config: HistoryConfig) -> Result<Self, HookError> {
        let manager = Self {
            config,
            memory_records: Arc::new(RwLock::new(VecDeque::new())),
            current_file: Arc::new(RwLock::new(None)),
            current_file_size: Arc::new(RwLock::new(0)),
            file_counter: Arc::new(RwLock::new(0)),
        };

        if manager.config.persist_to_disk {
            manager.ensure_history_directory()?;
            manager.initialize_file_logging()?;
        }

        Ok(manager)
    }

    /// Create a history manager with default configuration.
    pub fn default() -> Result<Self, HookError> {
        Self::new(HistoryConfig::default())
    }

    /// Record a hook execution in history.
    pub fn record_execution(
        &self,
        execution_id: String,
        hook_id: String,
        event_type: LifecycleEventType,
        started_at: DateTime<Utc>,
        result: &HookResult,
        retry_attempts: u32,
        cancelled: bool,
        hook_config: serde_json::Value,
        environment: Option<std::collections::HashMap<String, String>>,
    ) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        let record = ExecutionHistoryRecord {
            execution_id,
            hook_id,
            event_type,
            started_at,
            completed_at: Some(Utc::now()),
            duration: result.duration,
            success: result.success,
            exit_code: None, // TODO: Extract from result metadata if available
            output: if self.config.include_output { result.output.clone() } else { None },
            error_message: result.error.clone(),
            retry_attempts,
            cancelled,
            environment: if self.config.include_environment { environment } else { None },
            hook_config,
            metadata: result.metadata.clone().into_iter().collect(),
        };

        // Add to memory
        self.add_to_memory(record.clone())?;

        // Persist to disk if enabled
        if self.config.persist_to_disk {
            self.persist_to_disk(&record)?;
        }

        Ok(())
    }

    /// Add a record to memory storage.
    fn add_to_memory(&self, record: ExecutionHistoryRecord) -> Result<(), HookError> {
        if let Ok(mut records) = self.memory_records.write() {
            records.push_back(record);

            // Maintain size limit
            while records.len() > self.config.max_memory_records {
                records.pop_front();
            }
        }
        Ok(())
    }

    /// Persist a record to disk.
    fn persist_to_disk(&self, record: &ExecutionHistoryRecord) -> Result<(), HookError> {
        let json_line = serde_json::to_string(record)
            .map_err(|e| HookError::Execution(format!("Failed to serialize history record: {}", e)))?;

        let line_size = json_line.len() as u64 + 1; // +1 for newline

        // Check if we need to rotate the file
        if let Ok(current_size) = self.current_file_size.read() {
            if *current_size + line_size > self.config.max_file_size {
                self.rotate_log_file()?;
            }
        }

        // Write to current file
        if let Ok(mut file_opt) = self.current_file.write() {
            if let Some(ref mut writer) = *file_opt {
                writeln!(writer, "{}", json_line)
                    .map_err(|e| HookError::Execution(format!("Failed to write history record: {}", e)))?;
                writer.flush()
                    .map_err(|e| HookError::Execution(format!("Failed to flush history file: {}", e)))?;

                // Update file size
                if let Ok(mut size) = self.current_file_size.write() {
                    *size += line_size;
                }
            }
        }

        Ok(())
    }

    /// Query execution history with filters.
    pub fn query_history(&self, filter: HistoryFilter) -> Result<Vec<ExecutionHistoryRecord>, HookError> {
        let records = if let Ok(memory_records) = self.memory_records.read() {
            memory_records.clone().into_iter().collect::<Vec<_>>()
        } else {
            return Err(HookError::Execution("Failed to read memory records".to_string()));
        };

        let mut filtered_records: Vec<_> = records
            .into_iter()
            .filter(|record| self.matches_filter(record, &filter))
            .collect();

        // Sort by started_at descending (most recent first)
        filtered_records.sort_by(|a, b| b.started_at.cmp(&a.started_at));

        // Apply offset and limit
        if let Some(offset) = filter.offset {
            if offset < filtered_records.len() {
                filtered_records = filtered_records.into_iter().skip(offset).collect();
            } else {
                filtered_records.clear();
            }
        }

        if let Some(limit) = filter.limit {
            filtered_records.truncate(limit);
        }

        Ok(filtered_records)
    }

    /// Check if a record matches the given filter.
    fn matches_filter(&self, record: &ExecutionHistoryRecord, filter: &HistoryFilter) -> bool {
        if let Some(ref hook_id) = filter.hook_id {
            if record.hook_id != *hook_id {
                return false;
            }
        }

        if let Some(event_type) = filter.event_type {
            if record.event_type != event_type {
                return false;
            }
        }

        if let Some(success) = filter.success {
            if record.success != success {
                return false;
            }
        }

        if let Some((start, end)) = filter.date_range {
            if record.started_at < start || record.started_at > end {
                return false;
            }
        }

        true
    }

    /// Get summary statistics for execution history.
    pub fn get_summary(&self) -> Result<HistorySummary, HookError> {
        let records = if let Ok(memory_records) = self.memory_records.read() {
            memory_records.clone().into_iter().collect::<Vec<_>>()
        } else {
            return Err(HookError::Execution("Failed to read memory records".to_string()));
        };

        if records.is_empty() {
            return Ok(HistorySummary {
                total_executions: 0,
                successful_executions: 0,
                failed_executions: 0,
                cancelled_executions: 0,
                date_range: None,
                most_active_hook: None,
                least_reliable_hook: None,
                average_execution_time: std::time::Duration::ZERO,
            });
        }

        let total_executions = records.len();
        let successful_executions = records.iter().filter(|r| r.success).count();
        let failed_executions = records.iter().filter(|r| !r.success && !r.cancelled).count();
        let cancelled_executions = records.iter().filter(|r| r.cancelled).count();

        let date_range = {
            let dates: Vec<_> = records.iter().map(|r| r.started_at).collect();
            if dates.is_empty() {
                None
            } else {
                let min_date = dates.iter().min().unwrap();
                let max_date = dates.iter().max().unwrap();
                Some((*min_date, *max_date))
            }
        };

        // Find most active hook
        let mut hook_counts = std::collections::HashMap::new();
        for record in &records {
            *hook_counts.entry(record.hook_id.clone()).or_insert(0) += 1;
        }
        let most_active_hook = hook_counts
            .into_iter()
            .max_by_key(|(_, count)| *count)
            .map(|(hook_id, _)| hook_id);

        // Find least reliable hook (highest failure rate with minimum executions)
        let mut hook_stats = std::collections::HashMap::new();
        for record in &records {
            let stats = hook_stats.entry(record.hook_id.clone()).or_insert((0, 0)); // (total, failures)
            stats.0 += 1;
            if !record.success {
                stats.1 += 1;
            }
        }
        let least_reliable_hook = hook_stats
            .into_iter()
            .filter(|(_, (total, _))| *total >= 5) // Minimum 5 executions
            .max_by(|(_, (total_a, failures_a)), (_, (total_b, failures_b))| {
                let rate_a = *failures_a as f64 / *total_a as f64;
                let rate_b = *failures_b as f64 / *total_b as f64;
                rate_a.partial_cmp(&rate_b).unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|(hook_id, _)| hook_id);

        // Calculate average execution time
        let total_duration: std::time::Duration = records.iter().map(|r| r.duration).sum();
        let average_execution_time = total_duration / total_executions as u32;

        Ok(HistorySummary {
            total_executions,
            successful_executions,
            failed_executions,
            cancelled_executions,
            date_range,
            most_active_hook,
            least_reliable_hook,
            average_execution_time,
        })
    }

    /// Clear all history records.
    pub fn clear_history(&self) -> Result<(), HookError> {
        if let Ok(mut records) = self.memory_records.write() {
            records.clear();
        }

        // TODO: Also clear disk files if needed
        Ok(())
    }

    /// Export history to JSON file.
    pub fn export_to_file(&self, path: &Path) -> Result<(), HookError> {
        let records = if let Ok(memory_records) = self.memory_records.read() {
            memory_records.clone().into_iter().collect::<Vec<_>>()
        } else {
            return Err(HookError::Execution("Failed to read memory records".to_string()));
        };

        let json = serde_json::to_string_pretty(&records)
            .map_err(|e| HookError::Execution(format!("Failed to serialize history: {}", e)))?;

        std::fs::write(path, json)
            .map_err(|e| HookError::Execution(format!("Failed to write history file: {}", e)))?;

        Ok(())
    }

    /// Ensure the history directory exists.
    fn ensure_history_directory(&self) -> Result<(), HookError> {
        let expanded_path = self.expand_path(&self.config.history_directory)?;
        std::fs::create_dir_all(&expanded_path)
            .map_err(|e| HookError::Configuration(format!("Failed to create history directory: {}", e)))?;
        Ok(())
    }

    /// Initialize file logging.
    fn initialize_file_logging(&self) -> Result<(), HookError> {
        let file_path = self.get_current_log_file_path()?;
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&file_path)
            .map_err(|e| HookError::Configuration(format!("Failed to open history file: {}", e)))?;

        let writer = BufWriter::new(file);
        
        if let Ok(mut current_file) = self.current_file.write() {
            *current_file = Some(writer);
        }

        // Get current file size
        let metadata = std::fs::metadata(&file_path)
            .map_err(|e| HookError::Configuration(format!("Failed to get file metadata: {}", e)))?;
        
        if let Ok(mut size) = self.current_file_size.write() {
            *size = metadata.len();
        }

        Ok(())
    }

    /// Rotate the current log file.
    fn rotate_log_file(&self) -> Result<(), HookError> {
        // Close current file
        if let Ok(mut current_file) = self.current_file.write() {
            *current_file = None;
        }

        // Increment file counter
        if let Ok(mut counter) = self.file_counter.write() {
            *counter += 1;
        }

        // Clean up old files if necessary
        self.cleanup_old_files()?;

        // Initialize new file
        self.initialize_file_logging()?;

        Ok(())
    }

    /// Clean up old log files.
    fn cleanup_old_files(&self) -> Result<(), HookError> {
        let history_dir = self.expand_path(&self.config.history_directory)?;
        
        let mut log_files = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&history_dir) {
            for entry in entries.flatten() {
                if let Some(name) = entry.file_name().to_str() {
                    if name.starts_with("hooks_") && name.ends_with(".jsonl") {
                        if let Ok(metadata) = entry.metadata() {
                            if let Ok(modified) = metadata.modified() {
                                log_files.push((entry.path(), modified));
                            }
                        }
                    }
                }
            }
        }

        // Sort by modification time (oldest first)
        log_files.sort_by_key(|(_, modified)| *modified);

        // Remove excess files
        while log_files.len() >= self.config.max_files {
            if let Some((path, _)) = log_files.remove(0) {
                let _ = std::fs::remove_file(path); // Ignore errors
            }
        }

        Ok(())
    }

    /// Get the current log file path.
    fn get_current_log_file_path(&self) -> Result<PathBuf, HookError> {
        let history_dir = self.expand_path(&self.config.history_directory)?;
        let counter = if let Ok(counter) = self.file_counter.read() {
            *counter
        } else {
            0
        };
        
        let filename = format!("hooks_{:04}.jsonl", counter);
        Ok(history_dir.join(filename))
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
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn create_test_config() -> HistoryConfig {
        let temp_dir = TempDir::new().unwrap();
        HistoryConfig {
            enabled: true,
            max_memory_records: 100,
            persist_to_disk: false, // Disable for tests
            history_directory: temp_dir.path().to_path_buf(),
            max_file_size: 1024,
            max_files: 3,
            log_level: LogLevel::Info,
            include_output: true,
            include_environment: false,
        }
    }

    fn create_test_result(success: bool) -> HookResult {
        HookResult {
            success,
            output: Some("test output".to_string()),
            error: if success { None } else { Some("test error".to_string()) },
            duration: std::time::Duration::from_millis(100),
            metadata: std::collections::HashMap::new(),
        }
    }

    #[test]
    fn test_history_manager_creation() {
        let config = create_test_config();
        let manager = HistoryManager::new(config).unwrap();
        
        let summary = manager.get_summary().unwrap();
        assert_eq!(summary.total_executions, 0);
    }

    #[test]
    fn test_record_execution() {
        let config = create_test_config();
        let manager = HistoryManager::new(config).unwrap();
        
        let result = create_test_result(true);
        manager.record_execution(
            "exec_1".to_string(),
            "hook_1".to_string(),
            LifecycleEventType::SessionStart,
            Utc::now(),
            &result,
            0,
            false,
            serde_json::json!({}),
            None,
        ).unwrap();

        let summary = manager.get_summary().unwrap();
        assert_eq!(summary.total_executions, 1);
        assert_eq!(summary.successful_executions, 1);
        assert_eq!(summary.failed_executions, 0);
    }

    #[test]
    fn test_query_history_with_filter() {
        let config = create_test_config();
        let manager = HistoryManager::new(config).unwrap();
        
        // Record multiple executions
        let result1 = create_test_result(true);
        let result2 = create_test_result(false);
        
        manager.record_execution(
            "exec_1".to_string(),
            "hook_1".to_string(),
            LifecycleEventType::SessionStart,
            Utc::now(),
            &result1,
            0,
            false,
            serde_json::json!({}),
            None,
        ).unwrap();

        manager.record_execution(
            "exec_2".to_string(),
            "hook_2".to_string(),
            LifecycleEventType::TaskStart,
            Utc::now(),
            &result2,
            1,
            false,
            serde_json::json!({}),
            None,
        ).unwrap();

        // Query successful executions only
        let filter = HistoryFilter {
            success: Some(true),
            ..Default::default()
        };
        let records = manager.query_history(filter).unwrap();
        assert_eq!(records.len(), 1);
        assert!(records[0].success);

        // Query by hook ID
        let filter = HistoryFilter {
            hook_id: Some("hook_2".to_string()),
            ..Default::default()
        };
        let records = manager.query_history(filter).unwrap();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].hook_id, "hook_2");
    }

    #[test]
    fn test_history_summary() {
        let config = create_test_config();
        let manager = HistoryManager::new(config).unwrap();
        
        // Record executions for different hooks
        for i in 0..5 {
            let result = create_test_result(i % 2 == 0); // Alternate success/failure
            manager.record_execution(
                format!("exec_{}", i),
                format!("hook_{}", i % 2), // Two different hooks
                LifecycleEventType::SessionStart,
                Utc::now(),
                &result,
                0,
                false,
                serde_json::json!({}),
                None,
            ).unwrap();
        }

        let summary = manager.get_summary().unwrap();
        assert_eq!(summary.total_executions, 5);
        assert_eq!(summary.successful_executions, 3);
        assert_eq!(summary.failed_executions, 2);
        assert!(summary.most_active_hook.is_some());
        assert!(summary.date_range.is_some());
    }
}
