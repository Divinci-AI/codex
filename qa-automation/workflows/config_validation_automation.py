#!/usr/bin/env python3
"""
Hook Configuration Validation Automation for Codex Hooks QA

This module provides automated workflows for continuous validation of
hook configurations, including real-time monitoring, change detection,
and automated validation pipelines.
"""

import asyncio
import logging
import json
import toml
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import hashlib
import watchdog.observers
import watchdog.events
from dataclasses import dataclass

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

# Import our specialized agents
import sys
sys.path.append(str(Path(__file__).parent.parent / "agents"))
from file_surfer_agent import CodexHooksFileSurferAgent

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a configuration validation."""
    file_path: str
    validation_id: str
    timestamp: datetime
    status: str  # "passed", "failed", "warning"
    issues: List[Dict[str, Any]]
    score: float
    recommendations: List[str]


class ConfigurationFileWatcher(watchdog.events.FileSystemEventHandler):
    """File system watcher for configuration file changes."""
    
    def __init__(self, validation_automation):
        self.validation_automation = validation_automation
        self.debounce_time = 2.0  # seconds
        self.pending_validations = {}
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a configuration file we care about
        if self._is_config_file(file_path):
            logger.info(f"Configuration file modified: {file_path}")
            self._schedule_validation(file_path)
            
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        if self._is_config_file(file_path):
            logger.info(f"Configuration file created: {file_path}")
            self._schedule_validation(file_path)
            
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if a file is a configuration file we should validate."""
        config_extensions = {'.toml', '.yaml', '.yml', '.json'}
        config_patterns = {'hooks', 'config', 'settings'}
        
        # Check extension
        if file_path.suffix.lower() not in config_extensions:
            return False
            
        # Check if filename contains config-related patterns
        filename_lower = file_path.name.lower()
        return any(pattern in filename_lower for pattern in config_patterns)
        
    def _schedule_validation(self, file_path: Path):
        """Schedule validation with debouncing."""
        file_key = str(file_path)
        
        # Cancel existing validation if pending
        if file_key in self.pending_validations:
            self.pending_validations[file_key].cancel()
            
        # Schedule new validation
        loop = asyncio.get_event_loop()
        self.pending_validations[file_key] = loop.call_later(
            self.debounce_time,
            lambda: asyncio.create_task(
                self.validation_automation.validate_config_file_async(file_path)
            )
        )


class ConfigValidationAutomation:
    """
    Automated Configuration Validation System for Codex Hooks.
    
    This class provides continuous monitoring and validation of hook
    configurations with real-time feedback and automated remediation.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, watch_directories: List[str] = None):
        self.model_client = model_client
        self.file_surfer = CodexHooksFileSurferAgent(model_client)
        self.validation_history = []
        self.validation_cache = {}
        self.watch_directories = watch_directories or ["examples", "qa-automation/config"]
        
        # File system monitoring
        self.observer = None
        self.file_watcher = ConfigurationFileWatcher(self)
        
        # Validation rules and thresholds
        self.validation_rules = self._load_validation_rules()
        self.quality_thresholds = {
            "minimum_score": 7.0,
            "critical_issues_max": 0,
            "high_issues_max": 2,
            "medium_issues_max": 5
        }
        
    async def start_continuous_monitoring(self):
        """Start continuous monitoring of configuration files."""
        logger.info("Starting continuous configuration monitoring")
        
        try:
            # Set up file system monitoring
            self.observer = watchdog.observers.Observer()
            
            for watch_dir in self.watch_directories:
                watch_path = Path(watch_dir)
                if watch_path.exists():
                    self.observer.schedule(
                        self.file_watcher,
                        str(watch_path),
                        recursive=True
                    )
                    logger.info(f"Monitoring directory: {watch_path}")
                else:
                    logger.warning(f"Watch directory does not exist: {watch_path}")
            
            self.observer.start()
            
            # Perform initial validation of all config files
            await self._perform_initial_validation()
            
            logger.info("Continuous monitoring started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start continuous monitoring: {e}")
            raise
            
    async def stop_continuous_monitoring(self):
        """Stop continuous monitoring."""
        logger.info("Stopping continuous configuration monitoring")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
        logger.info("Continuous monitoring stopped")
        
    async def validate_config_file_async(self, file_path: Path) -> ValidationResult:
        """Asynchronously validate a configuration file."""
        try:
            logger.info(f"Validating configuration file: {file_path}")
            
            # Check cache first
            file_hash = self._get_file_hash(file_path)
            cache_key = f"{file_path}:{file_hash}"
            
            if cache_key in self.validation_cache:
                logger.info(f"Using cached validation result for: {file_path}")
                return self.validation_cache[cache_key]
            
            # Perform validation
            validation_result = await self.file_surfer.validate_hooks_configuration(str(file_path))
            
            # Process and analyze results
            processed_result = await self._process_validation_result(file_path, validation_result)
            
            # Cache result
            self.validation_cache[cache_key] = processed_result
            
            # Store in history
            self.validation_history.append(processed_result)
            
            # Check if immediate action is needed
            await self._check_validation_alerts(processed_result)
            
            # Save validation report
            await self._save_validation_report(processed_result)
            
            logger.info(f"Validation completed for: {file_path} (Status: {processed_result.status})")
            return processed_result
            
        except Exception as e:
            logger.error(f"Validation failed for {file_path}: {e}")
            
            # Create error result
            error_result = ValidationResult(
                file_path=str(file_path),
                validation_id=f"error-{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                status="failed",
                issues=[{"type": "validation_error", "message": str(e), "severity": "critical"}],
                score=0.0,
                recommendations=["Fix validation error and retry"]
            )
            
            self.validation_history.append(error_result)
            return error_result
            
    async def validate_all_configurations(self) -> Dict[str, ValidationResult]:
        """Validate all configuration files in monitored directories."""
        logger.info("Validating all configuration files")
        
        results = {}
        config_files = self._discover_config_files()
        
        for config_file in config_files:
            try:
                result = await self.validate_config_file_async(config_file)
                results[str(config_file)] = result
            except Exception as e:
                logger.error(f"Failed to validate {config_file}: {e}")
                
        # Generate summary report
        await self._generate_summary_report(results)
        
        logger.info(f"Completed validation of {len(results)} configuration files")
        return results
        
    async def run_validation_pipeline(self, 
                                    config_files: List[str] = None,
                                    validation_level: str = "comprehensive") -> Dict[str, Any]:
        """
        Run automated validation pipeline.
        
        Args:
            config_files: Specific files to validate (None for all)
            validation_level: "basic", "standard", "comprehensive"
            
        Returns:
            Pipeline execution results
        """
        pipeline_id = f"pipeline-{int(datetime.now().timestamp())}"
        logger.info(f"Running validation pipeline: {pipeline_id} (level: {validation_level})")
        
        pipeline_result = {
            "pipeline_id": pipeline_id,
            "start_time": datetime.now().isoformat(),
            "validation_level": validation_level,
            "files_processed": 0,
            "validation_results": {},
            "summary": {},
            "status": "running"
        }
        
        try:
            # Determine files to validate
            if config_files:
                files_to_validate = [Path(f) for f in config_files]
            else:
                files_to_validate = self._discover_config_files()
            
            pipeline_result["files_processed"] = len(files_to_validate)
            
            # Run validations based on level
            if validation_level == "basic":
                results = await self._run_basic_validation(files_to_validate)
            elif validation_level == "standard":
                results = await self._run_standard_validation(files_to_validate)
            else:  # comprehensive
                results = await self._run_comprehensive_validation(files_to_validate)
            
            pipeline_result["validation_results"] = {
                str(k): self._serialize_validation_result(v) for k, v in results.items()
            }
            
            # Generate summary
            pipeline_result["summary"] = self._generate_pipeline_summary(results)
            pipeline_result["status"] = "completed"
            pipeline_result["end_time"] = datetime.now().isoformat()
            
            # Save pipeline results
            await self._save_pipeline_results(pipeline_result)
            
            logger.info(f"Validation pipeline completed: {pipeline_id}")
            return pipeline_result
            
        except Exception as e:
            logger.error(f"Validation pipeline failed: {e}")
            pipeline_result.update({
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
            return pipeline_result
            
    async def _perform_initial_validation(self):
        """Perform initial validation of all configuration files."""
        logger.info("Performing initial validation of all configuration files")
        
        try:
            await self.validate_all_configurations()
        except Exception as e:
            logger.error(f"Initial validation failed: {e}")
            
    async def _process_validation_result(self, 
                                       file_path: Path, 
                                       raw_result: Dict[str, Any]) -> ValidationResult:
        """Process raw validation result into structured format."""
        
        # Extract issues and calculate score
        issues = self._extract_issues_from_result(raw_result)
        score = self._calculate_quality_score(issues)
        status = self._determine_status(score, issues)
        recommendations = self._generate_recommendations(issues, score)
        
        return ValidationResult(
            file_path=str(file_path),
            validation_id=raw_result.get("validation_id", f"val-{int(datetime.now().timestamp())}"),
            timestamp=datetime.now(),
            status=status,
            issues=issues,
            score=score,
            recommendations=recommendations
        )
        
    def _extract_issues_from_result(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and categorize issues from raw validation result."""
        issues = []
        
        # Parse the detailed validation content for issues
        validation_content = raw_result.get("detailed_validation", "")
        
        # Simple pattern matching for common issues
        issue_patterns = {
            "syntax error": {"severity": "critical", "category": "syntax"},
            "missing required": {"severity": "high", "category": "configuration"},
            "deprecated": {"severity": "medium", "category": "compatibility"},
            "security risk": {"severity": "high", "category": "security"},
            "performance": {"severity": "medium", "category": "performance"},
            "warning": {"severity": "low", "category": "general"}
        }
        
        for pattern, metadata in issue_patterns.items():
            if pattern in validation_content.lower():
                issues.append({
                    "type": pattern.replace(" ", "_"),
                    "message": f"Detected {pattern} in configuration",
                    "severity": metadata["severity"],
                    "category": metadata["category"],
                    "line": None  # Could be enhanced with line number detection
                })
        
        return issues
        
    def _calculate_quality_score(self, issues: List[Dict[str, Any]]) -> float:
        """Calculate quality score based on issues."""
        base_score = 10.0
        
        severity_penalties = {
            "critical": 3.0,
            "high": 2.0,
            "medium": 1.0,
            "low": 0.5
        }
        
        for issue in issues:
            severity = issue.get("severity", "low")
            penalty = severity_penalties.get(severity, 0.5)
            base_score -= penalty
            
        return max(0.0, min(10.0, base_score))
        
    def _determine_status(self, score: float, issues: List[Dict[str, Any]]) -> str:
        """Determine validation status based on score and issues."""
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        high_issues = [i for i in issues if i.get("severity") == "high"]
        
        if critical_issues or score < 5.0:
            return "failed"
        elif high_issues or score < 7.0:
            return "warning"
        else:
            return "passed"
            
    def _generate_recommendations(self, issues: List[Dict[str, Any]], score: float) -> List[str]:
        """Generate recommendations based on issues and score."""
        recommendations = []
        
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        high_issues = [i for i in issues if i.get("severity") == "high"]
        
        if critical_issues:
            recommendations.append("Address critical issues immediately before deployment")
            
        if high_issues:
            recommendations.append("Review and fix high-severity issues")
            
        if score < 7.0:
            recommendations.append("Improve configuration quality to meet minimum standards")
            
        if not issues:
            recommendations.append("Configuration looks good - consider adding more comprehensive tests")
            
        return recommendations
        
    async def _check_validation_alerts(self, result: ValidationResult):
        """Check if validation result requires immediate alerts."""
        if result.status == "failed":
            await self._send_alert(
                "critical",
                f"Configuration validation failed: {result.file_path}",
                result
            )
        elif result.status == "warning" and result.score < 6.0:
            await self._send_alert(
                "warning",
                f"Configuration quality below threshold: {result.file_path}",
                result
            )
            
    async def _send_alert(self, level: str, message: str, result: ValidationResult):
        """Send alert for validation issues."""
        alert = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "file_path": result.file_path,
            "validation_id": result.validation_id,
            "score": result.score,
            "issues_count": len(result.issues)
        }
        
        # Save alert to file (could be enhanced to send to monitoring systems)
        alerts_dir = Path("qa-automation/alerts")
        alerts_dir.mkdir(exist_ok=True)
        
        alert_file = alerts_dir / f"alert_{int(datetime.now().timestamp())}.json"
        with open(alert_file, 'w') as f:
            json.dump(alert, f, indent=2)
            
        logger.warning(f"Alert generated: {message}")
        
    def _discover_config_files(self) -> List[Path]:
        """Discover all configuration files in monitored directories."""
        config_files = []
        config_extensions = {'.toml', '.yaml', '.yml', '.json'}
        
        for watch_dir in self.watch_directories:
            watch_path = Path(watch_dir)
            if watch_path.exists():
                for file_path in watch_path.rglob("*"):
                    if (file_path.is_file() and 
                        file_path.suffix.lower() in config_extensions and
                        self.file_watcher._is_config_file(file_path)):
                        config_files.append(file_path)
                        
        return config_files
        
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file content for caching."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return str(datetime.now().timestamp())
            
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules configuration."""
        return {
            "required_sections": ["hooks"],
            "required_fields": ["enabled", "timeout_seconds"],
            "security_checks": ["no_dangerous_commands", "secure_urls"],
            "performance_checks": ["reasonable_timeouts", "resource_limits"]
        }
        
    async def _run_basic_validation(self, files: List[Path]) -> Dict[Path, ValidationResult]:
        """Run basic validation (syntax and structure only)."""
        results = {}
        for file_path in files:
            result = await self.validate_config_file_async(file_path)
            results[file_path] = result
        return results
        
    async def _run_standard_validation(self, files: List[Path]) -> Dict[Path, ValidationResult]:
        """Run standard validation (basic + security checks)."""
        # For now, same as basic - could be enhanced
        return await self._run_basic_validation(files)
        
    async def _run_comprehensive_validation(self, files: List[Path]) -> Dict[Path, ValidationResult]:
        """Run comprehensive validation (all checks + performance analysis)."""
        # For now, same as basic - could be enhanced
        return await self._run_basic_validation(files)
        
    def _generate_pipeline_summary(self, results: Dict[Path, ValidationResult]) -> Dict[str, Any]:
        """Generate summary of pipeline results."""
        total_files = len(results)
        passed = sum(1 for r in results.values() if r.status == "passed")
        warnings = sum(1 for r in results.values() if r.status == "warning")
        failed = sum(1 for r in results.values() if r.status == "failed")
        
        avg_score = sum(r.score for r in results.values()) / total_files if total_files > 0 else 0
        
        return {
            "total_files": total_files,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "average_score": round(avg_score, 2),
            "pass_rate": round((passed / total_files) * 100, 1) if total_files > 0 else 0
        }
        
    def _serialize_validation_result(self, result: ValidationResult) -> Dict[str, Any]:
        """Serialize ValidationResult for JSON storage."""
        return {
            "file_path": result.file_path,
            "validation_id": result.validation_id,
            "timestamp": result.timestamp.isoformat(),
            "status": result.status,
            "issues": result.issues,
            "score": result.score,
            "recommendations": result.recommendations
        }
        
    async def _save_validation_report(self, result: ValidationResult):
        """Save individual validation report."""
        reports_dir = Path("qa-automation/validation-reports")
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"validation_{timestamp}_{result.validation_id}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self._serialize_validation_result(result), f, indent=2)
            
    async def _save_pipeline_results(self, pipeline_result: Dict[str, Any]):
        """Save pipeline execution results."""
        pipelines_dir = Path("qa-automation/pipeline-results")
        pipelines_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pipeline_file = pipelines_dir / f"pipeline_{timestamp}_{pipeline_result['pipeline_id']}.json"
        
        with open(pipeline_file, 'w') as f:
            json.dump(pipeline_result, f, indent=2)
            
    async def _generate_summary_report(self, results: Dict[str, ValidationResult]):
        """Generate summary report for all validations."""
        summary = self._generate_pipeline_summary(results)
        
        summary_dir = Path("qa-automation/summary-reports")
        summary_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = summary_dir / f"validation_summary_{timestamp}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
    async def cleanup(self):
        """Clean up resources."""
        await self.stop_continuous_monitoring()
        await self.file_surfer.cleanup()
        logger.info("ConfigValidationAutomation cleanup completed")


# Example usage and testing
async def test_config_validation_automation():
    """Test the configuration validation automation."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create validation automation
        automation = ConfigValidationAutomation(client)
        
        # Test pipeline execution
        pipeline_result = await automation.run_validation_pipeline(
            validation_level="standard"
        )
        print(f"Pipeline completed: {pipeline_result['pipeline_id']}")
        print(f"Files processed: {pipeline_result['files_processed']}")
        print(f"Summary: {pipeline_result['summary']}")
        
        # Test individual file validation
        config_files = automation._discover_config_files()
        if config_files:
            result = await automation.validate_config_file_async(config_files[0])
            print(f"Individual validation: {result.status} (score: {result.score})")
        
        # Cleanup
        await automation.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_config_validation_automation())
