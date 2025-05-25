//! Advanced hook performance metrics collection and analysis.

use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant, SystemTime};

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

use crate::hooks::types::{HookError, LifecycleEventType};

/// Advanced performance metrics collector with detailed analytics.
#[derive(Debug)]
pub struct PerformanceCollector {
    /// Configuration for performance collection.
    config: PerformanceConfig,
    /// Real-time performance data.
    performance_data: Arc<RwLock<PerformanceData>>,
    /// Historical performance trends.
    historical_data: Arc<RwLock<HistoricalData>>,
}

/// Configuration for performance metrics collection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceConfig {
    /// Whether performance collection is enabled.
    pub enabled: bool,
    /// Sampling interval for metrics collection.
    pub sampling_interval: Duration,
    /// Maximum number of samples to keep in memory.
    pub max_samples: usize,
    /// Whether to collect detailed timing breakdowns.
    pub collect_detailed_timings: bool,
    /// Whether to collect resource usage metrics.
    pub collect_resource_metrics: bool,
    /// Whether to collect concurrency metrics.
    pub collect_concurrency_metrics: bool,
    /// Percentiles to calculate for performance analysis.
    pub percentiles: Vec<f64>,
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            sampling_interval: Duration::from_secs(1),
            max_samples: 10000,
            collect_detailed_timings: true,
            collect_resource_metrics: true,
            collect_concurrency_metrics: true,
            percentiles: vec![50.0, 75.0, 90.0, 95.0, 99.0, 99.9],
        }
    }
}

/// Real-time performance data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceData {
    /// Current performance metrics.
    pub current_metrics: CurrentMetrics,
    /// Recent performance samples.
    pub recent_samples: VecDeque<PerformanceSample>,
    /// Performance by hook ID.
    pub hook_performance: HashMap<String, HookPerformanceData>,
    /// Performance by event type.
    pub event_performance: HashMap<LifecycleEventType, EventPerformanceData>,
    /// System resource metrics.
    pub resource_metrics: ResourceMetrics,
    /// Concurrency metrics.
    pub concurrency_metrics: ConcurrencyMetrics,
    /// Last update timestamp.
    pub last_updated: DateTime<Utc>,
}

/// Current real-time performance metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CurrentMetrics {
    /// Current throughput (executions per second).
    pub throughput: f64,
    /// Current average response time.
    pub average_response_time: Duration,
    /// Current error rate (0.0 to 1.0).
    pub error_rate: f64,
    /// Current active executions.
    pub active_executions: u32,
    /// Current queue depth.
    pub queue_depth: u32,
}

/// Individual performance sample.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceSample {
    /// Sample timestamp.
    pub timestamp: DateTime<Utc>,
    /// Hook ID.
    pub hook_id: String,
    /// Event type.
    pub event_type: LifecycleEventType,
    /// Execution duration.
    pub duration: Duration,
    /// Whether execution was successful.
    pub success: bool,
    /// Detailed timing breakdown.
    pub timing_breakdown: Option<TimingBreakdown>,
    /// Resource usage during execution.
    pub resource_usage: Option<ResourceUsage>,
    /// Concurrency level at time of execution.
    pub concurrency_level: u32,
}

/// Detailed timing breakdown for hook execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingBreakdown {
    /// Time spent in pre-execution setup.
    pub setup_time: Duration,
    /// Time spent in actual execution.
    pub execution_time: Duration,
    /// Time spent in post-execution cleanup.
    pub cleanup_time: Duration,
    /// Time spent waiting for resources.
    pub wait_time: Duration,
    /// Time spent in serialization/deserialization.
    pub serialization_time: Duration,
}

/// Resource usage metrics during execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceUsage {
    /// CPU usage percentage.
    pub cpu_usage: f64,
    /// Memory usage in bytes.
    pub memory_usage: u64,
    /// Network I/O in bytes.
    pub network_io: u64,
    /// Disk I/O in bytes.
    pub disk_io: u64,
    /// Number of file descriptors used.
    pub file_descriptors: u32,
}

/// Performance data for a specific hook.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookPerformanceData {
    /// Hook ID.
    pub hook_id: String,
    /// Total executions.
    pub total_executions: u64,
    /// Successful executions.
    pub successful_executions: u64,
    /// Performance statistics.
    pub statistics: PerformanceStatistics,
    /// Recent performance trend.
    pub trend: PerformanceTrend,
    /// Performance percentiles.
    pub percentiles: HashMap<String, Duration>,
    /// Last execution timestamp.
    pub last_execution: Option<DateTime<Utc>>,
}

/// Performance data for a specific event type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventPerformanceData {
    /// Event type.
    pub event_type: LifecycleEventType,
    /// Total events processed.
    pub total_events: u64,
    /// Average hooks per event.
    pub average_hooks_per_event: f64,
    /// Performance statistics.
    pub statistics: PerformanceStatistics,
    /// Event processing trend.
    pub trend: PerformanceTrend,
}

/// Statistical performance metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceStatistics {
    /// Mean execution time.
    pub mean: Duration,
    /// Median execution time.
    pub median: Duration,
    /// Standard deviation.
    pub std_dev: Duration,
    /// Minimum execution time.
    pub min: Duration,
    /// Maximum execution time.
    pub max: Duration,
    /// Success rate.
    pub success_rate: f64,
    /// Throughput (executions per second).
    pub throughput: f64,
}

/// Performance trend analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceTrend {
    /// Trend direction.
    pub direction: TrendDirection,
    /// Trend strength (0.0 to 1.0).
    pub strength: f64,
    /// Recent change percentage.
    pub change_percentage: f64,
    /// Trend analysis period.
    pub analysis_period: Duration,
}

/// Direction of performance trend.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TrendDirection {
    /// Performance is improving.
    Improving,
    /// Performance is stable.
    Stable,
    /// Performance is degrading.
    Degrading,
    /// Insufficient data for trend analysis.
    Unknown,
}

/// System resource metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceMetrics {
    /// Overall CPU usage percentage.
    pub cpu_usage: f64,
    /// Overall memory usage percentage.
    pub memory_usage: f64,
    /// Available memory in bytes.
    pub available_memory: u64,
    /// Disk usage percentage.
    pub disk_usage: f64,
    /// Network throughput in bytes per second.
    pub network_throughput: u64,
    /// Number of open file descriptors.
    pub open_file_descriptors: u32,
    /// System load average.
    pub load_average: f64,
}

/// Concurrency and parallelism metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConcurrencyMetrics {
    /// Current concurrent executions.
    pub current_concurrent: u32,
    /// Maximum concurrent executions observed.
    pub max_concurrent: u32,
    /// Average concurrent executions.
    pub average_concurrent: f64,
    /// Thread pool utilization percentage.
    pub thread_pool_utilization: f64,
    /// Queue wait times.
    pub queue_wait_times: QueueMetrics,
}

/// Queue performance metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueueMetrics {
    /// Current queue depth.
    pub current_depth: u32,
    /// Maximum queue depth observed.
    pub max_depth: u32,
    /// Average queue depth.
    pub average_depth: f64,
    /// Average wait time in queue.
    pub average_wait_time: Duration,
    /// Queue throughput (items per second).
    pub throughput: f64,
}

/// Historical performance data for trend analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalData {
    /// Hourly aggregated metrics.
    pub hourly_metrics: VecDeque<AggregatedMetrics>,
    /// Daily aggregated metrics.
    pub daily_metrics: VecDeque<AggregatedMetrics>,
    /// Weekly aggregated metrics.
    pub weekly_metrics: VecDeque<AggregatedMetrics>,
    /// Performance baselines.
    pub baselines: PerformanceBaselines,
}

/// Aggregated metrics for a time period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedMetrics {
    /// Time period start.
    pub period_start: DateTime<Utc>,
    /// Time period end.
    pub period_end: DateTime<Utc>,
    /// Total executions in period.
    pub total_executions: u64,
    /// Successful executions in period.
    pub successful_executions: u64,
    /// Performance statistics for period.
    pub statistics: PerformanceStatistics,
    /// Resource usage summary.
    pub resource_summary: ResourceSummary,
}

/// Summary of resource usage over a period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceSummary {
    /// Average CPU usage.
    pub avg_cpu_usage: f64,
    /// Peak CPU usage.
    pub peak_cpu_usage: f64,
    /// Average memory usage.
    pub avg_memory_usage: f64,
    /// Peak memory usage.
    pub peak_memory_usage: f64,
    /// Total network I/O.
    pub total_network_io: u64,
    /// Total disk I/O.
    pub total_disk_io: u64,
}

/// Performance baselines for comparison.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceBaselines {
    /// Baseline response time.
    pub baseline_response_time: Duration,
    /// Baseline throughput.
    pub baseline_throughput: f64,
    /// Baseline error rate.
    pub baseline_error_rate: f64,
    /// Baseline resource usage.
    pub baseline_resource_usage: ResourceUsage,
    /// When baselines were established.
    pub established_at: DateTime<Utc>,
}

impl PerformanceCollector {
    /// Create a new performance collector.
    pub fn new(config: PerformanceConfig) -> Self {
        Self {
            config,
            performance_data: Arc::new(RwLock::new(PerformanceData {
                current_metrics: CurrentMetrics {
                    throughput: 0.0,
                    average_response_time: Duration::ZERO,
                    error_rate: 0.0,
                    active_executions: 0,
                    queue_depth: 0,
                },
                recent_samples: VecDeque::new(),
                hook_performance: HashMap::new(),
                event_performance: HashMap::new(),
                resource_metrics: ResourceMetrics {
                    cpu_usage: 0.0,
                    memory_usage: 0.0,
                    available_memory: 0,
                    disk_usage: 0.0,
                    network_throughput: 0,
                    open_file_descriptors: 0,
                    load_average: 0.0,
                },
                concurrency_metrics: ConcurrencyMetrics {
                    current_concurrent: 0,
                    max_concurrent: 0,
                    average_concurrent: 0.0,
                    thread_pool_utilization: 0.0,
                    queue_wait_times: QueueMetrics {
                        current_depth: 0,
                        max_depth: 0,
                        average_depth: 0.0,
                        average_wait_time: Duration::ZERO,
                        throughput: 0.0,
                    },
                },
                last_updated: Utc::now(),
            })),
            historical_data: Arc::new(RwLock::new(HistoricalData {
                hourly_metrics: VecDeque::new(),
                daily_metrics: VecDeque::new(),
                weekly_metrics: VecDeque::new(),
                baselines: PerformanceBaselines {
                    baseline_response_time: Duration::from_millis(100),
                    baseline_throughput: 10.0,
                    baseline_error_rate: 0.01,
                    baseline_resource_usage: ResourceUsage {
                        cpu_usage: 10.0,
                        memory_usage: 100 * 1024 * 1024, // 100MB
                        network_io: 0,
                        disk_io: 0,
                        file_descriptors: 10,
                    },
                    established_at: Utc::now(),
                },
            })),
        }
    }

    /// Create a performance collector with default configuration.
    pub fn default() -> Self {
        Self::new(PerformanceConfig::default())
    }

    /// Record a performance sample.
    pub fn record_sample(&self, sample: PerformanceSample) -> Result<(), HookError> {
        if !self.config.enabled {
            return Ok(());
        }

        if let Ok(mut data) = self.performance_data.write() {
            // Add to recent samples
            data.recent_samples.push_back(sample.clone());
            
            // Maintain size limit
            if data.recent_samples.len() > self.config.max_samples {
                data.recent_samples.pop_front();
            }

            // Update hook performance data
            self.update_hook_performance(&mut data, &sample);

            // Update event performance data
            self.update_event_performance(&mut data, &sample);

            // Update current metrics
            self.update_current_metrics(&mut data);

            data.last_updated = Utc::now();
        }

        Ok(())
    }

    /// Update hook-specific performance data.
    fn update_hook_performance(&self, data: &mut PerformanceData, sample: &PerformanceSample) {
        let hook_perf = data.hook_performance
            .entry(sample.hook_id.clone())
            .or_insert_with(|| HookPerformanceData {
                hook_id: sample.hook_id.clone(),
                total_executions: 0,
                successful_executions: 0,
                statistics: PerformanceStatistics {
                    mean: Duration::ZERO,
                    median: Duration::ZERO,
                    std_dev: Duration::ZERO,
                    min: Duration::MAX,
                    max: Duration::ZERO,
                    success_rate: 0.0,
                    throughput: 0.0,
                },
                trend: PerformanceTrend {
                    direction: TrendDirection::Unknown,
                    strength: 0.0,
                    change_percentage: 0.0,
                    analysis_period: Duration::from_hours(1),
                },
                percentiles: HashMap::new(),
                last_execution: None,
            });

        hook_perf.total_executions += 1;
        if sample.success {
            hook_perf.successful_executions += 1;
        }
        hook_perf.last_execution = Some(sample.timestamp);

        // Update statistics
        self.update_statistics(&mut hook_perf.statistics, sample, hook_perf.total_executions);

        // Calculate percentiles
        hook_perf.percentiles = self.calculate_percentiles_for_hook(&sample.hook_id, data);
    }

    /// Update event-specific performance data.
    fn update_event_performance(&self, data: &mut PerformanceData, sample: &PerformanceSample) {
        let event_perf = data.event_performance
            .entry(sample.event_type)
            .or_insert_with(|| EventPerformanceData {
                event_type: sample.event_type,
                total_events: 0,
                average_hooks_per_event: 1.0,
                statistics: PerformanceStatistics {
                    mean: Duration::ZERO,
                    median: Duration::ZERO,
                    std_dev: Duration::ZERO,
                    min: Duration::MAX,
                    max: Duration::ZERO,
                    success_rate: 0.0,
                    throughput: 0.0,
                },
                trend: PerformanceTrend {
                    direction: TrendDirection::Unknown,
                    strength: 0.0,
                    change_percentage: 0.0,
                    analysis_period: Duration::from_hours(1),
                },
            });

        event_perf.total_events += 1;
        self.update_statistics(&mut event_perf.statistics, sample, event_perf.total_events);
    }

    /// Update performance statistics.
    fn update_statistics(&self, stats: &mut PerformanceStatistics, sample: &PerformanceSample, total_count: u64) {
        // Update min/max
        if sample.duration < stats.min {
            stats.min = sample.duration;
        }
        if sample.duration > stats.max {
            stats.max = sample.duration;
        }

        // Update mean (running average)
        let new_mean_ms = (stats.mean.as_millis() as f64 * (total_count - 1) as f64 + sample.duration.as_millis() as f64) / total_count as f64;
        stats.mean = Duration::from_millis(new_mean_ms as u64);

        // Update success rate
        stats.success_rate = if sample.success {
            (stats.success_rate * (total_count - 1) as f64 + 1.0) / total_count as f64
        } else {
            (stats.success_rate * (total_count - 1) as f64) / total_count as f64
        };
    }

    /// Update current real-time metrics.
    fn update_current_metrics(&self, data: &mut PerformanceData) {
        if data.recent_samples.is_empty() {
            return;
        }

        // Calculate throughput over last minute
        let one_minute_ago = Utc::now() - chrono::Duration::minutes(1);
        let recent_count = data.recent_samples
            .iter()
            .filter(|s| s.timestamp > one_minute_ago)
            .count();
        data.current_metrics.throughput = recent_count as f64 / 60.0;

        // Calculate average response time over recent samples
        let recent_durations: Vec<Duration> = data.recent_samples
            .iter()
            .rev()
            .take(100) // Last 100 samples
            .map(|s| s.duration)
            .collect();

        if !recent_durations.is_empty() {
            let total_ms: u64 = recent_durations.iter().map(|d| d.as_millis() as u64).sum();
            data.current_metrics.average_response_time = Duration::from_millis(total_ms / recent_durations.len() as u64);
        }

        // Calculate error rate over recent samples
        let recent_errors = data.recent_samples
            .iter()
            .rev()
            .take(100)
            .filter(|s| !s.success)
            .count();
        data.current_metrics.error_rate = recent_errors as f64 / 100.0.min(data.recent_samples.len() as f64);
    }

    /// Calculate percentiles for a specific hook.
    fn calculate_percentiles_for_hook(&self, hook_id: &str, data: &PerformanceData) -> HashMap<String, Duration> {
        let mut durations: Vec<Duration> = data.recent_samples
            .iter()
            .filter(|s| s.hook_id == hook_id)
            .map(|s| s.duration)
            .collect();

        if durations.is_empty() {
            return HashMap::new();
        }

        durations.sort();
        let mut percentiles = HashMap::new();

        for &percentile in &self.config.percentiles {
            let index = ((percentile / 100.0) * (durations.len() - 1) as f64) as usize;
            let duration = durations.get(index).copied().unwrap_or(Duration::ZERO);
            percentiles.insert(format!("p{}", percentile), duration);
        }

        percentiles
    }

    /// Get current performance data.
    pub fn get_performance_data(&self) -> Result<PerformanceData, HookError> {
        self.performance_data.read()
            .map(|data| data.clone())
            .map_err(|e| HookError::Execution(format!("Failed to read performance data: {}", e)))
    }

    /// Get performance summary for a specific hook.
    pub fn get_hook_performance(&self, hook_id: &str) -> Result<Option<HookPerformanceData>, HookError> {
        self.performance_data.read()
            .map(|data| data.hook_performance.get(hook_id).cloned())
            .map_err(|e| HookError::Execution(format!("Failed to read hook performance: {}", e)))
    }

    /// Update resource metrics.
    pub fn update_resource_metrics(&self, metrics: ResourceMetrics) -> Result<(), HookError> {
        if !self.config.collect_resource_metrics {
            return Ok(());
        }

        if let Ok(mut data) = self.performance_data.write() {
            data.resource_metrics = metrics;
            data.last_updated = Utc::now();
        }

        Ok(())
    }

    /// Update concurrency metrics.
    pub fn update_concurrency_metrics(&self, metrics: ConcurrencyMetrics) -> Result<(), HookError> {
        if !self.config.collect_concurrency_metrics {
            return Ok(());
        }

        if let Ok(mut data) = self.performance_data.write() {
            data.concurrency_metrics = metrics;
            data.last_updated = Utc::now();
        }

        Ok(())
    }

    /// Analyze performance trends.
    pub fn analyze_trends(&self) -> Result<HashMap<String, PerformanceTrend>, HookError> {
        let data = self.get_performance_data()?;
        let mut trends = HashMap::new();

        for (hook_id, hook_perf) in &data.hook_performance {
            let trend = self.calculate_trend_for_hook(hook_id, &data)?;
            trends.insert(hook_id.clone(), trend);
        }

        Ok(trends)
    }

    /// Calculate performance trend for a specific hook.
    fn calculate_trend_for_hook(&self, hook_id: &str, data: &PerformanceData) -> Result<PerformanceTrend, HookError> {
        let recent_samples: Vec<&PerformanceSample> = data.recent_samples
            .iter()
            .filter(|s| s.hook_id == hook_id)
            .collect();

        if recent_samples.len() < 10 {
            return Ok(PerformanceTrend {
                direction: TrendDirection::Unknown,
                strength: 0.0,
                change_percentage: 0.0,
                analysis_period: Duration::from_hours(1),
            });
        }

        // Split samples into two halves for comparison
        let mid_point = recent_samples.len() / 2;
        let first_half = &recent_samples[..mid_point];
        let second_half = &recent_samples[mid_point..];

        let first_avg = first_half.iter()
            .map(|s| s.duration.as_millis() as f64)
            .sum::<f64>() / first_half.len() as f64;

        let second_avg = second_half.iter()
            .map(|s| s.duration.as_millis() as f64)
            .sum::<f64>() / second_half.len() as f64;

        let change_percentage = ((second_avg - first_avg) / first_avg) * 100.0;
        let direction = if change_percentage < -5.0 {
            TrendDirection::Improving
        } else if change_percentage > 5.0 {
            TrendDirection::Degrading
        } else {
            TrendDirection::Stable
        };

        let strength = (change_percentage.abs() / 100.0).min(1.0);

        Ok(PerformanceTrend {
            direction,
            strength,
            change_percentage,
            analysis_period: Duration::from_hours(1),
        })
    }

    /// Export performance data to JSON.
    pub fn export_performance_data(&self) -> Result<String, HookError> {
        let data = self.get_performance_data()?;
        serde_json::to_string_pretty(&data)
            .map_err(|e| HookError::Execution(format!("Failed to serialize performance data: {}", e)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_performance_collector_creation() {
        let collector = PerformanceCollector::default();
        assert!(collector.config.enabled);
    }

    #[test]
    fn test_performance_sample_recording() {
        let collector = PerformanceCollector::default();
        
        let sample = PerformanceSample {
            timestamp: Utc::now(),
            hook_id: "test_hook".to_string(),
            event_type: LifecycleEventType::SessionStart,
            duration: Duration::from_millis(100),
            success: true,
            timing_breakdown: None,
            resource_usage: None,
            concurrency_level: 1,
        };

        collector.record_sample(sample).unwrap();
        
        let data = collector.get_performance_data().unwrap();
        assert_eq!(data.recent_samples.len(), 1);
        assert!(data.hook_performance.contains_key("test_hook"));
    }

    #[test]
    fn test_trend_direction_serialization() {
        let direction = TrendDirection::Improving;
        let serialized = serde_json::to_string(&direction).unwrap();
        let deserialized: TrendDirection = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized, TrendDirection::Improving);
    }

    #[test]
    fn test_performance_statistics_update() {
        let collector = PerformanceCollector::default();
        
        // Record multiple samples
        for i in 0..10 {
            let sample = PerformanceSample {
                timestamp: Utc::now(),
                hook_id: "test_hook".to_string(),
                event_type: LifecycleEventType::SessionStart,
                duration: Duration::from_millis(100 + i * 10),
                success: i % 2 == 0, // 50% success rate
                timing_breakdown: None,
                resource_usage: None,
                concurrency_level: 1,
            };
            collector.record_sample(sample).unwrap();
        }

        let hook_perf = collector.get_hook_performance("test_hook").unwrap().unwrap();
        assert_eq!(hook_perf.total_executions, 10);
        assert_eq!(hook_perf.successful_executions, 5);
        assert_eq!(hook_perf.statistics.success_rate, 0.5);
    }
}
