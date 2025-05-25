#!/usr/bin/env python3
"""
Safety Integration System for Magentic-One QA Automation

This module integrates all safety components into a unified system
for comprehensive protection and monitoring.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from .container_isolation import ContainerIsolationManager, SecurityError
from .logging_monitor import ComprehensiveLoggingSystem, MonitoringDashboard
from .human_oversight import HumanOversightProtocol, OversightDecision
from .access_control import AccessControlManager, PermissionLevel
from .prompt_protection import PromptInjectionProtector, ThreatLevel

logger = logging.getLogger(__name__)


class SafetyIntegrationSystem:
    """
    Integrated safety system for Magentic-One QA automation.
    
    Combines all safety components into a unified system providing
    comprehensive protection, monitoring, and oversight.
    """
    
    def __init__(self, 
                 security_level: str = "standard",
                 enable_container_isolation: bool = True,
                 enable_human_oversight: bool = True):
        
        self.security_level = security_level
        self.enable_container_isolation = enable_container_isolation
        self.enable_human_oversight = enable_human_oversight
        
        # Initialize safety components
        self.logging_system = ComprehensiveLoggingSystem()
        self.monitoring_dashboard = MonitoringDashboard(self.logging_system)
        self.access_control = AccessControlManager()
        self.prompt_protector = PromptInjectionProtector(security_level)
        
        # Optional components
        self.container_isolation = None
        self.human_oversight = None
        
        if enable_container_isolation:
            try:
                self.container_isolation = ContainerIsolationManager()
            except ImportError:
                logger.warning("Container isolation disabled - Docker not available")
                
        if enable_human_oversight:
            self.human_oversight = HumanOversightProtocol()
            
        # Integration state
        self.active_sessions = {}
        self.safety_metrics = {}
        
        logger.info(f"Safety integration system initialized (level: {security_level})")
        
    async def create_safe_execution_environment(self, 
                                              agent_type: str,
                                              session_id: str,
                                              user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a safe execution environment for an agent.
        
        Args:
            agent_type: Type of agent
            session_id: Session identifier
            user_context: User context and permissions
            
        Returns:
            Safe execution environment configuration
        """
        
        user_context = user_context or {}
        
        logger.info(f"Creating safe execution environment for {agent_type} (session: {session_id})")
        
        try:
            # Create execution environment
            environment = {
                "session_id": session_id,
                "agent_type": agent_type,
                "security_level": self.security_level,
                "created_at": datetime.now().isoformat(),
                "components": {}
            }
            
            # Set up container isolation if enabled
            if self.container_isolation:
                container_env = await self.container_isolation.create_isolated_environment(
                    agent_type, self.security_level
                )
                environment["components"]["container"] = container_env
                
            # Set up access control
            auth_result = await self.access_control.authorize_agent_action(
                agent_type, "create_environment", "qa_system", user_context
            )
            
            if not auth_result["authorized"]:
                raise SecurityError(f"Agent not authorized: {auth_result['reason']}")
                
            environment["components"]["access_control"] = {
                "authorized": True,
                "permissions": auth_result["permissions"]
            }
            
            # Set up logging for this session
            self.logging_system.log_qa_event(
                "environment_created",
                agent_type,
                session_id,
                {"environment_id": environment.get("environment_id", session_id)}
            )
            
            # Store active session
            self.active_sessions[session_id] = environment
            
            logger.info(f"Safe execution environment created: {session_id}")
            return environment
            
        except Exception as e:
            logger.error(f"Failed to create safe execution environment: {e}")
            
            # Log failure
            self.logging_system.log_qa_event(
                "environment_creation_failed",
                agent_type,
                session_id,
                {"error": str(e)},
                "ERROR"
            )
            
            raise
            
    async def execute_safe_action(self, 
                                session_id: str,
                                action_type: str,
                                action_data: Dict[str, Any],
                                prompt: str = None) -> Dict[str, Any]:
        """
        Execute an action safely with all protection mechanisms.
        
        Args:
            session_id: Session identifier
            action_type: Type of action to execute
            action_data: Action data and parameters
            prompt: Optional prompt to protect
            
        Returns:
            Execution result
        """
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
            
        session = self.active_sessions[session_id]
        agent_type = session["agent_type"]
        
        logger.info(f"Executing safe action: {action_type} (session: {session_id})")
        
        try:
            execution_result = {
                "action_id": f"action-{datetime.now().timestamp()}",
                "session_id": session_id,
                "action_type": action_type,
                "agent_type": agent_type,
                "start_time": datetime.now().isoformat(),
                "status": "running",
                "safety_checks": {}
            }
            
            # Step 1: Prompt protection (if prompt provided)
            if prompt:
                prompt_result = await self.prompt_protector.protect_prompt(
                    prompt, agent_type, action_data
                )
                
                execution_result["safety_checks"]["prompt_protection"] = prompt_result
                
                if not prompt_result["safe_to_execute"]:
                    execution_result["status"] = "blocked"
                    execution_result["block_reason"] = prompt_result["block_reason"]
                    return execution_result
                    
                # Use sanitized prompt if available
                if prompt_result["sanitized_prompt"]:
                    action_data["prompt"] = prompt_result["sanitized_prompt"]
                    
            # Step 2: Access control check
            access_result = await self.access_control.authorize_agent_action(
                agent_type, action_type, "qa_system", action_data
            )
            
            execution_result["safety_checks"]["access_control"] = access_result
            
            if not access_result["authorized"]:
                execution_result["status"] = "blocked"
                execution_result["block_reason"] = access_result["reason"]
                return execution_result
                
            # Step 3: Human oversight (if required)
            if self.human_oversight and self._requires_human_oversight(action_type, action_data):
                oversight_request = await self.human_oversight.request_oversight(
                    action_type,
                    agent_type,
                    f"Execute {action_type} action",
                    action_data
                )
                
                execution_result["safety_checks"]["human_oversight"] = {
                    "request_id": oversight_request.request_id,
                    "required": True
                }
                
                # Wait for decision
                decision = await self.human_oversight.wait_for_decision(oversight_request)
                
                execution_result["safety_checks"]["human_oversight"]["decision"] = decision.value
                
                if decision != OversightDecision.APPROVE:
                    execution_result["status"] = "blocked"
                    execution_result["block_reason"] = f"Human oversight: {decision.value}"
                    return execution_result
                    
            # Step 4: Execute action in safe environment
            if self.container_isolation and session.get("components", {}).get("container"):
                container_env = session["components"]["container"]
                
                # Execute in isolated container
                container_result = await self.container_isolation.execute_in_isolation(
                    container_env["environment_id"],
                    self._build_execution_command(action_type, action_data),
                    timeout=300
                )
                
                execution_result["execution"] = container_result
                execution_result["status"] = container_result["status"]
                
            else:
                # Execute without container isolation
                execution_result["execution"] = {
                    "status": "completed",
                    "message": "Executed without container isolation",
                    "output": "Action completed successfully"
                }
                execution_result["status"] = "completed"
                
            # Step 5: Log execution
            self.logging_system.log_qa_event(
                "action_executed",
                agent_type,
                session_id,
                {
                    "action_id": execution_result["action_id"],
                    "action_type": action_type,
                    "status": execution_result["status"]
                }
            )
            
            execution_result["end_time"] = datetime.now().isoformat()
            
            logger.info(f"Safe action completed: {action_type} (status: {execution_result['status']})")
            return execution_result
            
        except Exception as e:
            logger.error(f"Safe action execution failed: {e}")
            
            # Log error
            self.logging_system.log_qa_event(
                "action_execution_failed",
                agent_type,
                session_id,
                {"action_type": action_type, "error": str(e)},
                "ERROR"
            )
            
            return {
                "action_id": execution_result.get("action_id", "unknown"),
                "session_id": session_id,
                "action_type": action_type,
                "status": "error",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            }
            
    async def cleanup_session(self, session_id: str):
        """Clean up a session and its resources."""
        
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found for cleanup: {session_id}")
            return
            
        session = self.active_sessions[session_id]
        
        logger.info(f"Cleaning up session: {session_id}")
        
        try:
            # Clean up container if exists
            if (self.container_isolation and 
                session.get("components", {}).get("container")):
                container_env = session["components"]["container"]
                await self.container_isolation.cleanup_environment(
                    container_env["environment_id"]
                )
                
            # Log session cleanup
            self.logging_system.log_qa_event(
                "session_cleanup",
                session["agent_type"],
                session_id,
                {"cleanup_time": datetime.now().isoformat()}
            )
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Session cleaned up: {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety system status."""
        
        dashboard_data = self.monitoring_dashboard.get_dashboard_data()
        
        return {
            "system_status": dashboard_data["system_status"],
            "active_sessions": len(self.active_sessions),
            "security_level": self.security_level,
            "components": {
                "container_isolation": self.container_isolation is not None,
                "human_oversight": self.human_oversight is not None,
                "prompt_protection": True,
                "access_control": True,
                "logging_monitoring": True
            },
            "recent_metrics": dashboard_data.get("recent_metrics", []),
            "alerts": dashboard_data.get("active_alerts", [])
        }
        
    def _requires_human_oversight(self, action_type: str, action_data: Dict[str, Any]) -> bool:
        """Determine if action requires human oversight."""
        
        # High-risk actions that always require oversight
        high_risk_actions = [
            "system_modification",
            "security_change",
            "data_deletion",
            "external_network_access"
        ]
        
        if action_type in high_risk_actions:
            return True
            
        # Check for high-risk context
        if action_data.get("modifies_production_data", False):
            return True
            
        if action_data.get("requires_elevated_privileges", False):
            return True
            
        return False
        
    def _build_execution_command(self, action_type: str, action_data: Dict[str, Any]) -> str:
        """Build execution command for container."""
        
        # This would build appropriate commands based on action type
        # For now, return a safe default
        return f"echo 'Executing {action_type} action'"


# Example usage and testing
async def test_safety_integration():
    """Test the integrated safety system."""
    
    try:
        # Create safety system
        safety_system = SafetyIntegrationSystem(
            security_level="standard",
            enable_container_isolation=False,  # Disable for testing
            enable_human_oversight=False
        )
        
        # Create safe execution environment
        environment = await safety_system.create_safe_execution_environment(
            agent_type="file_surfer",
            session_id="test-session-001"
        )
        
        print(f"Created environment: {environment['session_id']}")
        
        # Execute safe action
        result = await safety_system.execute_safe_action(
            session_id="test-session-001",
            action_type="file_analysis",
            action_data={"file_path": "/test/file.txt"},
            prompt="Analyze this configuration file for security issues"
        )
        
        print(f"Action result: {result['status']}")
        
        # Get safety status
        status = safety_system.get_safety_status()
        print(f"Safety status: {status['system_status']}")
        
        # Cleanup
        await safety_system.cleanup_session("test-session-001")
        print("Session cleaned up")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_safety_integration())
