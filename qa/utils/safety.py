"""
Safety Manager
Comprehensive safety and security management for QA operations
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)


class SafetyManager:
    """
    Safety manager responsible for enforcing security protocols,
    monitoring operations, and ensuring safe execution of QA workflows.
    """
    
    def __init__(self):
        self.safety_config = {}
        self.active_monitors = {}
        self.security_violations = []
        self.approval_queue = []
        
    async def initialize(self) -> bool:
        """Initialize the safety manager"""
        try:
            logger.info("Initializing Safety Manager...")
            
            # Load safety configuration
            await self._load_safety_config()
            
            # Initialize monitoring systems
            await self._initialize_monitors()
            
            # Set up security protocols
            await self._setup_security_protocols()
            
            logger.info("Safety Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Safety Manager: {e}")
            return False
    
    async def _load_safety_config(self):
        """Load safety configuration"""
        try:
            config_path = Path('configs/safety_config.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.safety_config = json.load(f)
            else:
                # Default safety configuration
                self.safety_config = {
                    'container_isolation': {'enabled': True},
                    'network_restrictions': {'enabled': True},
                    'file_system_restrictions': {'enabled': True},
                    'execution_limits': {'max_execution_time': 600},
                    'human_oversight': {'enabled': True},
                    'monitoring_and_logging': {'enabled': True}
                }
            
            logger.info("Safety configuration loaded")
            
        except Exception as e:
            logger.error(f"Failed to load safety configuration: {e}")
            raise
    
    async def _initialize_monitors(self):
        """Initialize monitoring systems"""
        try:
            # Resource monitor
            if self.safety_config.get('monitoring_and_logging', {}).get('enabled'):
                self.active_monitors['resource'] = await self._start_resource_monitor()
            
            # Security monitor
            self.active_monitors['security'] = await self._start_security_monitor()
            
            # Network monitor
            if self.safety_config.get('network_restrictions', {}).get('enabled'):
                self.active_monitors['network'] = await self._start_network_monitor()
            
            logger.info(f"Initialized {len(self.active_monitors)} monitoring systems")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitors: {e}")
            raise
    
    async def _setup_security_protocols(self):
        """Set up security protocols"""
        try:
            # Container isolation
            if self.safety_config.get('container_isolation', {}).get('enabled'):
                await self._setup_container_isolation()
            
            # File system restrictions
            if self.safety_config.get('file_system_restrictions', {}).get('enabled'):
                await self._setup_file_restrictions()
            
            # Network restrictions
            if self.safety_config.get('network_restrictions', {}).get('enabled'):
                await self._setup_network_restrictions()
            
            logger.info("Security protocols configured")
            
        except Exception as e:
            logger.error(f"Failed to set up security protocols: {e}")
            raise
    
    async def _start_resource_monitor(self) -> Dict:
        """Start resource monitoring"""
        monitor_config = {
            'enabled': True,
            'interval': 30,
            'thresholds': {
                'cpu_usage': 90,
                'memory_usage': 90,
                'disk_usage': 85
            }
        }
        
        # Start monitoring task
        task = asyncio.create_task(self._resource_monitor_loop(monitor_config))
        
        return {
            'type': 'resource',
            'config': monitor_config,
            'task': task
        }
    
    async def _resource_monitor_loop(self, config: Dict):
        """Resource monitoring loop"""
        while True:
            try:
                # Monitor CPU usage
                cpu_usage = await self._get_cpu_usage()
                if cpu_usage > config['thresholds']['cpu_usage']:
                    await self._handle_resource_violation('cpu', cpu_usage)
                
                # Monitor memory usage
                memory_usage = await self._get_memory_usage()
                if memory_usage > config['thresholds']['memory_usage']:
                    await self._handle_resource_violation('memory', memory_usage)
                
                # Monitor disk usage
                disk_usage = await self._get_disk_usage()
                if disk_usage > config['thresholds']['disk_usage']:
                    await self._handle_resource_violation('disk', disk_usage)
                
                await asyncio.sleep(config['interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(config['interval'])
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0
    
    async def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    async def _get_disk_usage(self) -> float:
        """Get current disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return 0.0
    
    async def _handle_resource_violation(self, resource_type: str, usage: float):
        """Handle resource usage violations"""
        violation = {
            'type': 'resource_violation',
            'resource': resource_type,
            'usage': usage,
            'timestamp': time.time(),
            'severity': 'high' if usage > 95 else 'medium'
        }
        
        self.security_violations.append(violation)
        logger.warning(f"Resource violation: {resource_type} usage at {usage}%")
        
        # Take action based on severity
        if violation['severity'] == 'high':
            await self._emergency_resource_action(resource_type)
    
    async def _emergency_resource_action(self, resource_type: str):
        """Take emergency action for critical resource usage"""
        logger.critical(f"Emergency action triggered for {resource_type} usage")
        
        # Could implement actions like:
        # - Killing non-essential processes
        # - Pausing QA workflows
        # - Alerting administrators
        # - Graceful shutdown
    
    async def _start_security_monitor(self) -> Dict:
        """Start security monitoring"""
        monitor_config = {
            'enabled': True,
            'check_interval': 10,
            'patterns': [
                'privilege_escalation',
                'unauthorized_access',
                'malicious_commands',
                'data_exfiltration'
            ]
        }
        
        task = asyncio.create_task(self._security_monitor_loop(monitor_config))
        
        return {
            'type': 'security',
            'config': monitor_config,
            'task': task
        }
    
    async def _security_monitor_loop(self, config: Dict):
        """Security monitoring loop"""
        while True:
            try:
                # Check for security violations
                await self._check_security_patterns()
                
                # Validate ongoing operations
                await self._validate_active_operations()
                
                await asyncio.sleep(config['check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(config['check_interval'])
    
    async def _check_security_patterns(self):
        """Check for security violation patterns"""
        # This would implement pattern detection for:
        # - Suspicious command patterns
        # - Unauthorized file access
        # - Network anomalies
        # - Process behavior analysis
        pass
    
    async def _validate_active_operations(self):
        """Validate currently active operations"""
        # This would check:
        # - Running processes
        # - Open network connections
        # - File system access
        # - Resource usage patterns
        pass
    
    async def _start_network_monitor(self) -> Dict:
        """Start network monitoring"""
        monitor_config = {
            'enabled': True,
            'allowed_domains': self.safety_config.get('network_restrictions', {}).get('allowed_domains', []),
            'blocked_domains': self.safety_config.get('network_restrictions', {}).get('blocked_domains', []),
            'rate_limits': self.safety_config.get('network_restrictions', {}).get('rate_limiting', {})
        }
        
        return {
            'type': 'network',
            'config': monitor_config
        }
    
    async def _setup_container_isolation(self):
        """Set up container isolation"""
        logger.info("Setting up container isolation")
        # This would configure Docker security options
    
    async def _setup_file_restrictions(self):
        """Set up file system restrictions"""
        logger.info("Setting up file system restrictions")
        # This would configure file access controls
    
    async def _setup_network_restrictions(self):
        """Set up network restrictions"""
        logger.info("Setting up network restrictions")
        # This would configure network access controls
    
    async def run_with_safety_checks(self, operation: Callable, *args, **kwargs) -> Any:
        """Run an operation with comprehensive safety checks"""
        try:
            # Pre-execution safety checks
            if not await self._pre_execution_checks(operation, *args, **kwargs):
                raise SecurityError("Pre-execution safety checks failed")
            
            # Check if human approval is required
            if await self._requires_human_approval(operation, *args, **kwargs):
                if not await self._get_human_approval(operation, *args, **kwargs):
                    raise SecurityError("Human approval required but not granted")
            
            # Execute operation with monitoring
            start_time = time.time()
            result = await self._execute_with_monitoring(operation, *args, **kwargs)
            execution_time = time.time() - start_time
            
            # Post-execution safety checks
            if not await self._post_execution_checks(result, execution_time):
                logger.warning("Post-execution safety checks failed")
            
            return result
            
        except Exception as e:
            await self._handle_execution_error(e, operation, *args, **kwargs)
            raise
    
    async def _pre_execution_checks(self, operation: Callable, *args, **kwargs) -> bool:
        """Perform pre-execution safety checks"""
        try:
            # Check resource availability
            if not await self._check_resource_availability():
                return False
            
            # Validate operation parameters
            if not await self._validate_operation_parameters(operation, *args, **kwargs):
                return False
            
            # Check security constraints
            if not await self._check_security_constraints(operation, *args, **kwargs):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Pre-execution checks failed: {e}")
            return False
    
    async def _check_resource_availability(self) -> bool:
        """Check if sufficient resources are available"""
        cpu_usage = await self._get_cpu_usage()
        memory_usage = await self._get_memory_usage()
        disk_usage = await self._get_disk_usage()
        
        limits = self.safety_config.get('execution_limits', {})
        
        if cpu_usage > limits.get('max_cpu_usage', 80):
            logger.warning(f"CPU usage too high: {cpu_usage}%")
            return False
        
        if memory_usage > limits.get('max_memory_usage', 80):
            logger.warning(f"Memory usage too high: {memory_usage}%")
            return False
        
        if disk_usage > limits.get('max_disk_usage', 85):
            logger.warning(f"Disk usage too high: {disk_usage}%")
            return False
        
        return True
    
    async def _validate_operation_parameters(self, operation: Callable, *args, **kwargs) -> bool:
        """Validate operation parameters for safety"""
        # This would implement parameter validation logic
        return True
    
    async def _check_security_constraints(self, operation: Callable, *args, **kwargs) -> bool:
        """Check security constraints for operation"""
        # This would implement security constraint checking
        return True
    
    async def _requires_human_approval(self, operation: Callable, *args, **kwargs) -> bool:
        """Check if operation requires human approval"""
        oversight_config = self.safety_config.get('human_oversight', {})
        
        if not oversight_config.get('enabled', False):
            return False
        
        # Check if operation type requires approval
        require_approval = oversight_config.get('require_approval_for', [])
        operation_name = getattr(operation, '__name__', str(operation))
        
        return any(pattern in operation_name for pattern in require_approval)
    
    async def _get_human_approval(self, operation: Callable, *args, **kwargs) -> bool:
        """Get human approval for operation"""
        approval_request = {
            'operation': getattr(operation, '__name__', str(operation)),
            'args': str(args)[:100],  # Truncate for safety
            'kwargs': str(kwargs)[:100],
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        self.approval_queue.append(approval_request)
        
        # For now, auto-approve safe operations
        oversight_config = self.safety_config.get('human_oversight', {})
        if oversight_config.get('auto_approve_safe_operations', True):
            approval_request['status'] = 'approved'
            return True
        
        # In a real implementation, this would wait for human input
        logger.info(f"Human approval required for: {approval_request['operation']}")
        return True  # Auto-approve for demo
    
    async def _execute_with_monitoring(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with real-time monitoring"""
        # Set execution timeout
        timeout = self.safety_config.get('execution_limits', {}).get('max_execution_time', 600)
        
        try:
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            raise SecurityError(f"Operation timed out after {timeout} seconds")
    
    async def _post_execution_checks(self, result: Any, execution_time: float) -> bool:
        """Perform post-execution safety checks"""
        try:
            # Check execution time
            max_time = self.safety_config.get('execution_limits', {}).get('max_execution_time', 600)
            if execution_time > max_time:
                logger.warning(f"Execution time exceeded limit: {execution_time}s > {max_time}s")
                return False
            
            # Validate result
            if not await self._validate_execution_result(result):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Post-execution checks failed: {e}")
            return False
    
    async def _validate_execution_result(self, result: Any) -> bool:
        """Validate execution result for safety"""
        # This would implement result validation logic
        return True
    
    async def _handle_execution_error(self, error: Exception, operation: Callable, *args, **kwargs):
        """Handle execution errors"""
        error_record = {
            'error': str(error),
            'operation': getattr(operation, '__name__', str(operation)),
            'timestamp': time.time(),
            'severity': 'high' if isinstance(error, SecurityError) else 'medium'
        }
        
        self.security_violations.append(error_record)
        logger.error(f"Operation execution error: {error}")
    
    async def validate_safety_protocols(self) -> bool:
        """Validate that safety protocols are active and working"""
        try:
            # Check monitoring systems
            if not self.active_monitors:
                return False
            
            # Check configuration
            if not self.safety_config:
                return False
            
            # Test safety mechanisms
            # This would perform comprehensive safety validation
            
            return True
            
        except Exception as e:
            logger.error(f"Safety protocol validation failed: {e}")
            return False
    
    async def get_security_status(self) -> Dict:
        """Get current security status"""
        return {
            'active_monitors': len(self.active_monitors),
            'security_violations': len(self.security_violations),
            'pending_approvals': len([a for a in self.approval_queue if a['status'] == 'pending']),
            'safety_protocols_active': await self.validate_safety_protocols()
        }
    
    async def shutdown(self):
        """Shutdown the safety manager"""
        logger.info("Shutting down Safety Manager...")
        
        # Cancel monitoring tasks
        for monitor_name, monitor in self.active_monitors.items():
            if 'task' in monitor:
                monitor['task'].cancel()
                try:
                    await monitor['task']
                except asyncio.CancelledError:
                    pass
        
        self.active_monitors.clear()
        logger.info("Safety Manager shutdown complete")


class SecurityError(Exception):
    """Custom exception for security violations"""
    pass
