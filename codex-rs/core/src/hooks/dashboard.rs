//! Hook execution dashboard and monitoring system.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, SystemTime};

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use crate::hooks::metrics::{HookMetrics, MetricsCollector, PerformanceSummary};
use crate::hooks::history::{HistoryManager, HistorySummary, ExecutionHistoryRecord};
use crate::hooks::types::{HookError, LifecycleEventType};

/// Real-time dashboard for hook execution monitoring.
#[derive(Debug)]
pub struct HookDashboard {
    /// Metrics collector for performance data.
    metrics_collector: Arc<MetricsCollector>,
    /// History manager for execution records.
    history_manager: Arc<HistoryManager>,
    /// Dashboard configuration.
    config: DashboardConfig,
    /// Real-time status tracking.
    status_tracker: Arc<RwLock<StatusTracker>>,
}

/// Configuration for the hook dashboard.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardConfig {
    /// Whether the dashboard is enabled.
    pub enabled: bool,
    /// Update interval for real-time data.
    pub update_interval: Duration,
    /// Maximum number of recent events to display.
    pub max_recent_events: usize,
    /// Whether to enable real-time notifications.
    pub enable_notifications: bool,
    /// Threshold for slow execution warnings (in seconds).
    pub slow_execution_threshold: Duration,
    /// Threshold for error rate alerts (percentage).
    pub error_rate_threshold: f64,
}

impl Default for DashboardConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            update_interval: Duration::from_secs(5),
            max_recent_events: 100,
            enable_notifications: true,
            slow_execution_threshold: Duration::from_secs(10),
            error_rate_threshold: 0.1, // 10%
        }
    }
}

/// Real-time status tracking for the dashboard.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusTracker {
    /// Currently executing hooks.
    pub active_executions: HashMap<String, ActiveExecution>,
    /// Recent events for real-time display.
    pub recent_events: Vec<DashboardEvent>,
    /// Current system status.
    pub system_status: SystemStatus,
    /// Last update timestamp.
    pub last_updated: DateTime<Utc>,
}

/// Information about an actively executing hook.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveExecution {
    /// Unique execution ID.
    pub execution_id: String,
    /// Hook ID being executed.
    pub hook_id: String,
    /// Event type that triggered the hook.
    pub event_type: LifecycleEventType,
    /// When the execution started.
    pub started_at: DateTime<Utc>,
    /// Expected duration (if available).
    pub estimated_duration: Option<Duration>,
    /// Current status.
    pub status: ExecutionStatus,
}

/// Status of a hook execution.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ExecutionStatus {
    /// Execution is starting.
    Starting,
    /// Execution is in progress.
    Running,
    /// Execution is completing.
    Completing,
    /// Execution completed successfully.
    Completed,
    /// Execution failed.
    Failed,
    /// Execution was cancelled.
    Cancelled,
    /// Execution timed out.
    TimedOut,
}

/// Real-time dashboard event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardEvent {
    /// Event ID.
    pub id: String,
    /// Event type.
    pub event_type: DashboardEventType,
    /// Event timestamp.
    pub timestamp: DateTime<Utc>,
    /// Event message.
    pub message: String,
    /// Event severity.
    pub severity: EventSeverity,
    /// Associated hook ID (if applicable).
    pub hook_id: Option<String>,
    /// Additional metadata.
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Types of dashboard events.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DashboardEventType {
    /// Hook execution started.
    ExecutionStarted,
    /// Hook execution completed.
    ExecutionCompleted,
    /// Hook execution failed.
    ExecutionFailed,
    /// Hook execution timed out.
    ExecutionTimedOut,
    /// Performance threshold exceeded.
    PerformanceAlert,
    /// Error rate threshold exceeded.
    ErrorRateAlert,
    /// System status change.
    SystemStatusChange,
    /// Configuration change.
    ConfigurationChange,
}

/// Event severity levels.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum EventSeverity {
    /// Informational event.
    Info,
    /// Warning event.
    Warning,
    /// Error event.
    Error,
    /// Critical event.
    Critical,
}

/// Overall system status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SystemStatus {
    /// System is healthy.
    Healthy,
    /// System has warnings.
    Warning,
    /// System has errors.
    Error,
    /// System is in critical state.
    Critical,
    /// System is offline.
    Offline,
}

/// Comprehensive dashboard data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardData {
    /// Current system status.
    pub system_status: SystemStatus,
    /// Performance summary.
    pub performance_summary: PerformanceSummary,
    /// History summary.
    pub history_summary: HistorySummary,
    /// Currently active executions.
    pub active_executions: Vec<ActiveExecution>,
    /// Recent events.
    pub recent_events: Vec<DashboardEvent>,
    /// Hook statistics by type.
    pub hook_statistics: HashMap<String, HookStatistics>,
    /// Event type statistics.
    pub event_statistics: HashMap<LifecycleEventType, EventStatistics>,
    /// System health indicators.
    pub health_indicators: HealthIndicators,
    /// Last update timestamp.
    pub last_updated: DateTime<Utc>,
}

/// Statistics for a specific hook.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookStatistics {
    /// Hook ID.
    pub hook_id: String,
    /// Total executions.
    pub total_executions: u64,
    /// Success rate.
    pub success_rate: f64,
    /// Average execution time.
    pub average_duration: Duration,
    /// Last execution time.
    pub last_execution: Option<DateTime<Utc>>,
    /// Current status.
    pub status: HookStatus,
}

/// Status of a specific hook.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum HookStatus {
    /// Hook is active and healthy.
    Active,
    /// Hook has warnings.
    Warning,
    /// Hook has errors.
    Error,
    /// Hook is disabled.
    Disabled,
}

/// Statistics for a specific event type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventStatistics {
    /// Event type.
    pub event_type: LifecycleEventType,
    /// Total hooks triggered.
    pub total_hooks_triggered: u64,
    /// Average hooks per event.
    pub average_hooks_per_event: f64,
    /// Average total execution time.
    pub average_total_duration: Duration,
    /// Success rate across all hooks.
    pub overall_success_rate: f64,
}

/// System health indicators.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthIndicators {
    /// Overall system health score (0.0 to 1.0).
    pub health_score: f64,
    /// CPU usage percentage.
    pub cpu_usage: Option<f64>,
    /// Memory usage percentage.
    pub memory_usage: Option<f64>,
    /// Disk usage percentage.
    pub disk_usage: Option<f64>,
    /// Number of active connections.
    pub active_connections: u32,
    /// Uptime in seconds.
    pub uptime: Duration,
}

impl HookDashboard {
    /// Create a new hook dashboard.
    pub fn new(
        metrics_collector: Arc<MetricsCollector>,
        history_manager: Arc<HistoryManager>,
        config: DashboardConfig,
    ) -> Self {
        Self {
            metrics_collector,
            history_manager,
            config,
            status_tracker: Arc::new(RwLock::new(StatusTracker {
                active_executions: HashMap::new(),
                recent_events: Vec::new(),
                system_status: SystemStatus::Healthy,
                last_updated: Utc::now(),
            })),
        }
    }

    /// Create a dashboard with default configuration.
    pub fn with_defaults(
        metrics_collector: Arc<MetricsCollector>,
        history_manager: Arc<HistoryManager>,
    ) -> Self {
        Self::new(metrics_collector, history_manager, DashboardConfig::default())
    }

    /// Start tracking a hook execution.
    pub fn start_execution_tracking(
        &self,
        execution_id: String,
        hook_id: String,
        event_type: LifecycleEventType,
        estimated_duration: Option<Duration>,
    ) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        let active_execution = ActiveExecution {
            execution_id: execution_id.clone(),
            hook_id: hook_id.clone(),
            event_type,
            started_at: Utc::now(),
            estimated_duration,
            status: ExecutionStatus::Starting,
        };

        // Add to active executions
        if let Ok(mut tracker) = self.status_tracker.write() {
            tracker.active_executions.insert(execution_id.clone(), active_execution);
            tracker.last_updated = Utc::now();
        }

        // Create dashboard event
        self.add_dashboard_event(DashboardEvent {
            id: uuid::Uuid::new_v4().to_string(),
            event_type: DashboardEventType::ExecutionStarted,
            timestamp: Utc::now(),
            message: format!("Hook '{}' execution started", hook_id),
            severity: EventSeverity::Info,
            hook_id: Some(hook_id),
            metadata: HashMap::new(),
        })?;

        Ok(())
    }

    /// Update execution status.
    pub fn update_execution_status(
        &self,
        execution_id: &str,
        status: ExecutionStatus,
    ) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        if let Ok(mut tracker) = self.status_tracker.write() {
            if let Some(execution) = tracker.active_executions.get_mut(execution_id) {
                execution.status = status;
                tracker.last_updated = Utc::now();
            }
        }

        Ok(())
    }

    /// Complete execution tracking.
    pub fn complete_execution_tracking(
        &self,
        execution_id: &str,
        success: bool,
        duration: Duration,
        error_message: Option<String>,
    ) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        let (hook_id, event_type) = if let Ok(mut tracker) = self.status_tracker.write() {
            if let Some(execution) = tracker.active_executions.remove(execution_id) {
                tracker.last_updated = Utc::now();
                (execution.hook_id, Some(execution.event_type))
            } else {
                return Ok(()); // Execution not found
            }
        } else {
            return Ok(());
        };

        // Create completion event
        let (event_type_dashboard, severity, message) = if success {
            (
                DashboardEventType::ExecutionCompleted,
                EventSeverity::Info,
                format!("Hook '{}' completed successfully in {:?}", hook_id, duration),
            )
        } else if let Some(error) = error_message {
            (
                DashboardEventType::ExecutionFailed,
                EventSeverity::Error,
                format!("Hook '{}' failed: {}", hook_id, error),
            )
        } else {
            (
                DashboardEventType::ExecutionFailed,
                EventSeverity::Error,
                format!("Hook '{}' failed after {:?}", hook_id, duration),
            )
        };

        self.add_dashboard_event(DashboardEvent {
            id: uuid::Uuid::new_v4().to_string(),
            event_type: event_type_dashboard,
            timestamp: Utc::now(),
            message,
            severity,
            hook_id: Some(hook_id),
            metadata: {
                let mut metadata = HashMap::new();
                metadata.insert("duration_ms".to_string(), serde_json::Value::Number(
                    serde_json::Number::from(duration.as_millis() as u64)
                ));
                metadata.insert("success".to_string(), serde_json::Value::Bool(success));
                if let Some(event_type) = event_type {
                    metadata.insert("event_type".to_string(), serde_json::Value::String(
                        format!("{:?}", event_type)
                    ));
                }
                metadata
            },
        })?;

        // Check for performance alerts
        if duration > self.config.slow_execution_threshold {
            self.add_dashboard_event(DashboardEvent {
                id: uuid::Uuid::new_v4().to_string(),
                event_type: DashboardEventType::PerformanceAlert,
                timestamp: Utc::now(),
                message: format!(
                    "Hook '{}' execution exceeded slow threshold ({:?} > {:?})",
                    hook_id, duration, self.config.slow_execution_threshold
                ),
                severity: EventSeverity::Warning,
                hook_id: Some(hook_id),
                metadata: HashMap::new(),
            })?;
        }

        Ok(())
    }

    /// Add a dashboard event.
    fn add_dashboard_event(&self, event: DashboardEvent) -> Result<(), HookError> {
        if let Ok(mut tracker) = self.status_tracker.write() {
            tracker.recent_events.push(event);

            // Maintain size limit
            if tracker.recent_events.len() > self.config.max_recent_events {
                tracker.recent_events.remove(0);
            }

            tracker.last_updated = Utc::now();
        }

        Ok(())
    }

    /// Get current dashboard data.
    pub async fn get_dashboard_data(&self) -> Result<DashboardData, HookError> {
        // Get performance summary
        let performance_summary = self.metrics_collector.get_performance_summary()?;

        // Get history summary
        let history_summary = self.history_manager.get_summary()?;

        // Get current status
        let (active_executions, recent_events, system_status) = if let Ok(tracker) = self.status_tracker.read() {
            (
                tracker.active_executions.values().cloned().collect(),
                tracker.recent_events.clone(),
                tracker.system_status.clone(),
            )
        } else {
            (Vec::new(), Vec::new(), SystemStatus::Error)
        };

        // Calculate hook statistics
        let hook_statistics = self.calculate_hook_statistics().await?;

        // Calculate event statistics
        let event_statistics = self.calculate_event_statistics().await?;

        // Get health indicators
        let health_indicators = self.get_health_indicators().await?;

        Ok(DashboardData {
            system_status,
            performance_summary,
            history_summary,
            active_executions,
            recent_events,
            hook_statistics,
            event_statistics,
            health_indicators,
            last_updated: Utc::now(),
        })
    }

    /// Calculate statistics for each hook.
    async fn calculate_hook_statistics(&self) -> Result<HashMap<String, HookStatistics>, HookError> {
        let metrics = self.metrics_collector.get_metrics()?;
        let mut statistics = HashMap::new();

        for (hook_id, hook_metrics) in metrics.by_hook_id {
            let status = if hook_metrics.success_rate < 0.5 {
                HookStatus::Error
            } else if hook_metrics.success_rate < 0.9 {
                HookStatus::Warning
            } else {
                HookStatus::Active
            };

            statistics.insert(hook_id.clone(), HookStatistics {
                hook_id,
                total_executions: hook_metrics.total_executions,
                success_rate: hook_metrics.success_rate,
                average_duration: hook_metrics.average_execution_time,
                last_execution: hook_metrics.last_execution.map(|st| {
                    DateTime::from(st)
                }),
                status,
            });
        }

        Ok(statistics)
    }

    /// Calculate statistics for each event type.
    async fn calculate_event_statistics(&self) -> Result<HashMap<LifecycleEventType, EventStatistics>, HookError> {
        let metrics = self.metrics_collector.get_metrics()?;
        let mut statistics = HashMap::new();

        for (event_type, event_metrics) in metrics.by_event_type {
            statistics.insert(event_type, EventStatistics {
                event_type,
                total_hooks_triggered: event_metrics.total_executions,
                average_hooks_per_event: 1.0, // TODO: Calculate based on actual data
                average_total_duration: event_metrics.average_execution_time,
                overall_success_rate: event_metrics.success_rate,
            });
        }

        Ok(statistics)
    }

    /// Get system health indicators.
    async fn get_health_indicators(&self) -> Result<HealthIndicators, HookError> {
        let metrics = self.metrics_collector.get_metrics()?;
        
        // Calculate health score based on success rate and performance
        let health_score = if metrics.total_executions == 0 {
            1.0 // No executions yet, assume healthy
        } else {
            let success_factor = metrics.success_rate;
            let performance_factor = if metrics.average_execution_time > Duration::from_secs(5) {
                0.8 // Penalize slow performance
            } else {
                1.0
            };
            success_factor * performance_factor
        };

        // Get system metrics (simplified for now)
        let active_connections = if let Ok(tracker) = self.status_tracker.read() {
            tracker.active_executions.len() as u32
        } else {
            0
        };

        Ok(HealthIndicators {
            health_score,
            cpu_usage: None, // TODO: Implement actual system monitoring
            memory_usage: None,
            disk_usage: None,
            active_connections,
            uptime: Duration::from_secs(0), // TODO: Track actual uptime
        })
    }

    /// Update system status based on current conditions.
    pub async fn update_system_status(&self) -> Result<(), HookError> {
        let health_indicators = self.get_health_indicators().await?;
        let metrics = self.metrics_collector.get_metrics()?;

        let new_status = if health_indicators.health_score >= 0.9 {
            SystemStatus::Healthy
        } else if health_indicators.health_score >= 0.7 {
            SystemStatus::Warning
        } else if health_indicators.health_score >= 0.5 {
            SystemStatus::Error
        } else {
            SystemStatus::Critical
        };

        // Check for error rate alerts
        if metrics.total_executions > 10 && (1.0 - metrics.success_rate) > self.config.error_rate_threshold {
            self.add_dashboard_event(DashboardEvent {
                id: uuid::Uuid::new_v4().to_string(),
                event_type: DashboardEventType::ErrorRateAlert,
                timestamp: Utc::now(),
                message: format!(
                    "Error rate ({:.1}%) exceeds threshold ({:.1}%)",
                    (1.0 - metrics.success_rate) * 100.0,
                    self.config.error_rate_threshold * 100.0
                ),
                severity: EventSeverity::Warning,
                hook_id: None,
                metadata: HashMap::new(),
            })?;
        }

        // Update status if changed
        if let Ok(mut tracker) = self.status_tracker.write() {
            if tracker.system_status != new_status {
                tracker.system_status = new_status.clone();
                tracker.last_updated = Utc::now();

                // Create status change event
                self.add_dashboard_event(DashboardEvent {
                    id: uuid::Uuid::new_v4().to_string(),
                    event_type: DashboardEventType::SystemStatusChange,
                    timestamp: Utc::now(),
                    message: format!("System status changed to {:?}", new_status),
                    severity: match new_status {
                        SystemStatus::Healthy => EventSeverity::Info,
                        SystemStatus::Warning => EventSeverity::Warning,
                        SystemStatus::Error => EventSeverity::Error,
                        SystemStatus::Critical | SystemStatus::Offline => EventSeverity::Critical,
                    },
                    hook_id: None,
                    metadata: HashMap::new(),
                })?;
            }
        }

        Ok(())
    }

    /// Get dashboard configuration.
    pub fn get_config(&self) -> &DashboardConfig {
        &self.config
    }

    /// Update dashboard configuration.
    pub fn update_config(&mut self, config: DashboardConfig) -> Result<(), HookError> {
        self.config = config;
        
        self.add_dashboard_event(DashboardEvent {
            id: uuid::Uuid::new_v4().to_string(),
            event_type: DashboardEventType::ConfigurationChange,
            timestamp: Utc::now(),
            message: "Dashboard configuration updated".to_string(),
            severity: EventSeverity::Info,
            hook_id: None,
            metadata: HashMap::new(),
        })?;

        Ok(())
    }

    /// Export dashboard data to JSON.
    pub async fn export_dashboard_data(&self) -> Result<String, HookError> {
        let data = self.get_dashboard_data().await?;
        serde_json::to_string_pretty(&data)
            .map_err(|e| HookError::Execution(format!("Failed to serialize dashboard data: {}", e)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::metrics::MetricsConfig;
    use crate::hooks::history::HistoryConfig;

    #[tokio::test]
    async fn test_dashboard_creation() {
        let metrics_collector = Arc::new(MetricsCollector::new(MetricsConfig::default()));
        let history_manager = Arc::new(HistoryManager::new(HistoryConfig::default()).unwrap());
        
        let dashboard = HookDashboard::with_defaults(metrics_collector, history_manager);
        assert!(dashboard.config.enabled);
    }

    #[tokio::test]
    async fn test_execution_tracking() {
        let metrics_collector = Arc::new(MetricsCollector::new(MetricsConfig::default()));
        let history_manager = Arc::new(HistoryManager::new(HistoryConfig::default()).unwrap());
        
        let dashboard = HookDashboard::with_defaults(metrics_collector, history_manager);
        
        // Start tracking
        dashboard.start_execution_tracking(
            "exec_1".to_string(),
            "hook_1".to_string(),
            LifecycleEventType::SessionStart,
            Some(Duration::from_secs(5)),
        ).unwrap();

        // Update status
        dashboard.update_execution_status("exec_1", ExecutionStatus::Running).unwrap();

        // Complete tracking
        dashboard.complete_execution_tracking(
            "exec_1",
            true,
            Duration::from_secs(3),
            None,
        ).unwrap();

        let data = dashboard.get_dashboard_data().await.unwrap();
        assert_eq!(data.active_executions.len(), 0); // Should be removed after completion
        assert!(!data.recent_events.is_empty()); // Should have events
    }

    #[tokio::test]
    async fn test_dashboard_data_generation() {
        let metrics_collector = Arc::new(MetricsCollector::new(MetricsConfig::default()));
        let history_manager = Arc::new(HistoryManager::new(HistoryConfig::default()).unwrap());
        
        let dashboard = HookDashboard::with_defaults(metrics_collector, history_manager);
        
        let data = dashboard.get_dashboard_data().await.unwrap();
        assert_eq!(data.system_status, SystemStatus::Healthy);
        assert!(data.health_indicators.health_score >= 0.0);
        assert!(data.health_indicators.health_score <= 1.0);
    }

    #[test]
    fn test_execution_status_serialization() {
        let status = ExecutionStatus::Running;
        let serialized = serde_json::to_string(&status).unwrap();
        let deserialized: ExecutionStatus = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized, ExecutionStatus::Running);
    }

    #[test]
    fn test_dashboard_event_creation() {
        let event = DashboardEvent {
            id: "test_event".to_string(),
            event_type: DashboardEventType::ExecutionStarted,
            timestamp: Utc::now(),
            message: "Test event".to_string(),
            severity: EventSeverity::Info,
            hook_id: Some("test_hook".to_string()),
            metadata: HashMap::new(),
        };

        assert_eq!(event.event_type, DashboardEventType::ExecutionStarted);
        assert_eq!(event.severity, EventSeverity::Info);
    }
}
