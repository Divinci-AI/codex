//! Hook execution metrics and monitoring system.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};

use crate::hooks::types::{HookError, LifecycleEventType};

/// Comprehensive metrics for hook execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookMetrics {
    /// Total number of hook executions.
    pub total_executions: u64,
    /// Number of successful executions.
    pub successful_executions: u64,
    /// Number of failed executions.
    pub failed_executions: u64,
    /// Number of timed out executions.
    pub timed_out_executions: u64,
    /// Number of cancelled executions.
    pub cancelled_executions: u64,
    /// Total execution time across all hooks.
    pub total_execution_time: Duration,
    /// Average execution time.
    pub average_execution_time: Duration,
    /// Minimum execution time.
    pub min_execution_time: Duration,
    /// Maximum execution time.
    pub max_execution_time: Duration,
    /// Success rate (0.0 to 1.0).
    pub success_rate: f64,
    /// Metrics by event type.
    pub by_event_type: HashMap<LifecycleEventType, EventTypeMetrics>,
    /// Metrics by hook ID.
    pub by_hook_id: HashMap<String, HookIdMetrics>,
    /// Recent execution history.
    pub recent_executions: Vec<ExecutionRecord>,
    /// Performance percentiles.
    pub performance_percentiles: PerformancePercentiles,
    /// Error statistics.
    pub error_stats: ErrorStatistics,
}

/// Metrics for a specific event type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventTypeMetrics {
    pub total_executions: u64,
    pub successful_executions: u64,
    pub failed_executions: u64,
    pub average_execution_time: Duration,
    pub success_rate: f64,
}

/// Metrics for a specific hook ID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookIdMetrics {
    pub hook_id: String,
    pub total_executions: u64,
    pub successful_executions: u64,
    pub failed_executions: u64,
    pub average_execution_time: Duration,
    pub last_execution: Option<SystemTime>,
    pub success_rate: f64,
    pub error_count_by_type: HashMap<String, u64>,
}

/// Performance percentiles for execution times.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformancePercentiles {
    pub p50: Duration,
    pub p90: Duration,
    pub p95: Duration,
    pub p99: Duration,
}

/// Error statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorStatistics {
    pub total_errors: u64,
    pub error_count_by_type: HashMap<String, u64>,
    pub most_common_error: Option<String>,
    pub recent_errors: Vec<ErrorRecord>,
}

/// Record of a single hook execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRecord {
    pub hook_id: String,
    pub event_type: LifecycleEventType,
    pub started_at: SystemTime,
    pub duration: Duration,
    pub success: bool,
    pub error_message: Option<String>,
    pub retry_count: u32,
}

/// Record of an error occurrence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRecord {
    pub hook_id: String,
    pub event_type: LifecycleEventType,
    pub error_type: String,
    pub error_message: String,
    pub occurred_at: SystemTime,
    pub retry_count: u32,
}

/// Configuration for metrics collection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsConfig {
    /// Whether to collect metrics.
    pub enabled: bool,
    /// Maximum number of recent executions to keep.
    pub max_recent_executions: usize,
    /// Maximum number of recent errors to keep.
    pub max_recent_errors: usize,
    /// Whether to collect detailed performance percentiles.
    pub collect_percentiles: bool,
    /// Interval for aggregating metrics.
    pub aggregation_interval: Duration,
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_recent_executions: 1000,
            max_recent_errors: 100,
            collect_percentiles: true,
            aggregation_interval: Duration::from_secs(60),
        }
    }
}

/// Thread-safe metrics collector.
#[derive(Debug)]
pub struct MetricsCollector {
    config: MetricsConfig,
    metrics: Arc<RwLock<HookMetrics>>,
    execution_times: Arc<RwLock<Vec<Duration>>>,
}

impl MetricsCollector {
    /// Create a new metrics collector.
    pub fn new(config: MetricsConfig) -> Self {
        Self {
            config,
            metrics: Arc::new(RwLock::new(HookMetrics::default())),
            execution_times: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Create a metrics collector with default configuration.
    pub fn default() -> Self {
        Self::new(MetricsConfig::default())
    }

    /// Record a hook execution.
    pub fn record_execution(
        &self,
        hook_id: &str,
        event_type: LifecycleEventType,
        duration: Duration,
        success: bool,
        error_message: Option<String>,
        retry_count: u32,
    ) {
        if !self.config.enabled {
            return;
        }

        let now = SystemTime::now();
        let execution_record = ExecutionRecord {
            hook_id: hook_id.to_string(),
            event_type,
            started_at: now,
            duration,
            success,
            error_message: error_message.clone(),
            retry_count,
        };

        // Update metrics
        if let Ok(mut metrics) = self.metrics.write() {
            self.update_metrics(&mut metrics, &execution_record);
        }

        // Store execution time for percentile calculations
        if self.config.collect_percentiles {
            if let Ok(mut times) = self.execution_times.write() {
                times.push(duration);
                // Keep only recent times to prevent unbounded growth
                if times.len() > self.config.max_recent_executions {
                    times.drain(0..times.len() - self.config.max_recent_executions);
                }
            }
        }

        // Record error if applicable
        if !success {
            if let Some(error_msg) = error_message {
                self.record_error(hook_id, event_type, &error_msg, retry_count);
            }
        }
    }

    /// Record an error occurrence.
    fn record_error(
        &self,
        hook_id: &str,
        event_type: LifecycleEventType,
        error_message: &str,
        retry_count: u32,
    ) {
        let error_type = self.classify_error(error_message);
        let error_record = ErrorRecord {
            hook_id: hook_id.to_string(),
            event_type,
            error_type: error_type.clone(),
            error_message: error_message.to_string(),
            occurred_at: SystemTime::now(),
            retry_count,
        };

        if let Ok(mut metrics) = self.metrics.write() {
            // Update error statistics
            metrics.error_stats.total_errors += 1;
            *metrics.error_stats.error_count_by_type.entry(error_type).or_insert(0) += 1;

            // Update most common error
            let most_common = metrics.error_stats.error_count_by_type
                .iter()
                .max_by_key(|(_, count)| *count)
                .map(|(error_type, _)| error_type.clone());
            metrics.error_stats.most_common_error = most_common;

            // Add to recent errors
            metrics.error_stats.recent_errors.push(error_record);
            if metrics.error_stats.recent_errors.len() > self.config.max_recent_errors {
                metrics.error_stats.recent_errors.remove(0);
            }
        }
    }

    /// Update the main metrics with a new execution record.
    fn update_metrics(&self, metrics: &mut HookMetrics, record: &ExecutionRecord) {
        // Update overall metrics
        metrics.total_executions += 1;
        if record.success {
            metrics.successful_executions += 1;
        } else {
            metrics.failed_executions += 1;
        }

        metrics.total_execution_time += record.duration;
        metrics.average_execution_time = metrics.total_execution_time / metrics.total_executions as u32;

        if metrics.min_execution_time == Duration::ZERO || record.duration < metrics.min_execution_time {
            metrics.min_execution_time = record.duration;
        }
        if record.duration > metrics.max_execution_time {
            metrics.max_execution_time = record.duration;
        }

        metrics.success_rate = metrics.successful_executions as f64 / metrics.total_executions as f64;

        // Update event type metrics
        let event_metrics = metrics.by_event_type.entry(record.event_type).or_insert_with(|| EventTypeMetrics {
            total_executions: 0,
            successful_executions: 0,
            failed_executions: 0,
            average_execution_time: Duration::ZERO,
            success_rate: 0.0,
        });

        event_metrics.total_executions += 1;
        if record.success {
            event_metrics.successful_executions += 1;
        } else {
            event_metrics.failed_executions += 1;
        }
        event_metrics.success_rate = event_metrics.successful_executions as f64 / event_metrics.total_executions as f64;

        // Update hook ID metrics
        let hook_metrics = metrics.by_hook_id.entry(record.hook_id.clone()).or_insert_with(|| HookIdMetrics {
            hook_id: record.hook_id.clone(),
            total_executions: 0,
            successful_executions: 0,
            failed_executions: 0,
            average_execution_time: Duration::ZERO,
            last_execution: None,
            success_rate: 0.0,
            error_count_by_type: HashMap::new(),
        });

        hook_metrics.total_executions += 1;
        if record.success {
            hook_metrics.successful_executions += 1;
        } else {
            hook_metrics.failed_executions += 1;
        }
        hook_metrics.last_execution = Some(record.started_at);
        hook_metrics.success_rate = hook_metrics.successful_executions as f64 / hook_metrics.total_executions as f64;

        // Add to recent executions
        metrics.recent_executions.push(record.clone());
        if metrics.recent_executions.len() > self.config.max_recent_executions {
            metrics.recent_executions.remove(0);
        }

        // Update performance percentiles
        if self.config.collect_percentiles {
            metrics.performance_percentiles = self.calculate_percentiles();
        }
    }

    /// Calculate performance percentiles from execution times.
    fn calculate_percentiles(&self) -> PerformancePercentiles {
        if let Ok(times) = self.execution_times.read() {
            if times.is_empty() {
                return PerformancePercentiles {
                    p50: Duration::ZERO,
                    p90: Duration::ZERO,
                    p95: Duration::ZERO,
                    p99: Duration::ZERO,
                };
            }

            let mut sorted_times = times.clone();
            sorted_times.sort();

            let len = sorted_times.len();
            PerformancePercentiles {
                p50: sorted_times[len * 50 / 100],
                p90: sorted_times[len * 90 / 100],
                p95: sorted_times[len * 95 / 100],
                p99: sorted_times[len * 99 / 100],
            }
        } else {
            PerformancePercentiles {
                p50: Duration::ZERO,
                p90: Duration::ZERO,
                p95: Duration::ZERO,
                p99: Duration::ZERO,
            }
        }
    }

    /// Classify an error message into a type.
    fn classify_error(&self, error_message: &str) -> String {
        let error_lower = error_message.to_lowercase();
        
        if error_lower.contains("timeout") || error_lower.contains("timed out") {
            "timeout".to_string()
        } else if error_lower.contains("permission") || error_lower.contains("access denied") {
            "permission".to_string()
        } else if error_lower.contains("network") || error_lower.contains("connection") {
            "network".to_string()
        } else if error_lower.contains("not found") || error_lower.contains("404") {
            "not_found".to_string()
        } else if error_lower.contains("configuration") || error_lower.contains("config") {
            "configuration".to_string()
        } else if error_lower.contains("validation") || error_lower.contains("invalid") {
            "validation".to_string()
        } else {
            "unknown".to_string()
        }
    }

    /// Get current metrics snapshot.
    pub fn get_metrics(&self) -> Result<HookMetrics, HookError> {
        self.metrics.read()
            .map(|metrics| metrics.clone())
            .map_err(|e| HookError::Execution(format!("Failed to read metrics: {}", e)))
    }

    /// Get metrics for a specific hook ID.
    pub fn get_hook_metrics(&self, hook_id: &str) -> Result<Option<HookIdMetrics>, HookError> {
        self.metrics.read()
            .map(|metrics| metrics.by_hook_id.get(hook_id).cloned())
            .map_err(|e| HookError::Execution(format!("Failed to read hook metrics: {}", e)))
    }

    /// Get metrics for a specific event type.
    pub fn get_event_type_metrics(&self, event_type: LifecycleEventType) -> Result<Option<EventTypeMetrics>, HookError> {
        self.metrics.read()
            .map(|metrics| metrics.by_event_type.get(&event_type).cloned())
            .map_err(|e| HookError::Execution(format!("Failed to read event type metrics: {}", e)))
    }

    /// Reset all metrics.
    pub fn reset_metrics(&self) -> Result<(), HookError> {
        if let Ok(mut metrics) = self.metrics.write() {
            *metrics = HookMetrics::default();
        }
        if let Ok(mut times) = self.execution_times.write() {
            times.clear();
        }
        Ok(())
    }

    /// Export metrics to JSON.
    pub fn export_metrics(&self) -> Result<String, HookError> {
        let metrics = self.get_metrics()?;
        serde_json::to_string_pretty(&metrics)
            .map_err(|e| HookError::Execution(format!("Failed to serialize metrics: {}", e)))
    }

    /// Get performance summary.
    pub fn get_performance_summary(&self) -> Result<PerformanceSummary, HookError> {
        let metrics = self.get_metrics()?;
        
        Ok(PerformanceSummary {
            total_executions: metrics.total_executions,
            success_rate: metrics.success_rate,
            average_execution_time: metrics.average_execution_time,
            p95_execution_time: metrics.performance_percentiles.p95,
            most_common_error: metrics.error_stats.most_common_error,
            slowest_hook: self.find_slowest_hook(&metrics),
            most_reliable_hook: self.find_most_reliable_hook(&metrics),
        })
    }

    /// Find the slowest hook by average execution time.
    fn find_slowest_hook(&self, metrics: &HookMetrics) -> Option<String> {
        metrics.by_hook_id
            .values()
            .max_by_key(|hook_metrics| hook_metrics.average_execution_time)
            .map(|hook_metrics| hook_metrics.hook_id.clone())
    }

    /// Find the most reliable hook by success rate.
    fn find_most_reliable_hook(&self, metrics: &HookMetrics) -> Option<String> {
        metrics.by_hook_id
            .values()
            .filter(|hook_metrics| hook_metrics.total_executions >= 5) // Minimum executions for reliability
            .max_by(|a, b| a.success_rate.partial_cmp(&b.success_rate).unwrap_or(std::cmp::Ordering::Equal))
            .map(|hook_metrics| hook_metrics.hook_id.clone())
    }
}

/// Performance summary for quick overview.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceSummary {
    pub total_executions: u64,
    pub success_rate: f64,
    pub average_execution_time: Duration,
    pub p95_execution_time: Duration,
    pub most_common_error: Option<String>,
    pub slowest_hook: Option<String>,
    pub most_reliable_hook: Option<String>,
}

impl Default for HookMetrics {
    fn default() -> Self {
        Self {
            total_executions: 0,
            successful_executions: 0,
            failed_executions: 0,
            timed_out_executions: 0,
            cancelled_executions: 0,
            total_execution_time: Duration::ZERO,
            average_execution_time: Duration::ZERO,
            min_execution_time: Duration::ZERO,
            max_execution_time: Duration::ZERO,
            success_rate: 0.0,
            by_event_type: HashMap::new(),
            by_hook_id: HashMap::new(),
            recent_executions: Vec::new(),
            performance_percentiles: PerformancePercentiles {
                p50: Duration::ZERO,
                p90: Duration::ZERO,
                p95: Duration::ZERO,
                p99: Duration::ZERO,
            },
            error_stats: ErrorStatistics {
                total_errors: 0,
                error_count_by_type: HashMap::new(),
                most_common_error: None,
                recent_errors: Vec::new(),
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_collector_creation() {
        let collector = MetricsCollector::default();
        let metrics = collector.get_metrics().unwrap();
        
        assert_eq!(metrics.total_executions, 0);
        assert_eq!(metrics.success_rate, 0.0);
    }

    #[test]
    fn test_record_successful_execution() {
        let collector = MetricsCollector::default();
        
        collector.record_execution(
            "test_hook",
            LifecycleEventType::SessionStart,
            Duration::from_millis(100),
            true,
            None,
            0,
        );

        let metrics = collector.get_metrics().unwrap();
        assert_eq!(metrics.total_executions, 1);
        assert_eq!(metrics.successful_executions, 1);
        assert_eq!(metrics.failed_executions, 0);
        assert_eq!(metrics.success_rate, 1.0);
        assert_eq!(metrics.average_execution_time, Duration::from_millis(100));
    }

    #[test]
    fn test_record_failed_execution() {
        let collector = MetricsCollector::default();
        
        collector.record_execution(
            "test_hook",
            LifecycleEventType::SessionStart,
            Duration::from_millis(50),
            false,
            Some("Test error".to_string()),
            1,
        );

        let metrics = collector.get_metrics().unwrap();
        assert_eq!(metrics.total_executions, 1);
        assert_eq!(metrics.successful_executions, 0);
        assert_eq!(metrics.failed_executions, 1);
        assert_eq!(metrics.success_rate, 0.0);
        assert_eq!(metrics.error_stats.total_errors, 1);
    }

    #[test]
    fn test_hook_specific_metrics() {
        let collector = MetricsCollector::default();
        
        collector.record_execution(
            "hook1",
            LifecycleEventType::SessionStart,
            Duration::from_millis(100),
            true,
            None,
            0,
        );
        
        collector.record_execution(
            "hook2",
            LifecycleEventType::TaskStart,
            Duration::from_millis(200),
            false,
            Some("Hook2 error".to_string()),
            0,
        );

        let hook1_metrics = collector.get_hook_metrics("hook1").unwrap().unwrap();
        assert_eq!(hook1_metrics.total_executions, 1);
        assert_eq!(hook1_metrics.success_rate, 1.0);

        let hook2_metrics = collector.get_hook_metrics("hook2").unwrap().unwrap();
        assert_eq!(hook2_metrics.total_executions, 1);
        assert_eq!(hook2_metrics.success_rate, 0.0);
    }

    #[test]
    fn test_error_classification() {
        let collector = MetricsCollector::default();
        
        assert_eq!(collector.classify_error("Connection timeout"), "timeout");
        assert_eq!(collector.classify_error("Permission denied"), "permission");
        assert_eq!(collector.classify_error("Network error"), "network");
        assert_eq!(collector.classify_error("File not found"), "not_found");
        assert_eq!(collector.classify_error("Invalid configuration"), "configuration");
        assert_eq!(collector.classify_error("Some other error"), "unknown");
    }

    #[test]
    fn test_performance_summary() {
        let collector = MetricsCollector::default();
        
        // Record some executions
        collector.record_execution("fast_hook", LifecycleEventType::SessionStart, Duration::from_millis(50), true, None, 0);
        collector.record_execution("slow_hook", LifecycleEventType::SessionStart, Duration::from_millis(500), true, None, 0);
        collector.record_execution("reliable_hook", LifecycleEventType::SessionStart, Duration::from_millis(100), true, None, 0);
        
        // Add more executions to reliable_hook to make it statistically significant
        for _ in 0..5 {
            collector.record_execution("reliable_hook", LifecycleEventType::SessionStart, Duration::from_millis(100), true, None, 0);
        }

        let summary = collector.get_performance_summary().unwrap();
        assert_eq!(summary.total_executions, 7);
        assert_eq!(summary.success_rate, 1.0);
        assert_eq!(summary.slowest_hook, Some("slow_hook".to_string()));
        assert_eq!(summary.most_reliable_hook, Some("reliable_hook".to_string()));
    }
}
