#!/usr/bin/env python3
"""
Comprehensive Logging and Monitoring System for Magentic-One QA

This module provides centralized logging, monitoring, and alerting
for the Magentic-One QA automation system.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import threading
import queue
import time

logger = logging.getLogger(__name__)


class ComprehensiveLoggingSystem:
    """
    Comprehensive logging system for Magentic-One QA automation.

    Provides structured logging, log aggregation, and real-time monitoring
    of all QA activities and agent operations.
    """

    def __init__(self, log_level: str = "INFO"):
        self.log_level = getattr(logging, log_level.upper())
        self.log_queue = queue.Queue()
        self.log_handlers = []
        self.active_sessions = {}

        # Log storage directories
        self.logs_dir = Path("qa-automation/logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Initialize logging components
        self._setup_logging()
        self._start_log_processor()

    def _setup_logging(self):
        """Set up logging configuration."""

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )

        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # File handlers
        main_log_file = self.logs_dir / "qa_automation.log"
        error_log_file = self.logs_dir / "errors.log"

        # Main log handler
        main_handler = logging.FileHandler(main_log_file)
        main_handler.setLevel(self.log_level)
        main_handler.setFormatter(detailed_formatter)

        # Error log handler
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)

        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)

        self.log_handlers = [main_handler, error_handler, console_handler]

    def _start_log_processor(self):
        """Start background log processing thread."""
        self.log_processor_thread = threading.Thread(
            target=self._process_logs,
            daemon=True
        )
        self.log_processor_thread.start()

    def _process_logs(self):
        """Process logs in background thread."""
        while True:
            try:
                # Get log entry from queue
                log_entry = self.log_queue.get(timeout=1)

                # Process the log entry
                self._handle_log_entry(log_entry)

                # Mark task as done
                self.log_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing log entry: {e}")

    def _handle_log_entry(self, log_entry: Dict[str, Any]):
        """Handle individual log entry."""

        # Save structured log
        self._save_structured_log(log_entry)

        # Check for alerts
        self._check_log_alerts(log_entry)

        # Update metrics
        self._update_log_metrics(log_entry)

    def log_qa_event(self,
                    event_type: str,
                    agent_type: str,
                    session_id: str,
                    data: Dict[str, Any],
                    level: str = "INFO"):
        """
        Log a QA automation event.

        Args:
            event_type: Type of event (execution, validation, error, etc.)
            agent_type: Type of agent generating the event
            session_id: QA session identifier
            data: Event data
            level: Log level
        """

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "agent_type": agent_type,
            "session_id": session_id,
            "level": level,
            "data": data
        }

        # Add to queue for processing
        self.log_queue.put(log_entry)

        # Also log to standard logger
        log_level = getattr(logging, level.upper())
        logger.log(log_level, f"{event_type} - {agent_type}: {data.get('message', '')}")

    def _save_structured_log(self, log_entry: Dict[str, Any]):
        """Save structured log entry to file."""

        # Create session-specific log file
        session_id = log_entry.get("session_id", "unknown")
        session_log_file = self.logs_dir / f"session_{session_id}.jsonl"

        # Append log entry
        with open(session_log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _check_log_alerts(self, log_entry: Dict[str, Any]):
        """Check if log entry should trigger alerts."""

        level = log_entry.get("level", "INFO")
        event_type = log_entry.get("event_type", "")

        # Critical error alert
        if level == "CRITICAL":
            self._send_alert("critical", log_entry)

        # Security event alert
        if "security" in event_type.lower():
            self._send_alert("security", log_entry)

        # Performance alert
        if "performance" in event_type.lower():
            data = log_entry.get("data", {})
            if data.get("execution_time", 0) > 300:  # 5 minutes
                self._send_alert("performance", log_entry)

    def _send_alert(self, alert_type: str, log_entry: Dict[str, Any]):
        """Send alert for log entry."""

        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "log_entry": log_entry,
            "status": "active"
        }

        # Save alert
        alerts_file = self.logs_dir / "alerts.jsonl"
        with open(alerts_file, "a") as f:
            f.write(json.dumps(alert) + "\n")

        logger.warning(f"Alert generated: {alert_type} - {log_entry.get('event_type')}")

    def _update_log_metrics(self, log_entry: Dict[str, Any]):
        """Update logging metrics."""

        # This would update metrics like:
        # - Events per minute
        # - Error rates
        # - Agent activity levels
        # - Performance trends

        pass  # Implementation would depend on metrics storage system


class MonitoringDashboard:
    """
    Real-time monitoring dashboard for QA automation system.

    Provides real-time visibility into system health, performance,
    and security status of the Magentic-One QA automation.
    """

    def __init__(self, logging_system: ComprehensiveLoggingSystem):
        self.logging_system = logging_system
        self.metrics = {}
        self.alerts = []
        self.system_status = "healthy"

        # Monitoring intervals
        self.monitoring_interval = 30  # seconds
        self.metrics_retention = timedelta(hours=24)

        # Start monitoring
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring tasks."""

        # Start metrics collection
        self.metrics_thread = threading.Thread(
            target=self._collect_metrics,
            daemon=True
        )
        self.metrics_thread.start()

    def _collect_metrics(self):
        """Collect system metrics continuously."""

        while True:
            try:
                # Collect current metrics
                current_metrics = self._gather_current_metrics()

                # Store metrics
                timestamp = datetime.now()
                self.metrics[timestamp] = current_metrics

                # Clean old metrics
                self._cleanup_old_metrics()

                # Update system status
                self._update_system_status(current_metrics)

                # Sleep until next collection
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                time.sleep(self.monitoring_interval)

    def _gather_current_metrics(self) -> Dict[str, Any]:
        """Gather current system metrics."""

        return {
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(self.logging_system.active_sessions),
            "log_queue_size": self.logging_system.log_queue.qsize(),
            "system_status": self.system_status,
            "alerts_count": len(self.alerts),
            "memory_usage": self._get_memory_usage(),
            "cpu_usage": self._get_cpu_usage()
        }

    def _get_memory_usage(self) -> float:
        """Get current memory usage."""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0

    def _cleanup_old_metrics(self):
        """Remove old metrics beyond retention period."""

        cutoff_time = datetime.now() - self.metrics_retention

        # Remove old metrics
        old_timestamps = [
            ts for ts in self.metrics.keys()
            if ts < cutoff_time
        ]

        for ts in old_timestamps:
            del self.metrics[ts]

    def _update_system_status(self, metrics: Dict[str, Any]):
        """Update overall system status based on metrics."""

        # Check various health indicators
        issues = []

        # Check log queue size
        if metrics.get("log_queue_size", 0) > 1000:
            issues.append("high_log_queue")

        # Check memory usage
        if metrics.get("memory_usage", 0) > 90:
            issues.append("high_memory")

        # Check CPU usage
        if metrics.get("cpu_usage", 0) > 90:
            issues.append("high_cpu")

        # Check alerts
        if metrics.get("alerts_count", 0) > 10:
            issues.append("high_alerts")

        # Determine status
        if not issues:
            self.system_status = "healthy"
        elif len(issues) == 1:
            self.system_status = "warning"
        else:
            self.system_status = "critical"

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data."""

        # Get recent metrics
        recent_metrics = list(self.metrics.values())[-10:] if self.metrics else []

        return {
            "system_status": self.system_status,
            "current_time": datetime.now().isoformat(),
            "recent_metrics": recent_metrics,
            "active_alerts": self.alerts[-5:],  # Last 5 alerts
            "summary": {
                "total_sessions": len(self.logging_system.active_sessions),
                "log_queue_size": self.logging_system.log_queue.qsize(),
                "alerts_count": len(self.alerts)
            }
        }
