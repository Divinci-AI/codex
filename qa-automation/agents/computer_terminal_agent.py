#!/usr/bin/env python3
"""
Specialized ComputerTerminal Agent for Codex Hooks CLI Testing

This module provides an enhanced ComputerTerminal agent specifically designed for
automated CLI testing, command execution validation, and system-level testing
of the Codex lifecycle hooks system.
"""

import asyncio
import logging
import json
import subprocess
import shlex
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import os
import tempfile

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.agents import CodeExecutorAgent
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class CodexHooksComputerTerminalAgent:
    """
    Specialized ComputerTerminal Agent for Codex Hooks CLI Testing.
    
    This agent provides enhanced command execution capabilities specifically designed
    for testing the Codex CLI integration, validating hook execution, and performing
    comprehensive system-level testing of the hooks system.
    """
    
    def __init__(self, model_client: Optional[OpenAIChatCompletionClient] = None, name: str = "HooksTerminal"):
        self.model_client = model_client
        self.name = name
        self.execution_results = []
        self.command_history = []
        
        # Safety configuration
        self.allowed_commands = {
            'ls', 'cat', 'grep', 'find', 'head', 'tail', 'wc', 'sort', 'uniq',
            'python', 'python3', 'node', 'npm', 'pnpm', 'cargo', 'git',
            'codex', 'echo', 'pwd', 'cd', 'mkdir', 'touch', 'cp', 'mv',
            'which', 'whereis', 'type', 'file', 'stat', 'du', 'df',
            'ps', 'top', 'htop', 'free', 'uptime', 'whoami', 'id',
            'curl', 'wget', 'ping', 'nslookup', 'dig', 'netstat',
            'tar', 'gzip', 'gunzip', 'zip', 'unzip'
        }
        
        self.blocked_commands = {
            'rm', 'rmdir', 'sudo', 'su', 'chmod', 'chown', 'chgrp',
            'kill', 'killall', 'pkill', 'reboot', 'shutdown', 'halt',
            'format', 'fdisk', 'dd', 'mount', 'umount', 'fsck',
            'iptables', 'ufw', 'firewall-cmd', 'systemctl', 'service'
        }
        
        # Create code executor with safety restrictions
        self.code_executor = LocalCommandLineCodeExecutor(
            timeout=30,  # 30 second timeout
            work_dir=Path.cwd()
        )
        
        # Create the underlying CodeExecutorAgent if model client is provided
        if self.model_client:
            self.agent = CodeExecutorAgent(
                name=self.name,
                code_executor=self.code_executor
            )
        else:
            self.agent = None
            
    async def test_codex_cli_integration(self, test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test Codex CLI integration with hooks system.
        
        Args:
            test_scenarios: List of CLI test scenarios
            
        Returns:
            CLI integration test results
        """
        logger.info(f"Testing Codex CLI integration with {len(test_scenarios)} scenarios")
        
        test_results = []
        
        for scenario in test_scenarios:
            try:
                scenario_result = await self._execute_cli_test_scenario(scenario)
                test_results.append(scenario_result)
            except Exception as e:
                logger.error(f"CLI test scenario failed: {e}")
                test_results.append({
                    "scenario": scenario.get("name", "Unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        integration_result = {
            "test_id": f"cli-integration-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "scenarios_tested": len(test_scenarios),
            "test_results": test_results,
            "overall_status": self._determine_overall_status(test_results),
            "status": "completed"
        }
        
        # Store result
        self.execution_results.append(integration_result)
        
        logger.info(f"Completed CLI integration testing: {integration_result['test_id']}")
        return integration_result
        
    async def validate_hook_execution(self, hook_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate hook execution through CLI commands.
        
        Args:
            hook_configs: List of hook configurations to validate
            
        Returns:
            Hook execution validation results
        """
        logger.info(f"Validating execution of {len(hook_configs)} hooks")
        
        validation_results = []
        
        for hook_config in hook_configs:
            try:
                validation_result = await self._validate_individual_hook(hook_config)
                validation_results.append(validation_result)
            except Exception as e:
                logger.error(f"Hook validation failed: {e}")
                validation_results.append({
                    "hook_name": hook_config.get("name", "Unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        overall_result = {
            "validation_id": f"hook-validation-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "hooks_validated": len(hook_configs),
            "validation_results": validation_results,
            "overall_status": self._determine_overall_status(validation_results),
            "status": "completed"
        }
        
        # Store result
        self.execution_results.append(overall_result)
        
        logger.info(f"Completed hook execution validation: {overall_result['validation_id']}")
        return overall_result
        
    async def test_system_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test system requirements and environment setup.
        
        Args:
            requirements: System requirements to validate
            
        Returns:
            System requirements validation results
        """
        logger.info("Testing system requirements and environment")
        
        requirement_tests = []
        
        # Test basic system information
        system_info = await self._get_system_information()
        requirement_tests.append({
            "test": "System Information",
            "status": "completed",
            "result": system_info
        })
        
        # Test required dependencies
        if "dependencies" in requirements:
            for dep in requirements["dependencies"]:
                dep_result = await self._test_dependency(dep)
                requirement_tests.append(dep_result)
        
        # Test file permissions
        if "file_permissions" in requirements:
            for file_check in requirements["file_permissions"]:
                perm_result = await self._test_file_permissions(file_check)
                requirement_tests.append(perm_result)
        
        # Test network connectivity
        if "network_tests" in requirements:
            for network_test in requirements["network_tests"]:
                net_result = await self._test_network_connectivity(network_test)
                requirement_tests.append(net_result)
        
        # Test environment variables
        if "environment_variables" in requirements:
            for env_var in requirements["environment_variables"]:
                env_result = await self._test_environment_variable(env_var)
                requirement_tests.append(env_result)
        
        system_result = {
            "system_test_id": f"system-test-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "requirement_tests": requirement_tests,
            "overall_status": self._determine_overall_status(requirement_tests),
            "status": "completed"
        }
        
        # Store result
        self.execution_results.append(system_result)
        
        logger.info(f"Completed system requirements testing: {system_result['system_test_id']}")
        return system_result
        
    async def execute_performance_benchmarks(self, benchmark_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute performance benchmarks for hooks system.
        
        Args:
            benchmark_configs: List of benchmark configurations
            
        Returns:
            Performance benchmark results
        """
        logger.info(f"Executing {len(benchmark_configs)} performance benchmarks")
        
        benchmark_results = []
        
        for benchmark_config in benchmark_configs:
            try:
                benchmark_result = await self._execute_performance_benchmark(benchmark_config)
                benchmark_results.append(benchmark_result)
            except Exception as e:
                logger.error(f"Performance benchmark failed: {e}")
                benchmark_results.append({
                    "benchmark_name": benchmark_config.get("name", "Unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        performance_result = {
            "benchmark_id": f"performance-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "benchmarks_executed": len(benchmark_configs),
            "benchmark_results": benchmark_results,
            "overall_status": self._determine_overall_status(benchmark_results),
            "status": "completed"
        }
        
        # Store result
        self.execution_results.append(performance_result)
        
        logger.info(f"Completed performance benchmarks: {performance_result['benchmark_id']}")
        return performance_result
        
    async def _execute_cli_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single CLI test scenario."""
        scenario_name = scenario.get("name", "Unknown")
        commands = scenario.get("commands", [])
        expected_outputs = scenario.get("expected_outputs", [])
        
        logger.info(f"Executing CLI test scenario: {scenario_name}")
        
        command_results = []
        
        for i, command in enumerate(commands):
            try:
                # Validate command safety
                if not self._is_command_safe(command):
                    command_results.append({
                        "command": command,
                        "status": "blocked",
                        "reason": "Command not allowed for safety reasons"
                    })
                    continue
                
                # Execute command
                result = await self._execute_safe_command(command)
                
                # Check expected output if provided
                if i < len(expected_outputs):
                    expected = expected_outputs[i]
                    if self._check_output_match(result.get("stdout", ""), expected):
                        result["output_validation"] = "passed"
                    else:
                        result["output_validation"] = "failed"
                        result["expected_output"] = expected
                
                command_results.append(result)
                
            except Exception as e:
                command_results.append({
                    "command": command,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "scenario_name": scenario_name,
            "commands_executed": len(commands),
            "command_results": command_results,
            "status": "completed"
        }
        
    async def _validate_individual_hook(self, hook_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate execution of an individual hook."""
        hook_name = hook_config.get("name", "Unknown")
        hook_type = hook_config.get("type", "unknown")
        
        logger.info(f"Validating hook: {hook_name} (type: {hook_type})")
        
        validation_result = {
            "hook_name": hook_name,
            "hook_type": hook_type,
            "tests": []
        }
        
        if hook_type == "script":
            # Test script hook execution
            script_command = hook_config.get("command", [])
            if script_command:
                try:
                    # Create a test environment
                    test_env = {
                        "CODEX_EVENT_TYPE": "test",
                        "CODEX_SESSION_ID": "test-session-123",
                        "CODEX_TIMESTAMP": datetime.now().isoformat()
                    }
                    
                    # Execute script with test environment
                    result = await self._execute_safe_command(script_command, env=test_env)
                    validation_result["tests"].append({
                        "test": "Script execution",
                        "status": "passed" if result.get("return_code") == 0 else "failed",
                        "result": result
                    })
                    
                except Exception as e:
                    validation_result["tests"].append({
                        "test": "Script execution",
                        "status": "error",
                        "error": str(e)
                    })
        
        elif hook_type == "webhook":
            # Test webhook accessibility
            webhook_url = hook_config.get("url")
            if webhook_url:
                try:
                    # Use curl to test webhook
                    curl_command = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", webhook_url]
                    result = await self._execute_safe_command(curl_command)
                    
                    http_code = result.get("stdout", "").strip()
                    validation_result["tests"].append({
                        "test": "Webhook accessibility",
                        "status": "passed" if http_code.startswith("2") else "warning",
                        "http_code": http_code,
                        "result": result
                    })
                    
                except Exception as e:
                    validation_result["tests"].append({
                        "test": "Webhook accessibility",
                        "status": "error",
                        "error": str(e)
                    })
        
        validation_result["overall_status"] = self._determine_overall_status(validation_result["tests"])
        return validation_result
        
    async def _get_system_information(self) -> Dict[str, Any]:
        """Get basic system information."""
        system_info = {}
        
        # Get OS information
        try:
            result = await self._execute_safe_command(["uname", "-a"])
            system_info["os_info"] = result.get("stdout", "").strip()
        except Exception as e:
            system_info["os_info_error"] = str(e)
        
        # Get Python version
        try:
            result = await self._execute_safe_command(["python3", "--version"])
            system_info["python_version"] = result.get("stdout", "").strip()
        except Exception as e:
            system_info["python_version_error"] = str(e)
        
        # Get Node.js version
        try:
            result = await self._execute_safe_command(["node", "--version"])
            system_info["node_version"] = result.get("stdout", "").strip()
        except Exception as e:
            system_info["node_version_error"] = str(e)
        
        # Get available memory
        try:
            result = await self._execute_safe_command(["free", "-h"])
            system_info["memory_info"] = result.get("stdout", "").strip()
        except Exception as e:
            system_info["memory_info_error"] = str(e)
        
        # Get disk space
        try:
            result = await self._execute_safe_command(["df", "-h", "."])
            system_info["disk_info"] = result.get("stdout", "").strip()
        except Exception as e:
            system_info["disk_info_error"] = str(e)
        
        return system_info
        
    async def _test_dependency(self, dependency: Dict[str, Any]) -> Dict[str, Any]:
        """Test if a dependency is available."""
        dep_name = dependency.get("name", "Unknown")
        dep_command = dependency.get("command", dep_name)
        dep_version_flag = dependency.get("version_flag", "--version")
        
        try:
            # Test if command exists
            which_result = await self._execute_safe_command(["which", dep_command])
            if which_result.get("return_code") != 0:
                return {
                    "test": f"Dependency: {dep_name}",
                    "status": "failed",
                    "error": f"Command '{dep_command}' not found"
                }
            
            # Get version information
            version_result = await self._execute_safe_command([dep_command, dep_version_flag])
            
            return {
                "test": f"Dependency: {dep_name}",
                "status": "passed",
                "command_path": which_result.get("stdout", "").strip(),
                "version_info": version_result.get("stdout", "").strip()
            }
            
        except Exception as e:
            return {
                "test": f"Dependency: {dep_name}",
                "status": "error",
                "error": str(e)
            }
            
    async def _test_file_permissions(self, file_check: Dict[str, Any]) -> Dict[str, Any]:
        """Test file permissions."""
        file_path = file_check.get("path")
        expected_permissions = file_check.get("permissions")
        
        try:
            # Check if file exists
            result = await self._execute_safe_command(["stat", "-c", "%a %n", file_path])
            
            if result.get("return_code") != 0:
                return {
                    "test": f"File permissions: {file_path}",
                    "status": "failed",
                    "error": "File not found"
                }
            
            # Parse permissions
            output = result.get("stdout", "").strip()
            actual_permissions = output.split()[0] if output else "unknown"
            
            status = "passed" if actual_permissions == expected_permissions else "warning"
            
            return {
                "test": f"File permissions: {file_path}",
                "status": status,
                "actual_permissions": actual_permissions,
                "expected_permissions": expected_permissions
            }
            
        except Exception as e:
            return {
                "test": f"File permissions: {file_path}",
                "status": "error",
                "error": str(e)
            }
            
    async def _test_network_connectivity(self, network_test: Dict[str, Any]) -> Dict[str, Any]:
        """Test network connectivity."""
        host = network_test.get("host")
        port = network_test.get("port")
        
        try:
            if port:
                # Test specific port connectivity
                result = await self._execute_safe_command(["nc", "-z", "-v", host, str(port)])
            else:
                # Test basic ping connectivity
                result = await self._execute_safe_command(["ping", "-c", "1", host])
            
            status = "passed" if result.get("return_code") == 0 else "failed"
            
            return {
                "test": f"Network connectivity: {host}" + (f":{port}" if port else ""),
                "status": status,
                "result": result
            }
            
        except Exception as e:
            return {
                "test": f"Network connectivity: {host}" + (f":{port}" if port else ""),
                "status": "error",
                "error": str(e)
            }
            
    async def _test_environment_variable(self, env_var: Dict[str, Any]) -> Dict[str, Any]:
        """Test environment variable."""
        var_name = env_var.get("name")
        required = env_var.get("required", False)
        
        try:
            value = os.getenv(var_name)
            
            if required and not value:
                return {
                    "test": f"Environment variable: {var_name}",
                    "status": "failed",
                    "error": "Required environment variable not set"
                }
            
            return {
                "test": f"Environment variable: {var_name}",
                "status": "passed",
                "value": value if value else "not set",
                "is_set": bool(value)
            }
            
        except Exception as e:
            return {
                "test": f"Environment variable: {var_name}",
                "status": "error",
                "error": str(e)
            }
            
    async def _execute_performance_benchmark(self, benchmark_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a performance benchmark."""
        benchmark_name = benchmark_config.get("name", "Unknown")
        command = benchmark_config.get("command", [])
        iterations = benchmark_config.get("iterations", 1)
        
        logger.info(f"Executing performance benchmark: {benchmark_name}")
        
        execution_times = []
        
        for i in range(iterations):
            try:
                start_time = datetime.now()
                result = await self._execute_safe_command(command)
                end_time = datetime.now()
                
                execution_time = (end_time - start_time).total_seconds()
                execution_times.append(execution_time)
                
            except Exception as e:
                return {
                    "benchmark_name": benchmark_name,
                    "status": "error",
                    "error": str(e)
                }
        
        # Calculate statistics
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        
        return {
            "benchmark_name": benchmark_name,
            "status": "completed",
            "iterations": iterations,
            "execution_times": execution_times,
            "average_time_seconds": avg_time,
            "min_time_seconds": min_time,
            "max_time_seconds": max_time
        }
        
    async def _execute_safe_command(self, command: Union[str, List[str]], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute a command safely with proper validation."""
        # Convert string command to list
        if isinstance(command, str):
            command = shlex.split(command)
        
        # Validate command safety
        if not self._is_command_safe(command):
            raise ValueError(f"Command not allowed: {command[0] if command else 'empty'}")
        
        # Record command in history
        self.command_history.append({
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "env": env
        })
        
        try:
            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=exec_env,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            return {
                "command": command,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "timestamp": datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            return {
                "command": command,
                "return_code": -1,
                "error": "Command timed out",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "command": command,
                "return_code": -1,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    def _is_command_safe(self, command: List[str]) -> bool:
        """Check if a command is safe to execute."""
        if not command:
            return False
        
        base_command = command[0].split('/')[-1]  # Get just the command name
        
        # Check if command is explicitly blocked
        if base_command in self.blocked_commands:
            return False
        
        # Check if command is in allowed list
        if base_command in self.allowed_commands:
            return True
        
        # Allow relative paths to scripts in current directory
        if command[0].startswith('./') and not '..' in command[0]:
            return True
        
        # Block everything else by default
        return False
        
    def _check_output_match(self, actual_output: str, expected_pattern: str) -> bool:
        """Check if actual output matches expected pattern."""
        import re
        
        # Simple pattern matching - can be enhanced
        if expected_pattern.startswith("regex:"):
            pattern = expected_pattern[6:]
            return bool(re.search(pattern, actual_output))
        elif expected_pattern.startswith("contains:"):
            substring = expected_pattern[9:]
            return substring in actual_output
        else:
            # Exact match
            return actual_output.strip() == expected_pattern.strip()
            
    def _determine_overall_status(self, results: List[Dict[str, Any]]) -> str:
        """Determine overall status from individual results."""
        if not results:
            return "unknown"
        
        statuses = [result.get("status", "unknown") for result in results]
        
        if "error" in statuses or "failed" in statuses:
            return "failed"
        elif "warning" in statuses:
            return "warning"
        elif all(status == "passed" for status in statuses):
            return "passed"
        else:
            return "completed"
            
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self.execution_results.copy()
        
    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return self.command_history.copy()
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("ComputerTerminal agent cleanup completed")


# Example usage and testing
async def test_computer_terminal_agent():
    """Test the ComputerTerminal agent."""
    # Create ComputerTerminal agent (no model client needed for basic testing)
    terminal = CodexHooksComputerTerminalAgent()
    
    # Test CLI integration scenarios
    cli_scenarios = [
        {
            "name": "Basic system check",
            "commands": ["pwd", "ls -la", "whoami"],
            "expected_outputs": ["regex:.*", "contains:total", "regex:\\w+"]
        },
        {
            "name": "Python availability",
            "commands": ["python3 --version", "which python3"],
            "expected_outputs": ["contains:Python", "contains:python3"]
        }
    ]
    
    cli_result = await terminal.test_codex_cli_integration(cli_scenarios)
    print(f"CLI integration test: {cli_result['test_id']}")
    
    # Test system requirements
    requirements = {
        "dependencies": [
            {"name": "python3", "command": "python3"},
            {"name": "node", "command": "node"},
            {"name": "git", "command": "git"}
        ],
        "environment_variables": [
            {"name": "HOME", "required": True},
            {"name": "PATH", "required": True}
        ]
    }
    
    system_result = await terminal.test_system_requirements(requirements)
    print(f"System requirements test: {system_result['system_test_id']}")
    
    # Test hook validation
    hook_configs = [
        {
            "name": "test-script-hook",
            "type": "script",
            "command": ["echo", "Test hook executed"]
        }
    ]
    
    hook_result = await terminal.validate_hook_execution(hook_configs)
    print(f"Hook validation test: {hook_result['validation_id']}")
    
    # Cleanup
    await terminal.cleanup()


if __name__ == "__main__":
    asyncio.run(test_computer_terminal_agent())
