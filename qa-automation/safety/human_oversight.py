#!/usr/bin/env python3
"""
Human Oversight Protocol for Magentic-One QA Automation

This module provides human-in-the-loop validation and oversight
for critical QA automation decisions and actions.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import uuid
from enum import Enum
import threading
import queue

logger = logging.getLogger(__name__)


class OversightDecision(Enum):
    """Possible oversight decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ESCALATE = "escalate"
    PENDING = "pending"


class OversightRequest:
    """Represents a request for human oversight."""

    def __init__(self,
                 request_id: str,
                 request_type: str,
                 agent_type: str,
                 action_description: str,
                 risk_level: str,
                 context: Dict[str, Any],
                 timeout_minutes: int = 30):
        self.request_id = request_id
        self.request_type = request_type
        self.agent_type = agent_type
        self.action_description = action_description
        self.risk_level = risk_level
        self.context = context
        self.timeout_minutes = timeout_minutes
        self.created_at = datetime.now()
        self.decision = OversightDecision.PENDING
        self.decision_reason = ""
        self.decided_by = ""
        self.decided_at = None


class HumanOversightProtocol:
    """
    Human Oversight Protocol for QA automation system.

    Provides mechanisms for human validation of critical decisions,
    risk assessment, and intervention capabilities.
    """

    def __init__(self,
                 oversight_config: Dict[str, Any] = None,
                 notification_callback: Callable = None):
        self.oversight_config = oversight_config or self._default_oversight_config()
        self.notification_callback = notification_callback

        # Request management
        self.pending_requests = {}
        self.completed_requests = {}
        self.request_queue = queue.Queue()

        # Oversight rules
        self.oversight_rules = self._load_oversight_rules()

        # Storage
        self.oversight_dir = Path("qa-automation/oversight")
        self.oversight_dir.mkdir(exist_ok=True)

        # Start oversight processor
        self._start_oversight_processor()

    async def request_oversight(self,
                              request_type: str,
                              agent_type: str,
                              action_description: str,
                              context: Dict[str, Any],
                              timeout_minutes: int = 30) -> OversightRequest:
        """
        Request human oversight for a critical action.

        Args:
            request_type: Type of oversight request
            agent_type: Agent requesting oversight
            action_description: Description of the action requiring oversight
            context: Additional context for the decision
            timeout_minutes: Timeout for the oversight decision

        Returns:
            OversightRequest object
        """

        # Assess risk level
        risk_level = self._assess_risk_level(request_type, agent_type, context)

        # Create oversight request
        request_id = f"oversight-{uuid.uuid4().hex[:8]}"
        oversight_request = OversightRequest(
            request_id=request_id,
            request_type=request_type,
            agent_type=agent_type,
            action_description=action_description,
            risk_level=risk_level,
            context=context,
            timeout_minutes=timeout_minutes
        )

        # Check if oversight is required
        if not self._requires_oversight(oversight_request):
            # Auto-approve low-risk actions
            oversight_request.decision = OversightDecision.APPROVE
            oversight_request.decision_reason = "Auto-approved: Low risk"
            oversight_request.decided_by = "system"
            oversight_request.decided_at = datetime.now()

            logger.info(f"Auto-approved oversight request: {request_id}")
            return oversight_request

        # Add to pending requests
        self.pending_requests[request_id] = oversight_request

        # Save request
        await self._save_oversight_request(oversight_request)

        # Send notification
        await self._send_oversight_notification(oversight_request)

        logger.info(f"Oversight requested: {request_id} - {action_description}")
        return oversight_request

    async def provide_decision(self,
                             request_id: str,
                             decision: OversightDecision,
                             reason: str,
                             decided_by: str,
                             modifications: Dict[str, Any] = None) -> bool:
        """
        Provide a decision for an oversight request.

        Args:
            request_id: Request identifier
            decision: Oversight decision
            reason: Reason for the decision
            decided_by: Who made the decision
            modifications: Any modifications to the original request

        Returns:
            True if decision was recorded successfully
        """

        if request_id not in self.pending_requests:
            logger.error(f"Oversight request not found: {request_id}")
            return False

        oversight_request = self.pending_requests[request_id]

        # Update request with decision
        oversight_request.decision = decision
        oversight_request.decision_reason = reason
        oversight_request.decided_by = decided_by
        oversight_request.decided_at = datetime.now()

        if modifications:
            oversight_request.context["modifications"] = modifications

        # Move to completed requests
        self.completed_requests[request_id] = oversight_request
        del self.pending_requests[request_id]

        # Save decision
        await self._save_oversight_decision(oversight_request)

        # Log decision
        logger.info(f"Oversight decision: {request_id} - {decision.value} by {decided_by}")

        return True

    async def wait_for_decision(self,
                              oversight_request: OversightRequest,
                              check_interval: int = 5) -> OversightDecision:
        """
        Wait for a decision on an oversight request.

        Args:
            oversight_request: The oversight request to wait for
            check_interval: How often to check for decision (seconds)

        Returns:
            The final decision
        """

        request_id = oversight_request.request_id
        timeout_time = oversight_request.created_at + timedelta(minutes=oversight_request.timeout_minutes)

        while datetime.now() < timeout_time:
            # Check if decision has been made
            if request_id in self.completed_requests:
                return self.completed_requests[request_id].decision

            # Check if still pending
            if request_id in self.pending_requests:
                current_request = self.pending_requests[request_id]
                if current_request.decision != OversightDecision.PENDING:
                    return current_request.decision

            # Wait before checking again
            await asyncio.sleep(check_interval)

        # Timeout reached
        logger.warning(f"Oversight request timed out: {request_id}")

        # Handle timeout based on risk level
        if oversight_request.risk_level in ["critical", "high"]:
            # Reject high-risk actions on timeout
            await self.provide_decision(
                request_id,
                OversightDecision.REJECT,
                "Timed out - rejected for safety",
                "system"
            )
            return OversightDecision.REJECT
        else:
            # Auto-approve low-risk actions on timeout
            await self.provide_decision(
                request_id,
                OversightDecision.APPROVE,
                "Timed out - auto-approved",
                "system"
            )
            return OversightDecision.APPROVE

    def get_pending_requests(self) -> List[OversightRequest]:
        """Get all pending oversight requests."""
        return list(self.pending_requests.values())

    def get_request_status(self, request_id: str) -> Optional[OversightRequest]:
        """Get status of a specific oversight request."""

        if request_id in self.pending_requests:
            return self.pending_requests[request_id]
        elif request_id in self.completed_requests:
            return self.completed_requests[request_id]
        else:
            return None

    def _assess_risk_level(self,
                          request_type: str,
                          agent_type: str,
                          context: Dict[str, Any]) -> str:
        """Assess risk level for an oversight request."""

        # Risk factors
        risk_score = 0

        # Request type risk
        high_risk_types = ["system_modification", "security_change", "data_deletion"]
        medium_risk_types = ["configuration_change", "network_access", "file_modification"]

        if request_type in high_risk_types:
            risk_score += 3
        elif request_type in medium_risk_types:
            risk_score += 2
        else:
            risk_score += 1

        # Agent type risk
        high_risk_agents = ["computer_terminal", "web_surfer"]
        if agent_type in high_risk_agents:
            risk_score += 2

        # Context-based risk
        if context.get("involves_external_systems", False):
            risk_score += 2
        if context.get("modifies_production_data", False):
            risk_score += 3
        if context.get("requires_elevated_privileges", False):
            risk_score += 2

        # Determine risk level
        if risk_score >= 7:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"
