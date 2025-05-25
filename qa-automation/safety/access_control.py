#!/usr/bin/env python3
"""
Access Control Manager for Magentic-One QA Automation

This module provides access control, security policies, and permission
management for the QA automation system.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import uuid
import hashlib
import secrets
from enum import Enum

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for access control."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class SecurityPolicy:
    """Represents a security policy."""
    
    def __init__(self, 
                 policy_id: str,
                 name: str,
                 description: str,
                 rules: Dict[str, Any],
                 enabled: bool = True):
        self.policy_id = policy_id
        self.name = name
        self.description = description
        self.rules = rules
        self.enabled = enabled
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class AccessControlManager:
    """
    Access Control Manager for QA automation system.
    
    Provides comprehensive access control, security policies,
    and permission management for agents and users.
    """
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "qa-automation/safety/access_control.json"
        self.policies = {}
        self.user_permissions = {}
        self.agent_permissions = {}
        self.access_logs = []
        
        # Security settings
        self.session_timeout = timedelta(hours=8)
        self.max_failed_attempts = 3
        self.lockout_duration = timedelta(minutes=30)
        
        # Storage
        self.access_control_dir = Path("qa-automation/access-control")
        self.access_control_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self._load_configuration()
        self._initialize_default_policies()
        
    async def authenticate_user(self, 
                              username: str, 
                              password: str,
                              session_id: str = None) -> Dict[str, Any]:
        """
        Authenticate a user for QA system access.
        
        Args:
            username: Username
            password: Password
            session_id: Optional session identifier
            
        Returns:
            Authentication result
        """
        
        # Check if user is locked out
        if self._is_user_locked_out(username):
            return {
                "success": False,
                "reason": "account_locked",
                "message": "Account is temporarily locked due to failed attempts"
            }
        
        # Validate credentials
        if not self._validate_credentials(username, password):
            self._record_failed_attempt(username)
            return {
                "success": False,
                "reason": "invalid_credentials",
                "message": "Invalid username or password"
            }
        
        # Create session
        if not session_id:
            session_id = self._generate_session_id()
            
        session_data = {
            "session_id": session_id,
            "username": username,
            "authenticated_at": datetime.now(),
            "expires_at": datetime.now() + self.session_timeout,
            "permissions": self.user_permissions.get(username, {})
        }
        
        # Log successful authentication
        await self._log_access_event("authentication", username, {
            "session_id": session_id,
            "success": True
        })
        
        return {
            "success": True,
            "session_data": session_data
        }
        
    async def authorize_agent_action(self, 
                                   agent_type: str,
                                   action: str,
                                   resource: str,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Authorize an agent action against security policies.
        
        Args:
            agent_type: Type of agent requesting authorization
            action: Action to be performed
            resource: Resource being accessed
            context: Additional context for authorization
            
        Returns:
            Authorization result
        """
        
        context = context or {}
        
        # Get agent permissions
        agent_perms = self.agent_permissions.get(agent_type, {})
        
        # Check basic permission
        if not self._has_permission(agent_perms, action, resource):
            await self._log_access_event("authorization_denied", agent_type, {
                "action": action,
                "resource": resource,
                "reason": "insufficient_permissions"
            })
            
            return {
                "authorized": False,
                "reason": "insufficient_permissions",
                "message": f"Agent {agent_type} lacks permission for {action} on {resource}"
            }
        
        # Apply security policies
        policy_result = await self._apply_security_policies(agent_type, action, resource, context)
        
        if not policy_result["allowed"]:
            await self._log_access_event("authorization_denied", agent_type, {
                "action": action,
                "resource": resource,
                "reason": "policy_violation",
                "policy": policy_result.get("violated_policy")
            })
            
            return {
                "authorized": False,
                "reason": "policy_violation",
                "message": policy_result.get("message", "Action violates security policy"),
                "violated_policy": policy_result.get("violated_policy")
            }
        
        # Log successful authorization
        await self._log_access_event("authorization_granted", agent_type, {
            "action": action,
            "resource": resource
        })
        
        return {
            "authorized": True,
            "permissions": agent_perms.get(resource, {}),
            "applied_policies": policy_result.get("applied_policies", [])
        }
        
    async def create_security_policy(self, 
                                   name: str,
                                   description: str,
                                   rules: Dict[str, Any]) -> SecurityPolicy:
        """
        Create a new security policy.
        
        Args:
            name: Policy name
            description: Policy description
            rules: Policy rules
            
        Returns:
            Created security policy
        """
        
        policy_id = f"policy-{uuid.uuid4().hex[:8]}"
        
        policy = SecurityPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            rules=rules
        )
        
        self.policies[policy_id] = policy
        
        # Save policy
        await self._save_security_policy(policy)
        
        logger.info(f"Created security policy: {name} ({policy_id})")
        return policy
        
    async def update_agent_permissions(self, 
                                     agent_type: str,
                                     permissions: Dict[str, Any]):
        """
        Update permissions for an agent type.
        
        Args:
            agent_type: Agent type
            permissions: New permissions configuration
        """
        
        self.agent_permissions[agent_type] = permissions
        
        # Save configuration
        await self._save_configuration()
        
        logger.info(f"Updated permissions for agent: {agent_type}")
        
    def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials."""
        
        # In a real implementation, this would check against a secure user store
        # For now, we'll use a simple hardcoded check
        default_users = {
            "qa_admin": "secure_password_123",
            "qa_operator": "operator_pass_456"
        }
        
        return default_users.get(username) == password
        
    def _is_user_locked_out(self, username: str) -> bool:
        """Check if user is locked out due to failed attempts."""
        
        # Check recent failed attempts
        recent_failures = [
            log for log in self.access_logs
            if (log.get("event_type") == "authentication" and
                log.get("username") == username and
                not log.get("data", {}).get("success", True) and
                datetime.fromisoformat(log.get("timestamp")) > 
                datetime.now() - self.lockout_duration)
        ]
        
        return len(recent_failures) >= self.max_failed_attempts
        
    def _record_failed_attempt(self, username: str):
        """Record a failed authentication attempt."""
        
        asyncio.create_task(self._log_access_event("authentication", username, {
            "success": False,
            "reason": "invalid_credentials"
        }))
        
    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)
        
    def _has_permission(self, 
                       permissions: Dict[str, Any], 
                       action: str, 
                       resource: str) -> bool:
        """Check if permissions allow an action on a resource."""
        
        # Check resource-specific permissions
        resource_perms = permissions.get(resource, {})
        if action in resource_perms:
            return resource_perms[action]
            
        # Check wildcard permissions
        wildcard_perms = permissions.get("*", {})
        if action in wildcard_perms:
            return wildcard_perms[action]
            
        # Check permission levels
        permission_level = resource_perms.get("level", PermissionLevel.NONE)
        if isinstance(permission_level, str):
            permission_level = PermissionLevel(permission_level)
            
        # Map actions to required permission levels
        action_requirements = {
            "read": PermissionLevel.READ,
            "write": PermissionLevel.WRITE,
            "execute": PermissionLevel.EXECUTE,
            "delete": PermissionLevel.ADMIN,
            "modify": PermissionLevel.WRITE
        }
        
        required_level = action_requirements.get(action, PermissionLevel.ADMIN)
        
        # Check if current level meets requirement
        level_hierarchy = [
            PermissionLevel.NONE,
            PermissionLevel.READ,
            PermissionLevel.WRITE,
            PermissionLevel.EXECUTE,
            PermissionLevel.ADMIN
        ]
        
        current_index = level_hierarchy.index(permission_level)
        required_index = level_hierarchy.index(required_level)
        
        return current_index >= required_index
