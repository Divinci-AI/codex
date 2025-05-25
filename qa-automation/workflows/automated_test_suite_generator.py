#!/usr/bin/env python3
"""
Automated Test Suite Generation Workflows for Codex Hooks QA

This module provides automated workflows for generating comprehensive test suites
based on code changes, configuration updates, and system requirements.
"""

import asyncio
import logging
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import hashlib
import git

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

# Import our specialized agents
import sys
sys.path.append(str(Path(__file__).parent.parent / "agents"))
from integrated_qa_system import IntegratedCodexHooksQASystem

logger = logging.getLogger(__name__)


class AutomatedTestSuiteGenerator:
    """
    Automated Test Suite Generator for Codex Hooks QA.
    
    This class provides intelligent test suite generation based on:
    - Code changes and git diffs
    - Configuration file modifications
    - System requirement changes
    - Historical test results and patterns
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, repo_path: str = "."):
        self.model_client = model_client
        self.repo_path = Path(repo_path)
        self.qa_system = IntegratedCodexHooksQASystem(model_client)
        self.test_history = []
        self.change_patterns = {}
        
        # Initialize git repository
        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            logger.warning(f"Not a git repository: {repo_path}")
            self.repo = None
            
    async def generate_test_suite_from_changes(self, 
                                             base_commit: str = "HEAD~1",
                                             target_commit: str = "HEAD") -> Dict[str, Any]:
        """
        Generate test suite based on git changes between commits.
        
        Args:
            base_commit: Base commit for comparison
            target_commit: Target commit for comparison
            
        Returns:
            Generated test suite configuration
        """
        logger.info(f"Generating test suite for changes: {base_commit}..{target_commit}")
        
        try:
            # Analyze changes
            changes = await self._analyze_git_changes(base_commit, target_commit)
            
            # Generate test suite based on changes
            test_suite = await self._generate_targeted_test_suite(changes)
            
            # Add metadata
            test_suite.update({
                "generation_id": f"auto-suite-{int(datetime.now().timestamp())}",
                "generated_at": datetime.now().isoformat(),
                "base_commit": base_commit,
                "target_commit": target_commit,
                "changes_analyzed": changes,
                "generator": "AutomatedTestSuiteGenerator"
            })
            
            # Save test suite
            await self._save_test_suite(test_suite)
            
            logger.info(f"Generated test suite: {test_suite['generation_id']}")
            return test_suite
            
        except Exception as e:
            logger.error(f"Failed to generate test suite from changes: {e}")
            raise
            
    async def generate_test_suite_from_config_changes(self, 
                                                    config_files: List[str]) -> Dict[str, Any]:
        """
        Generate test suite based on configuration file changes.
        
        Args:
            config_files: List of configuration files that changed
            
        Returns:
            Generated test suite configuration
        """
        logger.info(f"Generating test suite for config changes: {config_files}")
        
        try:
            # Analyze configuration changes
            config_analysis = await self._analyze_config_changes(config_files)
            
            # Generate configuration-focused test suite
            test_suite = await self._generate_config_test_suite(config_analysis)
            
            # Add metadata
            test_suite.update({
                "generation_id": f"config-suite-{int(datetime.now().timestamp())}",
                "generated_at": datetime.now().isoformat(),
                "config_files": config_files,
                "config_analysis": config_analysis,
                "generator": "AutomatedTestSuiteGenerator"
            })
            
            # Save test suite
            await self._save_test_suite(test_suite)
            
            logger.info(f"Generated config test suite: {test_suite['generation_id']}")
            return test_suite
            
        except Exception as e:
            logger.error(f"Failed to generate test suite from config changes: {e}")
            raise
            
    async def generate_regression_test_suite(self, 
                                           previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate regression test suite based on previous test results.
        
        Args:
            previous_results: Previous test execution results
            
        Returns:
            Generated regression test suite
        """
        logger.info("Generating regression test suite")
        
        try:
            # Analyze previous failures and issues
            regression_analysis = await self._analyze_regression_patterns(previous_results)
            
            # Generate regression-focused test suite
            test_suite = await self._generate_regression_test_suite(regression_analysis)
            
            # Add metadata
            test_suite.update({
                "generation_id": f"regression-suite-{int(datetime.now().timestamp())}",
                "generated_at": datetime.now().isoformat(),
                "regression_analysis": regression_analysis,
                "generator": "AutomatedTestSuiteGenerator"
            })
            
            # Save test suite
            await self._save_test_suite(test_suite)
            
            logger.info(f"Generated regression test suite: {test_suite['generation_id']}")
            return test_suite
            
        except Exception as e:
            logger.error(f"Failed to generate regression test suite: {e}")
            raise
            
    async def generate_adaptive_test_suite(self, 
                                         system_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate adaptive test suite based on current system context.
        
        Args:
            system_context: Current system state and context
            
        Returns:
            Generated adaptive test suite
        """
        logger.info("Generating adaptive test suite")
        
        try:
            # Analyze system context
            context_analysis = await self._analyze_system_context(system_context)
            
            # Generate context-aware test suite
            test_suite = await self._generate_adaptive_test_suite(context_analysis)
            
            # Add metadata
            test_suite.update({
                "generation_id": f"adaptive-suite-{int(datetime.now().timestamp())}",
                "generated_at": datetime.now().isoformat(),
                "system_context": system_context,
                "context_analysis": context_analysis,
                "generator": "AutomatedTestSuiteGenerator"
            })
            
            # Save test suite
            await self._save_test_suite(test_suite)
            
            logger.info(f"Generated adaptive test suite: {test_suite['generation_id']}")
            return test_suite
            
        except Exception as e:
            logger.error(f"Failed to generate adaptive test suite: {e}")
            raise
            
    async def _analyze_git_changes(self, base_commit: str, target_commit: str) -> Dict[str, Any]:
        """Analyze git changes between commits."""
        if not self.repo:
            return {"error": "No git repository available"}
        
        try:
            # Get diff between commits
            diff = self.repo.git.diff(base_commit, target_commit, name_only=True)
            changed_files = diff.strip().split('\n') if diff.strip() else []
            
            # Categorize changes
            changes = {
                "total_files": len(changed_files),
                "rust_files": [],
                "typescript_files": [],
                "config_files": [],
                "test_files": [],
                "documentation_files": [],
                "other_files": []
            }
            
            for file_path in changed_files:
                if file_path.endswith(('.rs',)):
                    changes["rust_files"].append(file_path)
                elif file_path.endswith(('.ts', '.js')):
                    changes["typescript_files"].append(file_path)
                elif file_path.endswith(('.toml', '.yaml', '.yml', '.json')):
                    changes["config_files"].append(file_path)
                elif 'test' in file_path.lower() or file_path.endswith('.test.ts'):
                    changes["test_files"].append(file_path)
                elif file_path.endswith(('.md', '.txt', '.rst')):
                    changes["documentation_files"].append(file_path)
                else:
                    changes["other_files"].append(file_path)
            
            # Get detailed diff for analysis
            detailed_diff = self.repo.git.diff(base_commit, target_commit)
            changes["diff_stats"] = {
                "lines_changed": len(detailed_diff.split('\n')),
                "has_hook_changes": 'hook' in detailed_diff.lower(),
                "has_config_changes": any(ext in detailed_diff for ext in ['.toml', '.yaml', '.json']),
                "has_test_changes": 'test' in detailed_diff.lower()
            }
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to analyze git changes: {e}")
            return {"error": str(e)}
            
    async def _analyze_config_changes(self, config_files: List[str]) -> Dict[str, Any]:
        """Analyze configuration file changes."""
        analysis = {
            "files_analyzed": len(config_files),
            "config_types": {},
            "changes_detected": [],
            "risk_assessment": "low"
        }
        
        for config_file in config_files:
            try:
                file_path = Path(config_file)
                if not file_path.exists():
                    continue
                
                # Determine config type
                if file_path.suffix == '.toml':
                    analysis["config_types"]["toml"] = analysis["config_types"].get("toml", 0) + 1
                elif file_path.suffix in ['.yaml', '.yml']:
                    analysis["config_types"]["yaml"] = analysis["config_types"].get("yaml", 0) + 1
                elif file_path.suffix == '.json':
                    analysis["config_types"]["json"] = analysis["config_types"].get("json", 0) + 1
                
                # Analyze content for hooks-related changes
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                if 'hook' in content.lower():
                    analysis["changes_detected"].append({
                        "file": str(file_path),
                        "type": "hooks_configuration",
                        "risk": "medium"
                    })
                    analysis["risk_assessment"] = "medium"
                
                if any(keyword in content.lower() for keyword in ['webhook', 'script', 'mcp']):
                    analysis["changes_detected"].append({
                        "file": str(file_path),
                        "type": "hook_types_configuration",
                        "risk": "medium"
                    })
                    
            except Exception as e:
                logger.error(f"Failed to analyze config file {config_file}: {e}")
                
        return analysis
        
    async def _analyze_regression_patterns(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in previous test results to identify regression risks."""
        analysis = {
            "failure_patterns": [],
            "performance_trends": {},
            "risk_areas": [],
            "recommended_focus": []
        }
        
        # Analyze failure patterns
        if "phase_results" in previous_results:
            for phase_name, phase_result in previous_results["phase_results"].items():
                if phase_result.get("status") == "failed":
                    analysis["failure_patterns"].append({
                        "phase": phase_name,
                        "failure_type": "execution_failure",
                        "risk": "high"
                    })
                    analysis["risk_areas"].append(phase_name)
                elif phase_result.get("status") == "warning":
                    analysis["failure_patterns"].append({
                        "phase": phase_name,
                        "failure_type": "warning",
                        "risk": "medium"
                    })
        
        # Recommend focus areas
        if analysis["risk_areas"]:
            analysis["recommended_focus"] = list(set(analysis["risk_areas"]))
        else:
            analysis["recommended_focus"] = ["configuration", "integration", "performance"]
            
        return analysis
        
    async def _analyze_system_context(self, system_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current system context for adaptive test generation."""
        analysis = {
            "environment": system_context.get("environment", "unknown"),
            "load_level": system_context.get("load_level", "normal"),
            "recent_changes": system_context.get("recent_changes", []),
            "system_health": system_context.get("system_health", "unknown"),
            "recommended_tests": []
        }
        
        # Determine recommended tests based on context
        if analysis["load_level"] == "high":
            analysis["recommended_tests"].extend(["performance", "stress", "resource_limits"])
        
        if analysis["environment"] == "production":
            analysis["recommended_tests"].extend(["security", "integration", "monitoring"])
        elif analysis["environment"] == "development":
            analysis["recommended_tests"].extend(["unit", "configuration", "code_quality"])
            
        if analysis["recent_changes"]:
            analysis["recommended_tests"].extend(["regression", "integration"])
            
        return analysis
        
    async def _generate_targeted_test_suite(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test suite targeted at specific changes."""
        test_suite = {
            "name": "Targeted Test Suite",
            "description": "Test suite generated based on code changes",
            "test_phases": [],
            "priority": "high"
        }
        
        # Add configuration tests if config files changed
        if changes.get("config_files"):
            test_suite["test_phases"].append({
                "name": "configuration_validation",
                "priority": "critical",
                "tests": [
                    "validate_hooks_configuration",
                    "validate_example_configurations",
                    "security_configuration_check"
                ]
            })
        
        # Add code analysis if Rust/TypeScript files changed
        if changes.get("rust_files") or changes.get("typescript_files"):
            test_suite["test_phases"].append({
                "name": "code_analysis",
                "priority": "high",
                "tests": [
                    "analyze_hooks_implementation",
                    "security_code_analysis",
                    "performance_code_analysis"
                ]
            })
        
        # Add integration tests if hooks-related changes detected
        if changes.get("diff_stats", {}).get("has_hook_changes"):
            test_suite["test_phases"].append({
                "name": "integration_testing",
                "priority": "critical",
                "tests": [
                    "cli_integration_testing",
                    "hook_execution_validation",
                    "end_to_end_workflows"
                ]
            })
        
        # Add performance tests for significant changes
        if changes.get("total_files", 0) > 5:
            test_suite["test_phases"].append({
                "name": "performance_testing",
                "priority": "medium",
                "tests": [
                    "execution_benchmarks",
                    "resource_usage_analysis",
                    "scalability_testing"
                ]
            })
        
        return test_suite
        
    async def _generate_config_test_suite(self, config_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test suite focused on configuration changes."""
        test_suite = {
            "name": "Configuration Test Suite",
            "description": "Test suite focused on configuration validation",
            "test_phases": [
                {
                    "name": "configuration_validation",
                    "priority": "critical",
                    "tests": [
                        "syntax_validation",
                        "semantic_validation",
                        "security_validation",
                        "compatibility_validation"
                    ]
                },
                {
                    "name": "configuration_integration",
                    "priority": "high",
                    "tests": [
                        "cli_config_loading",
                        "hook_config_application",
                        "environment_override_testing"
                    ]
                }
            ],
            "priority": "critical" if config_analysis.get("risk_assessment") == "high" else "high"
        }
        
        # Add security tests for high-risk changes
        if config_analysis.get("risk_assessment") in ["high", "medium"]:
            test_suite["test_phases"].append({
                "name": "security_validation",
                "priority": "critical",
                "tests": [
                    "privilege_escalation_check",
                    "input_validation_testing",
                    "access_control_validation"
                ]
            })
        
        return test_suite
        
    async def _generate_regression_test_suite(self, regression_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test suite focused on regression testing."""
        test_suite = {
            "name": "Regression Test Suite",
            "description": "Test suite focused on preventing regressions",
            "test_phases": [],
            "priority": "high"
        }
        
        # Focus on previously failed areas
        for focus_area in regression_analysis.get("recommended_focus", []):
            test_suite["test_phases"].append({
                "name": f"{focus_area}_regression",
                "priority": "critical",
                "tests": [
                    f"{focus_area}_functionality_check",
                    f"{focus_area}_performance_check",
                    f"{focus_area}_integration_check"
                ]
            })
        
        # Add comprehensive regression tests
        test_suite["test_phases"].append({
            "name": "comprehensive_regression",
            "priority": "medium",
            "tests": [
                "full_functionality_suite",
                "performance_baseline_comparison",
                "integration_workflow_validation"
            ]
        })
        
        return test_suite
        
    async def _generate_adaptive_test_suite(self, context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate adaptive test suite based on system context."""
        test_suite = {
            "name": "Adaptive Test Suite",
            "description": "Test suite adapted to current system context",
            "test_phases": [],
            "priority": "medium"
        }
        
        # Add tests based on recommended focus areas
        for test_type in context_analysis.get("recommended_tests", []):
            test_suite["test_phases"].append({
                "name": f"{test_type}_testing",
                "priority": "high" if test_type in ["security", "performance"] else "medium",
                "tests": [
                    f"{test_type}_validation",
                    f"{test_type}_analysis",
                    f"{test_type}_reporting"
                ]
            })
        
        return test_suite
        
    async def _save_test_suite(self, test_suite: Dict[str, Any]):
        """Save generated test suite to file."""
        try:
            suites_dir = Path("qa-automation/generated-suites")
            suites_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suite_file = suites_dir / f"test_suite_{timestamp}.json"
            
            with open(suite_file, 'w') as f:
                json.dump(test_suite, f, indent=2)
                
            logger.info(f"Saved test suite to: {suite_file}")
            
        except Exception as e:
            logger.error(f"Failed to save test suite: {e}")
            
    async def cleanup(self):
        """Clean up resources."""
        await self.qa_system.cleanup()
        logger.info("AutomatedTestSuiteGenerator cleanup completed")


# Example usage and testing
async def test_automated_test_suite_generator():
    """Test the automated test suite generator."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create test suite generator
        generator = AutomatedTestSuiteGenerator(client)
        
        # Test change-based generation
        changes_suite = await generator.generate_test_suite_from_changes()
        print(f"Generated changes-based suite: {changes_suite['generation_id']}")
        
        # Test config-based generation
        config_files = ["examples/hooks.toml"]
        config_suite = await generator.generate_test_suite_from_config_changes(config_files)
        print(f"Generated config-based suite: {config_suite['generation_id']}")
        
        # Test adaptive generation
        system_context = {
            "environment": "development",
            "load_level": "normal",
            "recent_changes": ["hooks configuration"],
            "system_health": "good"
        }
        adaptive_suite = await generator.generate_adaptive_test_suite(system_context)
        print(f"Generated adaptive suite: {adaptive_suite['generation_id']}")
        
        # Cleanup
        await generator.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_automated_test_suite_generator())
