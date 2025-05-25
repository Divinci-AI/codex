//! Hook error reporting and alerting system.

use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, RwLock};
use std::time::{Duration, SystemTime};

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use tokio::sync::mpsc;

use crate::hooks::types::{HookError, LifecycleEventType};

/// Comprehensive error reporting and alerting system.
#[derive(Debug)]
pub struct AlertingSystem {
    /// Configuration for alerting.
    config: AlertingConfig,
    /// Alert rules and conditions.
    alert_rules: Arc<RwLock<Vec<AlertRule>>>,
    /// Active alerts.
    active_alerts: Arc<RwLock<HashMap<String, ActiveAlert>>>,
    /// Alert history.
    alert_history: Arc<RwLock<VecDeque<AlertRecord>>>,
    /// Notification channels.
    notification_channels: Vec<Box<dyn NotificationChannel>>,
    /// Alert sender for async processing.
    alert_sender: mpsc::UnboundedSender<AlertEvent>,
}

/// Configuration for the alerting system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertingConfig {
    /// Whether alerting is enabled.
    pub enabled: bool,
    /// Default alert severity threshold.
    pub default_severity_threshold: AlertSeverity,
    /// Maximum number of alerts to keep in history.
    pub max_alert_history: usize,
    /// Alert aggregation window.
    pub aggregation_window: Duration,
    /// Whether to enable alert suppression.
    pub enable_suppression: bool,
    /// Alert suppression duration.
    pub suppression_duration: Duration,
    /// Whether to enable escalation.
    pub enable_escalation: bool,
    /// Escalation timeout.
    pub escalation_timeout: Duration,
}

impl Default for AlertingConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            default_severity_threshold: AlertSeverity::Warning,
            max_alert_history: 10000,
            aggregation_window: Duration::from_minutes(5),
            enable_suppression: true,
            suppression_duration: Duration::from_minutes(30),
            enable_escalation: true,
            escalation_timeout: Duration::from_hours(1),
        }
    }
}

/// Alert rule definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRule {
    /// Unique rule ID.
    pub id: String,
    /// Rule name.
    pub name: String,
    /// Rule description.
    pub description: String,
    /// Whether the rule is enabled.
    pub enabled: bool,
    /// Alert condition.
    pub condition: AlertCondition,
    /// Alert severity.
    pub severity: AlertSeverity,
    /// Notification channels for this rule.
    pub notification_channels: Vec<String>,
    /// Alert suppression settings.
    pub suppression: Option<SuppressionSettings>,
    /// Alert escalation settings.
    pub escalation: Option<EscalationSettings>,
    /// Rule tags for categorization.
    pub tags: Vec<String>,
}

/// Alert condition definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertCondition {
    /// Condition type.
    pub condition_type: AlertConditionType,
    /// Threshold value.
    pub threshold: f64,
    /// Time window for evaluation.
    pub time_window: Duration,
    /// Minimum occurrences to trigger alert.
    pub min_occurrences: u32,
    /// Hook ID filter (optional).
    pub hook_id_filter: Option<String>,
    /// Event type filter (optional).
    pub event_type_filter: Option<LifecycleEventType>,
}

/// Types of alert conditions.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AlertConditionType {
    /// Error rate exceeds threshold.
    ErrorRate,
    /// Execution time exceeds threshold.
    ExecutionTime,
    /// Failure count exceeds threshold.
    FailureCount,
    /// Throughput drops below threshold.
    LowThroughput,
    /// Resource usage exceeds threshold.
    ResourceUsage,
    /// Queue depth exceeds threshold.
    QueueDepth,
    /// Custom condition.
    Custom(String),
}

/// Alert severity levels.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum AlertSeverity {
    /// Informational alert.
    Info,
    /// Warning alert.
    Warning,
    /// Error alert.
    Error,
    /// Critical alert.
    Critical,
}

/// Alert suppression settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuppressionSettings {
    /// Suppression duration.
    pub duration: Duration,
    /// Maximum alerts per suppression window.
    pub max_alerts_per_window: u32,
    /// Whether to suppress similar alerts.
    pub suppress_similar: bool,
}

/// Alert escalation settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscalationSettings {
    /// Escalation levels.
    pub levels: Vec<EscalationLevel>,
    /// Whether to auto-escalate.
    pub auto_escalate: bool,
}

/// Escalation level definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscalationLevel {
    /// Level number.
    pub level: u32,
    /// Escalation timeout.
    pub timeout: Duration,
    /// Notification channels for this level.
    pub notification_channels: Vec<String>,
    /// Escalation severity.
    pub severity: AlertSeverity,
}

/// Active alert information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveAlert {
    /// Alert ID.
    pub id: String,
    /// Rule that triggered the alert.
    pub rule_id: String,
    /// Alert severity.
    pub severity: AlertSeverity,
    /// Alert message.
    pub message: String,
    /// When the alert was first triggered.
    pub triggered_at: DateTime<Utc>,
    /// When the alert was last updated.
    pub last_updated: DateTime<Utc>,
    /// Number of occurrences.
    pub occurrence_count: u32,
    /// Alert status.
    pub status: AlertStatus,
    /// Associated hook ID (if applicable).
    pub hook_id: Option<String>,
    /// Associated event type (if applicable).
    pub event_type: Option<LifecycleEventType>,
    /// Alert metadata.
    pub metadata: HashMap<String, serde_json::Value>,
    /// Current escalation level.
    pub escalation_level: u32,
}

/// Alert status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AlertStatus {
    /// Alert is active.
    Active,
    /// Alert is acknowledged.
    Acknowledged,
    /// Alert is resolved.
    Resolved,
    /// Alert is suppressed.
    Suppressed,
    /// Alert is escalated.
    Escalated,
}

/// Alert record for history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRecord {
    /// Alert ID.
    pub id: String,
    /// Rule ID.
    pub rule_id: String,
    /// Alert severity.
    pub severity: AlertSeverity,
    /// Alert message.
    pub message: String,
    /// When triggered.
    pub triggered_at: DateTime<Utc>,
    /// When resolved (if applicable).
    pub resolved_at: Option<DateTime<Utc>>,
    /// Duration the alert was active.
    pub duration: Option<Duration>,
    /// Final status.
    pub final_status: AlertStatus,
    /// Total occurrences.
    pub total_occurrences: u32,
    /// Associated hook ID.
    pub hook_id: Option<String>,
    /// Associated event type.
    pub event_type: Option<LifecycleEventType>,
}

/// Alert event for processing.
#[derive(Debug, Clone)]
pub struct AlertEvent {
    /// Event type.
    pub event_type: AlertEventType,
    /// Event data.
    pub data: AlertEventData,
    /// Event timestamp.
    pub timestamp: DateTime<Utc>,
}

/// Types of alert events.
#[derive(Debug, Clone, PartialEq)]
pub enum AlertEventType {
    /// Hook execution failed.
    HookExecutionFailed,
    /// Hook execution slow.
    HookExecutionSlow,
    /// Error rate threshold exceeded.
    ErrorRateExceeded,
    /// Resource usage high.
    ResourceUsageHigh,
    /// System health degraded.
    SystemHealthDegraded,
    /// Custom alert event.
    Custom(String),
}

/// Alert event data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertEventData {
    /// Hook ID (if applicable).
    pub hook_id: Option<String>,
    /// Event type (if applicable).
    pub event_type: Option<LifecycleEventType>,
    /// Metric value.
    pub value: f64,
    /// Error message (if applicable).
    pub error_message: Option<String>,
    /// Additional context.
    pub context: HashMap<String, serde_json::Value>,
}

/// Notification channel trait.
pub trait NotificationChannel: Send + Sync + std::fmt::Debug {
    /// Send a notification.
    fn send_notification(&self, alert: &ActiveAlert) -> Result<(), HookError>;
    
    /// Get channel name.
    fn channel_name(&self) -> &str;
    
    /// Check if channel is enabled.
    fn is_enabled(&self) -> bool;
}

/// Email notification channel.
#[derive(Debug)]
pub struct EmailNotificationChannel {
    /// Channel name.
    pub name: String,
    /// SMTP configuration.
    pub smtp_config: SmtpConfig,
    /// Recipients.
    pub recipients: Vec<String>,
    /// Whether enabled.
    pub enabled: bool,
}

/// SMTP configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmtpConfig {
    /// SMTP server host.
    pub host: String,
    /// SMTP server port.
    pub port: u16,
    /// Username.
    pub username: String,
    /// Password.
    pub password: String,
    /// Whether to use TLS.
    pub use_tls: bool,
}

/// Slack notification channel.
#[derive(Debug)]
pub struct SlackNotificationChannel {
    /// Channel name.
    pub name: String,
    /// Webhook URL.
    pub webhook_url: String,
    /// Default channel.
    pub default_channel: String,
    /// Whether enabled.
    pub enabled: bool,
}

/// Webhook notification channel.
#[derive(Debug)]
pub struct WebhookNotificationChannel {
    /// Channel name.
    pub name: String,
    /// Webhook URL.
    pub url: String,
    /// HTTP headers.
    pub headers: HashMap<String, String>,
    /// Whether enabled.
    pub enabled: bool,
}

impl AlertingSystem {
    /// Create a new alerting system.
    pub fn new(config: AlertingConfig) -> Self {
        let (alert_sender, mut alert_receiver) = mpsc::unbounded_channel();
        
        let system = Self {
            config,
            alert_rules: Arc::new(RwLock::new(Vec::new())),
            active_alerts: Arc::new(RwLock::new(HashMap::new())),
            alert_history: Arc::new(RwLock::new(VecDeque::new())),
            notification_channels: Vec::new(),
            alert_sender,
        };

        // Start alert processing task
        let active_alerts = system.active_alerts.clone();
        let alert_history = system.alert_history.clone();
        let config = system.config.clone();
        
        tokio::spawn(async move {
            while let Some(event) = alert_receiver.recv().await {
                if let Err(e) = Self::process_alert_event(event, &active_alerts, &alert_history, &config).await {
                    tracing::error!("Failed to process alert event: {}", e);
                }
            }
        });

        system
    }

    /// Add an alert rule.
    pub fn add_alert_rule(&self, rule: AlertRule) -> Result<(), HookError> {
        if let Ok(mut rules) = self.alert_rules.write() {
            rules.push(rule);
        }
        Ok(())
    }

    /// Remove an alert rule.
    pub fn remove_alert_rule(&self, rule_id: &str) -> Result<(), HookError> {
        if let Ok(mut rules) = self.alert_rules.write() {
            rules.retain(|rule| rule.id != rule_id);
        }
        Ok(())
    }

    /// Add a notification channel.
    pub fn add_notification_channel(&mut self, channel: Box<dyn NotificationChannel>) {
        self.notification_channels.push(channel);
    }

    /// Trigger an alert event.
    pub fn trigger_alert_event(&self, event: AlertEvent) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        self.alert_sender.send(event)
            .map_err(|e| HookError::Execution(format!("Failed to send alert event: {}", e)))?;

        Ok(())
    }

    /// Process an alert event.
    async fn process_alert_event(
        event: AlertEvent,
        active_alerts: &Arc<RwLock<HashMap<String, ActiveAlert>>>,
        alert_history: &Arc<RwLock<VecDeque<AlertRecord>>>,
        config: &AlertingConfig,
    ) -> Result<(), HookError> {
        // This is a simplified implementation
        // In a real system, you would evaluate alert rules and trigger notifications
        
        tracing::info!("Processing alert event: {:?}", event.event_type);
        
        // Create a sample alert for demonstration
        let alert_id = uuid::Uuid::new_v4().to_string();
        let alert = ActiveAlert {
            id: alert_id.clone(),
            rule_id: "default_rule".to_string(),
            severity: AlertSeverity::Warning,
            message: format!("Alert triggered by {:?}", event.event_type),
            triggered_at: event.timestamp,
            last_updated: event.timestamp,
            occurrence_count: 1,
            status: AlertStatus::Active,
            hook_id: event.data.hook_id,
            event_type: event.data.event_type,
            metadata: HashMap::new(),
            escalation_level: 0,
        };

        // Add to active alerts
        if let Ok(mut alerts) = active_alerts.write() {
            alerts.insert(alert_id, alert);
        }

        Ok(())
    }

    /// Get active alerts.
    pub fn get_active_alerts(&self) -> Result<Vec<ActiveAlert>, HookError> {
        self.active_alerts.read()
            .map(|alerts| alerts.values().cloned().collect())
            .map_err(|e| HookError::Execution(format!("Failed to read active alerts: {}", e)))
    }

    /// Get alert history.
    pub fn get_alert_history(&self, limit: Option<usize>) -> Result<Vec<AlertRecord>, HookError> {
        self.alert_history.read()
            .map(|history| {
                let limit = limit.unwrap_or(100);
                history.iter().rev().take(limit).cloned().collect()
            })
            .map_err(|e| HookError::Execution(format!("Failed to read alert history: {}", e)))
    }

    /// Acknowledge an alert.
    pub fn acknowledge_alert(&self, alert_id: &str, acknowledged_by: &str) -> Result<(), HookError> {
        if let Ok(mut alerts) = self.active_alerts.write() {
            if let Some(alert) = alerts.get_mut(alert_id) {
                alert.status = AlertStatus::Acknowledged;
                alert.last_updated = Utc::now();
                alert.metadata.insert(
                    "acknowledged_by".to_string(),
                    serde_json::Value::String(acknowledged_by.to_string()),
                );
            }
        }
        Ok(())
    }

    /// Resolve an alert.
    pub fn resolve_alert(&self, alert_id: &str, resolved_by: &str) -> Result<(), HookError> {
        if let Ok(mut alerts) = self.active_alerts.write() {
            if let Some(alert) = alerts.remove(alert_id) {
                // Move to history
                let record = AlertRecord {
                    id: alert.id,
                    rule_id: alert.rule_id,
                    severity: alert.severity,
                    message: alert.message,
                    triggered_at: alert.triggered_at,
                    resolved_at: Some(Utc::now()),
                    duration: Some(Utc::now().signed_duration_since(alert.triggered_at).to_std().unwrap_or(Duration::ZERO)),
                    final_status: AlertStatus::Resolved,
                    total_occurrences: alert.occurrence_count,
                    hook_id: alert.hook_id,
                    event_type: alert.event_type,
                };

                if let Ok(mut history) = self.alert_history.write() {
                    history.push_back(record);
                    
                    // Maintain size limit
                    if history.len() > self.config.max_alert_history {
                        history.pop_front();
                    }
                }
            }
        }
        Ok(())
    }

    /// Get alert statistics.
    pub fn get_alert_statistics(&self) -> Result<AlertStatistics, HookError> {
        let active_alerts = self.get_active_alerts()?;
        let alert_history = self.get_alert_history(None)?;

        let total_alerts = active_alerts.len() + alert_history.len();
        let critical_alerts = active_alerts.iter()
            .filter(|a| a.severity == AlertSeverity::Critical)
            .count();
        
        let avg_resolution_time = if !alert_history.is_empty() {
            let total_duration: Duration = alert_history.iter()
                .filter_map(|r| r.duration)
                .sum();
            total_duration / alert_history.len() as u32
        } else {
            Duration::ZERO
        };

        Ok(AlertStatistics {
            total_alerts,
            active_alerts: active_alerts.len(),
            critical_alerts,
            resolved_alerts: alert_history.len(),
            average_resolution_time: avg_resolution_time,
            alert_rate_per_hour: 0.0, // TODO: Calculate based on time window
        })
    }

    /// Export alert data to JSON.
    pub fn export_alert_data(&self) -> Result<String, HookError> {
        let active_alerts = self.get_active_alerts()?;
        let alert_history = self.get_alert_history(Some(1000))?;
        
        let export_data = serde_json::json!({
            "active_alerts": active_alerts,
            "alert_history": alert_history,
            "statistics": self.get_alert_statistics()?,
            "exported_at": Utc::now()
        });

        serde_json::to_string_pretty(&export_data)
            .map_err(|e| HookError::Execution(format!("Failed to serialize alert data: {}", e)))
    }
}

/// Alert statistics summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertStatistics {
    /// Total number of alerts.
    pub total_alerts: usize,
    /// Number of active alerts.
    pub active_alerts: usize,
    /// Number of critical alerts.
    pub critical_alerts: usize,
    /// Number of resolved alerts.
    pub resolved_alerts: usize,
    /// Average time to resolve alerts.
    pub average_resolution_time: Duration,
    /// Alert rate per hour.
    pub alert_rate_per_hour: f64,
}

// Notification channel implementations
impl NotificationChannel for EmailNotificationChannel {
    fn send_notification(&self, alert: &ActiveAlert) -> Result<(), HookError> {
        if !self.enabled {
            return Ok(());
        }

        tracing::info!("Sending email notification for alert: {}", alert.id);
        // TODO: Implement actual email sending
        Ok(())
    }

    fn channel_name(&self) -> &str {
        &self.name
    }

    fn is_enabled(&self) -> bool {
        self.enabled
    }
}

impl NotificationChannel for SlackNotificationChannel {
    fn send_notification(&self, alert: &ActiveAlert) -> Result<(), HookError> {
        if !self.enabled {
            return Ok(());
        }

        tracing::info!("Sending Slack notification for alert: {}", alert.id);
        // TODO: Implement actual Slack webhook sending
        Ok(())
    }

    fn channel_name(&self) -> &str {
        &self.name
    }

    fn is_enabled(&self) -> bool {
        self.enabled
    }
}

impl NotificationChannel for WebhookNotificationChannel {
    fn send_notification(&self, alert: &ActiveAlert) -> Result<(), HookError> {
        if !self.enabled {
            return Ok(());
        }

        tracing::info!("Sending webhook notification for alert: {}", alert.id);
        // TODO: Implement actual webhook HTTP request
        Ok(())
    }

    fn channel_name(&self) -> &str {
        &self.name
    }

    fn is_enabled(&self) -> bool {
        self.enabled
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_alerting_system_creation() {
        let system = AlertingSystem::new(AlertingConfig::default());
        assert!(system.config.enabled);
    }

    #[tokio::test]
    async fn test_alert_rule_management() {
        let system = AlertingSystem::new(AlertingConfig::default());
        
        let rule = AlertRule {
            id: "test_rule".to_string(),
            name: "Test Rule".to_string(),
            description: "A test alert rule".to_string(),
            enabled: true,
            condition: AlertCondition {
                condition_type: AlertConditionType::ErrorRate,
                threshold: 0.1,
                time_window: Duration::from_minutes(5),
                min_occurrences: 3,
                hook_id_filter: None,
                event_type_filter: None,
            },
            severity: AlertSeverity::Warning,
            notification_channels: vec!["email".to_string()],
            suppression: None,
            escalation: None,
            tags: vec!["test".to_string()],
        };

        system.add_alert_rule(rule).unwrap();
        system.remove_alert_rule("test_rule").unwrap();
    }

    #[tokio::test]
    async fn test_alert_event_triggering() {
        let system = AlertingSystem::new(AlertingConfig::default());
        
        let event = AlertEvent {
            event_type: AlertEventType::HookExecutionFailed,
            data: AlertEventData {
                hook_id: Some("test_hook".to_string()),
                event_type: Some(LifecycleEventType::SessionStart),
                value: 1.0,
                error_message: Some("Test error".to_string()),
                context: HashMap::new(),
            },
            timestamp: Utc::now(),
        };

        system.trigger_alert_event(event).unwrap();
        
        // Give some time for async processing
        tokio::time::sleep(Duration::from_millis(100)).await;
        
        let active_alerts = system.get_active_alerts().unwrap();
        assert!(!active_alerts.is_empty());
    }

    #[test]
    fn test_alert_severity_ordering() {
        assert!(AlertSeverity::Critical > AlertSeverity::Error);
        assert!(AlertSeverity::Error > AlertSeverity::Warning);
        assert!(AlertSeverity::Warning > AlertSeverity::Info);
    }

    #[test]
    fn test_alert_condition_serialization() {
        let condition = AlertCondition {
            condition_type: AlertConditionType::ErrorRate,
            threshold: 0.1,
            time_window: Duration::from_minutes(5),
            min_occurrences: 3,
            hook_id_filter: None,
            event_type_filter: None,
        };

        let serialized = serde_json::to_string(&condition).unwrap();
        let deserialized: AlertCondition = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.condition_type, AlertConditionType::ErrorRate);
    }
}
