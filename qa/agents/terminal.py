"""
Terminal Agent
Specialized agent for CLI automation and command execution
"""

import asyncio
import logging
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class TerminalAgent:
    """
    ComputerTerminal agent responsible for CLI automation, command execution,
    and system interaction for the QA system.
    """
    
    def __init__(self, config: Dict, client):
        self.config = config
        self.client = client
        self.restrictions = config.get('restrictions', {})
        self.capabilities = config.get('capabilities', [])
        
        # Execution restrictions
        self.sandbox_mode = self.restrictions.get('sandbox_mode', True)
        self.allowed_commands = set(self.restrictions.get('allowed_commands', []))
        self.forbidden_commands = set(self.restrictions.get('forbidden_commands', []))
        self.max_execution_time = self.restrictions.get('max_execution_time', 60)
        self.working_directory = Path(self.restrictions.get('working_directory', '/workspace/qa/tmp'))
        self.environment_isolation = self.restrictions.get('environment_isolation', True)
        
        # Execution state
        self.command_history = []
        self.active_processes = {}
        self.environment_vars = {}
        
    async def initialize(self) -> bool:
        """Initialize the Terminal agent"""
        try:
            logger.info("Initializing Terminal agent...")
            
            # Validate configuration
            if not await self._validate_config():
                return False
            
            # Set up working directory
            if not await self._setup_working_directory():
                return False
            
            # Test command execution
            if not await self._test_command_execution():
                return False
            
            # Set up environment
            await self._setup_environment()
            
            logger.info("Terminal agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Terminal agent: {e}")
            return False
    
    async def _validate_config(self) -> bool:
        """Validate agent configuration"""
        required_capabilities = ['command_execution', 'cli_automation']
        missing_capabilities = [cap for cap in required_capabilities if cap not in self.capabilities]
        
        if missing_capabilities:
            logger.error(f"Missing required capabilities: {missing_capabilities}")
            return False
        
        if not self.allowed_commands:
            logger.warning("No allowed commands configured - agent will be very restricted")
        
        return True
    
    async def _setup_working_directory(self) -> bool:
        """Set up and validate working directory"""
        try:
            self.working_directory.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = self.working_directory / 'terminal_test.txt'
            test_file.write_text('test')
            test_file.unlink()
            
            logger.info(f"Working directory set up: {self.working_directory}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up working directory: {e}")
            return False
    
    async def _test_command_execution(self) -> bool:
        """Test basic command execution"""
        try:
            # Test a safe command
            result = await self._execute_command_internal(['echo', 'test'], timeout=5)
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"Command execution test failed: {e}")
            return False
    
    async def _setup_environment(self):
        """Set up isolated environment variables"""
        if self.environment_isolation:
            # Set up minimal environment
            self.environment_vars = {
                'PATH': '/usr/local/bin:/usr/bin:/bin',
                'HOME': str(self.working_directory),
                'USER': 'qa-agent',
                'SHELL': '/bin/bash',
                'TERM': 'xterm',
                'PWD': str(self.working_directory)
            }
        else:
            # Use current environment
            self.environment_vars = os.environ.copy()
    
    def _validate_command(self, command: List[str]) -> Tuple[bool, str]:
        """Validate command against security restrictions"""
        if not command:
            return False, "Empty command"
        
        base_command = command[0]
        
        # Check forbidden commands
        if base_command in self.forbidden_commands:
            return False, f"Command '{base_command}' is forbidden"
        
        # Check allowed commands (if whitelist is configured)
        if self.allowed_commands and base_command not in self.allowed_commands:
            return False, f"Command '{base_command}' is not in allowed list"
        
        # Check for dangerous patterns in arguments
        full_command = ' '.join(command)
        dangerous_patterns = [
            '&&', '||', ';', '|', '>', '>>', '<', '`', '$(',
            'rm -rf', 'sudo', 'su -', 'chmod +s', 'chown root'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in full_command:
                return False, f"Dangerous pattern detected: {pattern}"
        
        return True, "Command validation passed"
    
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> Dict:
        """Execute a shell command with safety checks"""
        try:
            logger.info(f"Executing command: {command}")
            
            # Parse command
            try:
                command_parts = shlex.split(command)
            except ValueError as e:
                return {'success': False, 'error': f'Command parsing failed: {e}'}
            
            # Validate command
            is_valid, validation_message = self._validate_command(command_parts)
            if not is_valid:
                return {'success': False, 'error': validation_message}
            
            # Execute command
            execution_timeout = timeout or self.max_execution_time
            result = await self._execute_command_internal(command_parts, execution_timeout)
            
            # Log command execution
            self.command_history.append({
                'command': command,
                'timestamp': time.time(),
                'success': result.get('success', False),
                'exit_code': result.get('exit_code', -1),
                'execution_time': result.get('execution_time', 0)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_command_internal(self, command_parts: List[str], timeout: int) -> Dict:
        """Internal command execution with proper isolation"""
        start_time = time.time()
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                env=self.environment_vars
            )
            
            # Store active process
            process_id = id(process)
            self.active_processes[process_id] = process
            
            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                return {
                    'success': process.returncode == 0,
                    'exit_code': process.returncode,
                    'stdout': stdout.decode('utf-8', errors='replace'),
                    'stderr': stderr.decode('utf-8', errors='replace'),
                    'execution_time': execution_time,
                    'command': ' '.join(command_parts)
                }
                
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                
                return {
                    'success': False,
                    'error': f'Command timed out after {timeout} seconds',
                    'exit_code': -1,
                    'execution_time': timeout,
                    'command': ' '.join(command_parts)
                }
                
            finally:
                # Remove from active processes
                self.active_processes.pop(process_id, None)
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'error': str(e),
                'exit_code': -1,
                'execution_time': execution_time,
                'command': ' '.join(command_parts)
            }
    
    async def execute_script(self, script_path: str, args: List[str] = None) -> Dict:
        """Execute a script file with arguments"""
        try:
            script_file = Path(script_path)
            
            # Validate script file
            if not script_file.exists():
                return {'success': False, 'error': f'Script file not found: {script_path}'}
            
            if not script_file.is_file():
                return {'success': False, 'error': f'Path is not a file: {script_path}'}
            
            # Check if script is executable
            if not os.access(script_file, os.X_OK):
                return {'success': False, 'error': f'Script is not executable: {script_path}'}
            
            # Build command
            command_parts = [str(script_file)]
            if args:
                command_parts.extend(args)
            
            # Execute script
            return await self._execute_command_internal(command_parts, self.max_execution_time)
            
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_codex_cli(self, codex_command: str) -> Dict:
        """Test Codex CLI with specific command"""
        try:
            logger.info(f"Testing Codex CLI: {codex_command}")
            
            # Build full command
            full_command = f"codex {codex_command}"
            
            # Execute command
            result = await self.execute_command(full_command, timeout=120)
            
            # Additional Codex-specific analysis
            if result.get('success'):
                result['codex_analysis'] = await self._analyze_codex_output(
                    result.get('stdout', ''),
                    result.get('stderr', '')
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Codex CLI test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _analyze_codex_output(self, stdout: str, stderr: str) -> Dict:
        """Analyze Codex CLI output for specific patterns"""
        analysis = {
            'hooks_executed': 0,
            'errors_detected': 0,
            'warnings_detected': 0,
            'execution_patterns': []
        }
        
        # Look for hook execution patterns
        hook_patterns = [
            r'Hook\s+(\w+)\s+executed',
            r'Executing\s+hook:\s+(\w+)',
            r'Hook\s+(\w+)\s+completed'
        ]
        
        for pattern in hook_patterns:
            import re
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            analysis['hooks_executed'] += len(matches)
            analysis['execution_patterns'].extend(matches)
        
        # Look for errors and warnings
        if 'error' in stdout.lower() or 'error' in stderr.lower():
            analysis['errors_detected'] += stdout.lower().count('error') + stderr.lower().count('error')
        
        if 'warning' in stdout.lower() or 'warning' in stderr.lower():
            analysis['warnings_detected'] += stdout.lower().count('warning') + stderr.lower().count('warning')
        
        return analysis
    
    async def monitor_system_resources(self, duration: int = 60) -> Dict:
        """Monitor system resources during test execution"""
        try:
            logger.info(f"Monitoring system resources for {duration} seconds")
            
            start_time = time.time()
            measurements = []
            
            while time.time() - start_time < duration:
                # Get CPU and memory usage
                cpu_result = await self.execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
                memory_result = await self.execute_command("free | grep Mem | awk '{printf \"%.2f\", $3/$2 * 100.0}'")
                
                measurement = {
                    'timestamp': time.time(),
                    'cpu_usage': float(cpu_result.get('stdout', '0').strip()) if cpu_result.get('success') else 0,
                    'memory_usage': float(memory_result.get('stdout', '0').strip()) if memory_result.get('success') else 0
                }
                
                measurements.append(measurement)
                await asyncio.sleep(5)  # Sample every 5 seconds
            
            # Calculate statistics
            if measurements:
                cpu_values = [m['cpu_usage'] for m in measurements]
                memory_values = [m['memory_usage'] for m in measurements]
                
                stats = {
                    'duration': duration,
                    'samples': len(measurements),
                    'cpu_stats': {
                        'average': sum(cpu_values) / len(cpu_values),
                        'max': max(cpu_values),
                        'min': min(cpu_values)
                    },
                    'memory_stats': {
                        'average': sum(memory_values) / len(memory_values),
                        'max': max(memory_values),
                        'min': min(memory_values)
                    },
                    'measurements': measurements
                }
            else:
                stats = {'error': 'No measurements collected'}
            
            return {'success': True, 'stats': stats}
            
        except Exception as e:
            logger.error(f"Resource monitoring failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def setup_test_environment(self, test_config: Dict) -> Dict:
        """Set up test environment for hook testing"""
        try:
            logger.info("Setting up test environment")
            
            setup_commands = [
                # Create test directories
                "mkdir -p test-hooks test-scripts test-data",
                
                # Set up test configuration
                "echo '[hooks]' > test-hooks.toml",
                
                # Create test scripts
                "echo '#!/bin/bash\necho \"Test hook executed\"' > test-scripts/test-hook.sh",
                "chmod +x test-scripts/test-hook.sh",
                
                # Verify setup
                "ls -la test-*"
            ]
            
            results = []
            for command in setup_commands:
                result = await self.execute_command(command)
                results.append(result)
                
                if not result.get('success'):
                    return {
                        'success': False,
                        'error': f'Setup command failed: {command}',
                        'results': results
                    }
            
            return {
                'success': True,
                'message': 'Test environment set up successfully',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Test environment setup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cleanup_test_environment(self) -> Dict:
        """Clean up test environment"""
        try:
            logger.info("Cleaning up test environment")
            
            cleanup_commands = [
                "rm -rf test-hooks test-scripts test-data",
                "rm -f test-hooks.toml",
                "rm -f *.log *.tmp"
            ]
            
            results = []
            for command in cleanup_commands:
                result = await self.execute_command(command)
                results.append(result)
            
            return {
                'success': True,
                'message': 'Test environment cleaned up',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Test environment cleanup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_command_history(self) -> List[Dict]:
        """Get history of executed commands"""
        return self.command_history.copy()
    
    async def kill_active_processes(self):
        """Kill all active processes"""
        for process_id, process in self.active_processes.items():
            try:
                process.kill()
                await process.wait()
                logger.info(f"Killed process {process_id}")
            except Exception as e:
                logger.error(f"Failed to kill process {process_id}: {e}")
        
        self.active_processes.clear()
    
    async def shutdown(self):
        """Shutdown the Terminal agent"""
        logger.info("Shutting down Terminal agent...")
        
        # Kill active processes
        await self.kill_active_processes()
        
        # Clean up test environment
        await self.cleanup_test_environment()
        
        # Clear state
        self.command_history.clear()
        
        logger.info("Terminal agent shutdown complete")
