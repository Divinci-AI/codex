#!/usr/bin/env python3
"""
End-to-End Testing Scenarios with Magentic-One for Codex Hooks QA

This module provides comprehensive end-to-end testing scenarios that validate
the complete Codex hooks system from CLI interaction to hook execution,
using the full Magentic-One multi-agent system.
"""

import asyncio
import logging
import json
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import uuid

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.teams.magentic_one import MagenticOne
    from autogen_agentchat.ui import Console
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

# Import our specialized agents
import sys
sys.path.append(str(Path(__file__).parent.parent / "agents"))
from integrated_qa_system import IntegratedCodexHooksQASystem

logger = logging.getLogger(__name__)


class E2ETestingScenarios:
    """
    End-to-End Testing Scenarios for Codex Hooks with Magentic-One.
    
    This class provides comprehensive end-to-end testing scenarios that validate
    the complete workflow from CLI commands to hook execution, using the full
    power of the Magentic-One multi-agent system.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient):
        self.model_client = model_client
        self.magentic_one = MagenticOne(client=model_client)
        self.qa_system = IntegratedCodexHooksQASystem(model_client)
        self.test_scenarios = []
        self.execution_results = []
        
        # Test environment setup
        self.test_workspace = Path("qa-automation/e2e-workspace")
        self.test_workspace.mkdir(exist_ok=True)
        
    async def run_complete_e2e_suite(self) -> Dict[str, Any]:
        """
        Run the complete end-to-end testing suite.
        
        Returns:
            Comprehensive E2E test results
        """
        suite_id = f"e2e-suite-{int(datetime.now().timestamp())}"
        logger.info(f"Starting complete E2E testing suite: {suite_id}")
        
        suite_result = {
            "suite_id": suite_id,
            "start_time": datetime.now().isoformat(),
            "scenarios": [],
            "status": "running"
        }
        
        try:
            # Scenario 1: Basic CLI Integration
            scenario_1 = await self.test_basic_cli_integration()
            suite_result["scenarios"].append(scenario_1)
            
            # Scenario 2: Hook Configuration and Loading
            scenario_2 = await self.test_hook_configuration_loading()
            suite_result["scenarios"].append(scenario_2)
            
            # Scenario 3: Script Hook Execution
            scenario_3 = await self.test_script_hook_execution()
            suite_result["scenarios"].append(scenario_3)
            
            # Scenario 4: Webhook Hook Integration
            scenario_4 = await self.test_webhook_hook_integration()
            suite_result["scenarios"].append(scenario_4)
            
            # Scenario 5: Error Handling and Recovery
            scenario_5 = await self.test_error_handling_scenarios()
            suite_result["scenarios"].append(scenario_5)
            
            # Scenario 6: Performance Under Load
            scenario_6 = await self.test_performance_scenarios()
            suite_result["scenarios"].append(scenario_6)
            
            # Scenario 7: Security Validation
            scenario_7 = await self.test_security_scenarios()
            suite_result["scenarios"].append(scenario_7)
            
            # Scenario 8: Multi-Hook Coordination
            scenario_8 = await self.test_multi_hook_coordination()
            suite_result["scenarios"].append(scenario_8)
            
            # Generate comprehensive analysis
            analysis = await self._analyze_e2e_results(suite_result["scenarios"])
            suite_result["analysis"] = analysis
            
            # Determine overall status
            suite_result["status"] = self._determine_suite_status(suite_result["scenarios"])
            suite_result["end_time"] = datetime.now().isoformat()
            
            # Save results
            await self._save_e2e_results(suite_result)
            
            logger.info(f"E2E testing suite completed: {suite_id}")
            return suite_result
            
        except Exception as e:
            logger.error(f"E2E testing suite failed: {e}")
            suite_result.update({
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
            return suite_result
            
    async def test_basic_cli_integration(self) -> Dict[str, Any]:
        """Test basic CLI integration with hooks system."""
        scenario_name = "Basic CLI Integration"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        scenario_prompt = """
        Test the basic CLI integration with the Codex hooks system:
        
        1. **CLI Availability Testing**:
           - Verify Codex CLI is available and functional
           - Test basic CLI commands and help system
           - Validate CLI version and dependencies
        
        2. **Hooks System Integration**:
           - Test CLI hooks enable/disable functionality
           - Verify hooks configuration loading
           - Test hooks status reporting
        
        3. **Basic Command Execution**:
           - Execute simple Codex commands with hooks enabled
           - Verify hook events are triggered correctly
           - Test command output and logging
        
        4. **Environment Validation**:
           - Check environment variable handling
           - Verify working directory behavior
           - Test configuration file discovery
        
        Please execute these tests and provide detailed results including:
        - Command execution results
        - Hook event triggering verification
        - Any errors or issues encountered
        - Performance observations
        - Recommendations for improvements
        """
        
        try:
            # Use Magentic-One to execute the scenario
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_hook_configuration_loading(self) -> Dict[str, Any]:
        """Test hook configuration loading and validation."""
        scenario_name = "Hook Configuration Loading"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        # Create test configuration
        test_config = await self._create_test_configuration()
        
        scenario_prompt = f"""
        Test hook configuration loading and validation:
        
        Test Configuration: {json.dumps(test_config, indent=2)}
        
        1. **Configuration File Loading**:
           - Test loading of hooks.toml configuration
           - Verify TOML syntax parsing
           - Test configuration validation
        
        2. **Hook Definition Processing**:
           - Verify hook type recognition (script, webhook, mcp_tool)
           - Test event type mapping
           - Validate hook parameters and settings
        
        3. **Configuration Validation**:
           - Test required field validation
           - Verify data type checking
           - Test configuration security validation
        
        4. **Error Handling**:
           - Test invalid configuration handling
           - Verify error message clarity
           - Test graceful degradation
        
        5. **Configuration Reloading**:
           - Test dynamic configuration reloading
           - Verify hot-reload functionality
           - Test configuration change detection
        
        Please execute comprehensive configuration testing and report:
        - Configuration loading success/failure
        - Validation results and any issues
        - Performance of configuration processing
        - Error handling effectiveness
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "test_config": test_config,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_script_hook_execution(self) -> Dict[str, Any]:
        """Test script hook execution scenarios."""
        scenario_name = "Script Hook Execution"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        # Create test scripts
        test_scripts = await self._create_test_scripts()
        
        scenario_prompt = f"""
        Test script hook execution in various scenarios:
        
        Test Scripts Created: {json.dumps(test_scripts, indent=2)}
        
        1. **Basic Script Execution**:
           - Test simple script hooks (echo, basic commands)
           - Verify script output capture
           - Test exit code handling
        
        2. **Environment Variable Passing**:
           - Test CODEX_EVENT_TYPE variable
           - Verify CODEX_SESSION_ID passing
           - Test CODEX_TIMESTAMP and other context variables
        
        3. **Script Types Testing**:
           - Test shell script execution
           - Test Python script execution
           - Test Node.js script execution (if available)
        
        4. **Error Scenarios**:
           - Test script execution failures
           - Verify timeout handling
           - Test permission denied scenarios
        
        5. **Performance Testing**:
           - Measure script execution time
           - Test concurrent script execution
           - Verify resource usage
        
        6. **Security Testing**:
           - Test script sandbox isolation
           - Verify command injection prevention
           - Test file system access restrictions
        
        Execute these script hook tests and provide:
        - Execution results for each script type
        - Environment variable verification
        - Performance metrics
        - Security validation results
        - Any issues or recommendations
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "test_scripts": test_scripts,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_webhook_hook_integration(self) -> Dict[str, Any]:
        """Test webhook hook integration scenarios."""
        scenario_name = "Webhook Hook Integration"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        # Set up test webhook server
        webhook_config = await self._setup_test_webhook_server()
        
        scenario_prompt = f"""
        Test webhook hook integration and execution:
        
        Webhook Configuration: {json.dumps(webhook_config, indent=2)}
        
        1. **Webhook Connectivity**:
           - Test webhook endpoint accessibility
           - Verify HTTP/HTTPS connectivity
           - Test network timeout handling
        
        2. **Webhook Payload Testing**:
           - Test JSON payload formatting
           - Verify event data transmission
           - Test payload size limits
        
        3. **Authentication Testing**:
           - Test API key authentication (if configured)
           - Verify bearer token authentication
           - Test custom header authentication
        
        4. **Response Handling**:
           - Test successful response processing
           - Verify error response handling
           - Test retry mechanisms
        
        5. **Performance Testing**:
           - Measure webhook response times
           - Test concurrent webhook calls
           - Verify rate limiting behavior
        
        6. **Error Scenarios**:
           - Test network connectivity failures
           - Verify timeout handling
           - Test malformed response handling
        
        Execute comprehensive webhook testing and report:
        - Connectivity test results
        - Payload transmission verification
        - Authentication test outcomes
        - Performance metrics
        - Error handling effectiveness
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "webhook_config": webhook_config,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_error_handling_scenarios(self) -> Dict[str, Any]:
        """Test error handling and recovery scenarios."""
        scenario_name = "Error Handling and Recovery"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        error_scenarios = await self._create_error_scenarios()
        
        scenario_prompt = f"""
        Test error handling and recovery mechanisms:
        
        Error Scenarios: {json.dumps(error_scenarios, indent=2)}
        
        1. **Configuration Errors**:
           - Test invalid TOML syntax handling
           - Verify missing required field errors
           - Test invalid hook type errors
        
        2. **Execution Errors**:
           - Test script execution failures
           - Verify webhook connection failures
           - Test timeout scenarios
        
        3. **Resource Errors**:
           - Test file not found errors
           - Verify permission denied handling
           - Test resource exhaustion scenarios
        
        4. **Network Errors**:
           - Test network connectivity failures
           - Verify DNS resolution errors
           - Test SSL/TLS certificate errors
        
        5. **Recovery Mechanisms**:
           - Test automatic retry logic
           - Verify graceful degradation
           - Test fallback mechanisms
        
        6. **Error Reporting**:
           - Verify error message clarity
           - Test error logging functionality
           - Validate error notification systems
        
        Execute error handling tests and provide:
        - Error detection accuracy
        - Recovery mechanism effectiveness
        - Error message quality
        - System stability under errors
        - Recommendations for improvements
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "error_scenarios": error_scenarios,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_performance_scenarios(self) -> Dict[str, Any]:
        """Test performance under various load conditions."""
        scenario_name = "Performance Under Load"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        performance_config = await self._create_performance_test_config()
        
        scenario_prompt = f"""
        Test performance under various load conditions:
        
        Performance Test Configuration: {json.dumps(performance_config, indent=2)}
        
        1. **Baseline Performance**:
           - Measure single hook execution time
           - Test memory usage during execution
           - Verify CPU utilization patterns
        
        2. **Concurrent Execution**:
           - Test multiple hooks executing simultaneously
           - Verify resource sharing and isolation
           - Test system stability under load
        
        3. **High-Frequency Events**:
           - Test rapid event triggering
           - Verify event queue handling
           - Test system responsiveness
        
        4. **Large Payload Testing**:
           - Test hooks with large data payloads
           - Verify memory management
           - Test payload processing efficiency
        
        5. **Long-Running Tests**:
           - Test system stability over time
           - Verify memory leak detection
           - Test resource cleanup
        
        6. **Scalability Testing**:
           - Test increasing number of hooks
           - Verify performance degradation patterns
           - Test system limits and thresholds
        
        Execute performance testing and provide:
        - Baseline performance metrics
        - Concurrent execution results
        - Scalability analysis
        - Resource usage patterns
        - Performance optimization recommendations
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "performance_config": performance_config,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_security_scenarios(self) -> Dict[str, Any]:
        """Test security validation scenarios."""
        scenario_name = "Security Validation"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        security_tests = await self._create_security_test_scenarios()
        
        scenario_prompt = f"""
        Test security validation and protection mechanisms:
        
        Security Test Scenarios: {json.dumps(security_tests, indent=2)}
        
        1. **Input Validation**:
           - Test malicious configuration inputs
           - Verify command injection prevention
           - Test path traversal protection
        
        2. **Execution Security**:
           - Test script sandbox isolation
           - Verify privilege escalation prevention
           - Test file system access controls
        
        3. **Network Security**:
           - Test webhook SSL/TLS validation
           - Verify certificate checking
           - Test secure communication protocols
        
        4. **Authentication Security**:
           - Test API key validation
           - Verify token security
           - Test authentication bypass attempts
        
        5. **Data Protection**:
           - Test sensitive data handling
           - Verify data encryption in transit
           - Test data sanitization
        
        6. **System Security**:
           - Test resource access controls
           - Verify system command restrictions
           - Test environment isolation
        
        Execute security testing and provide:
        - Security vulnerability assessment
        - Protection mechanism effectiveness
        - Risk analysis and ratings
        - Security compliance status
        - Remediation recommendations
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "security_tests": security_tests,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_multi_hook_coordination(self) -> Dict[str, Any]:
        """Test multi-hook coordination and workflow scenarios."""
        scenario_name = "Multi-Hook Coordination"
        logger.info(f"Running E2E scenario: {scenario_name}")
        
        coordination_config = await self._create_coordination_test_config()
        
        scenario_prompt = f"""
        Test multi-hook coordination and complex workflows:
        
        Coordination Configuration: {json.dumps(coordination_config, indent=2)}
        
        1. **Sequential Hook Execution**:
           - Test hooks executing in sequence
           - Verify execution order and timing
           - Test data passing between hooks
        
        2. **Parallel Hook Execution**:
           - Test concurrent hook execution
           - Verify resource sharing and isolation
           - Test synchronization mechanisms
        
        3. **Conditional Hook Execution**:
           - Test condition-based hook triggering
           - Verify conditional logic evaluation
           - Test dynamic hook selection
        
        4. **Hook Dependencies**:
           - Test hook dependency resolution
           - Verify dependency chain execution
           - Test circular dependency detection
        
        5. **Event Propagation**:
           - Test event chain propagation
           - Verify event data transformation
           - Test event filtering and routing
        
        6. **Workflow Orchestration**:
           - Test complex multi-step workflows
           - Verify workflow state management
           - Test workflow error recovery
        
        Execute multi-hook coordination tests and provide:
        - Coordination mechanism effectiveness
        - Workflow execution results
        - Performance under complex scenarios
        - Error handling in multi-hook contexts
        - Optimization recommendations
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=scenario_prompt))
            
            return {
                "scenario": scenario_name,
                "status": "completed",
                "coordination_config": coordination_config,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def _create_test_configuration(self) -> Dict[str, Any]:
        """Create test configuration for E2E testing."""
        test_config = {
            "hooks": {
                "enabled": True,
                "timeout_seconds": 30
            },
            "test_hooks": [
                {
                    "name": "test_session_start",
                    "event": "session_start",
                    "type": "script",
                    "command": ["echo", "Session started: $CODEX_SESSION_ID"],
                    "enabled": True
                },
                {
                    "name": "test_webhook",
                    "event": "task_end",
                    "type": "webhook",
                    "url": "http://localhost:8080/webhook/test",
                    "enabled": True
                }
            ]
        }
        
        # Save test configuration
        config_file = self.test_workspace / "test_hooks.toml"
        with open(config_file, 'w') as f:
            import toml
            toml.dump(test_config, f)
            
        return test_config
        
    async def _create_test_scripts(self) -> Dict[str, str]:
        """Create test scripts for script hook testing."""
        scripts = {}
        
        # Simple echo script
        echo_script = "#!/bin/bash\necho \"Test script executed: $CODEX_EVENT_TYPE\"\nexit 0\n"
        echo_file = self.test_workspace / "test_echo.sh"
        with open(echo_file, 'w') as f:
            f.write(echo_script)
        echo_file.chmod(0o755)
        scripts["echo_script"] = str(echo_file)
        
        # Python script
        python_script = """#!/usr/bin/env python3
import os
import sys
print(f"Python script executed")
print(f"Event: {os.getenv('CODEX_EVENT_TYPE', 'unknown')}")
print(f"Session: {os.getenv('CODEX_SESSION_ID', 'unknown')}")
sys.exit(0)
"""
        python_file = self.test_workspace / "test_python.py"
        with open(python_file, 'w') as f:
            f.write(python_script)
        python_file.chmod(0o755)
        scripts["python_script"] = str(python_file)
        
        return scripts
        
    async def _setup_test_webhook_server(self) -> Dict[str, Any]:
        """Set up test webhook server configuration."""
        return {
            "url": "http://localhost:8080/webhook/test",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "timeout": 30
        }
        
    async def _create_error_scenarios(self) -> List[Dict[str, Any]]:
        """Create error scenarios for testing."""
        return [
            {
                "name": "invalid_toml_syntax",
                "description": "Test invalid TOML syntax handling",
                "type": "configuration_error"
            },
            {
                "name": "missing_script_file",
                "description": "Test missing script file handling",
                "type": "execution_error"
            },
            {
                "name": "webhook_timeout",
                "description": "Test webhook timeout handling",
                "type": "network_error"
            },
            {
                "name": "permission_denied",
                "description": "Test permission denied scenarios",
                "type": "security_error"
            }
        ]
        
    async def _create_performance_test_config(self) -> Dict[str, Any]:
        """Create performance test configuration."""
        return {
            "concurrent_hooks": 10,
            "event_frequency": "high",
            "payload_size": "large",
            "duration_minutes": 5,
            "metrics": ["execution_time", "memory_usage", "cpu_usage"]
        }
        
    async def _create_security_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create security test scenarios."""
        return [
            {
                "name": "command_injection",
                "description": "Test command injection prevention",
                "type": "injection_attack"
            },
            {
                "name": "path_traversal",
                "description": "Test path traversal protection",
                "type": "file_access_attack"
            },
            {
                "name": "privilege_escalation",
                "description": "Test privilege escalation prevention",
                "type": "privilege_attack"
            }
        ]
        
    async def _create_coordination_test_config(self) -> Dict[str, Any]:
        """Create multi-hook coordination test configuration."""
        return {
            "sequential_hooks": 3,
            "parallel_hooks": 5,
            "conditional_hooks": 2,
            "dependency_chains": 2,
            "workflow_complexity": "medium"
        }
        
    async def _analyze_e2e_results(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze E2E test results comprehensively."""
        analysis_prompt = f"""
        Analyze the comprehensive E2E test results for the Codex hooks system:
        
        Test Scenarios Results: {json.dumps(scenarios, indent=2)}
        
        Please provide a detailed analysis including:
        
        1. **Overall System Health**:
           - Success rate across all scenarios
           - Critical failure analysis
           - System stability assessment
        
        2. **Performance Analysis**:
           - Performance metrics summary
           - Bottleneck identification
           - Scalability assessment
        
        3. **Security Assessment**:
           - Security vulnerability summary
           - Risk level evaluation
           - Compliance status
        
        4. **Integration Quality**:
           - CLI integration effectiveness
           - Hook execution reliability
           - Error handling quality
        
        5. **Recommendations**:
           - Priority improvements needed
           - Performance optimizations
           - Security enhancements
           - Feature recommendations
        
        Provide actionable insights and specific recommendations for system improvements.
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=analysis_prompt))
            
            return {
                "analysis_id": f"e2e-analysis-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "analysis_content": str(result),
                "scenarios_analyzed": len(scenarios)
            }
            
        except Exception as e:
            logger.error(f"E2E analysis failed: {e}")
            return {
                "analysis_id": f"e2e-analysis-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            
    def _determine_suite_status(self, scenarios: List[Dict[str, Any]]) -> str:
        """Determine overall suite status."""
        total_scenarios = len(scenarios)
        failed_scenarios = len([s for s in scenarios if s.get("status") == "failed"])
        
        if failed_scenarios == 0:
            return "passed"
        elif failed_scenarios < total_scenarios / 2:
            return "passed_with_failures"
        else:
            return "failed"
            
    async def _save_e2e_results(self, suite_result: Dict[str, Any]):
        """Save E2E test results."""
        results_dir = Path("qa-automation/e2e-results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"e2e_suite_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(suite_result, f, indent=2)
            
        logger.info(f"E2E results saved to: {results_file}")
        
    async def cleanup(self):
        """Clean up resources."""
        await self.qa_system.cleanup()
        logger.info("E2ETestingScenarios cleanup completed")


# Example usage and testing
async def test_e2e_scenarios():
    """Test the E2E testing scenarios."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create E2E testing scenarios
        e2e_scenarios = E2ETestingScenarios(client)
        
        # Run complete E2E suite
        suite_result = await e2e_scenarios.run_complete_e2e_suite()
        
        print(f"E2E Suite: {suite_result['suite_id']}")
        print(f"Status: {suite_result['status']}")
        print(f"Scenarios: {len(suite_result['scenarios'])}")
        
        # Cleanup
        await e2e_scenarios.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_e2e_scenarios())
