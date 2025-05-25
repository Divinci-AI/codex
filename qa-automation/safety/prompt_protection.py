#!/usr/bin/env python3
"""
Prompt Injection Protection for Magentic-One QA Automation

This module provides protection against prompt injection attacks
and malicious prompt manipulation in the QA automation system.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat levels for prompt injection detection."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InjectionDetector:
    """
    Prompt injection detector with multiple detection strategies.
    """

    def __init__(self):
        self.detection_patterns = self._load_detection_patterns()
        self.whitelist_patterns = self._load_whitelist_patterns()
        self.detection_history = []

    def analyze_prompt(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a prompt for potential injection attacks.

        Args:
            prompt: The prompt to analyze
            context: Additional context for analysis

        Returns:
            Analysis results
        """

        context = context or {}

        # Initialize analysis result
        analysis = {
            "prompt_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "prompt_length": len(prompt),
            "threat_level": ThreatLevel.NONE,
            "detected_patterns": [],
            "risk_score": 0.0,
            "recommendations": [],
            "safe_to_execute": True
        }

        # Run detection methods
        pattern_results = self._detect_malicious_patterns(prompt)
        structure_results = self._analyze_prompt_structure(prompt)
        context_results = self._analyze_context_manipulation(prompt, context)
        encoding_results = self._detect_encoding_attacks(prompt)

        # Combine results
        all_detections = (
            pattern_results["detections"] +
            structure_results["detections"] +
            context_results["detections"] +
            encoding_results["detections"]
        )

        # Calculate overall risk score
        total_risk = (
            pattern_results["risk_score"] +
            structure_results["risk_score"] +
            context_results["risk_score"] +
            encoding_results["risk_score"]
        )

        analysis["detected_patterns"] = all_detections
        analysis["risk_score"] = min(total_risk, 10.0)  # Cap at 10.0

        # Determine threat level
        analysis["threat_level"] = self._calculate_threat_level(analysis["risk_score"])

        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)

        # Determine if safe to execute
        analysis["safe_to_execute"] = analysis["threat_level"] in [ThreatLevel.NONE, ThreatLevel.LOW]

        # Store in history
        self.detection_history.append(analysis)

        return analysis

    def _detect_malicious_patterns(self, prompt: str) -> Dict[str, Any]:
        """Detect known malicious patterns in prompt."""

        detections = []
        risk_score = 0.0

        for pattern_name, pattern_data in self.detection_patterns.items():
            pattern = pattern_data["regex"]
            risk_weight = pattern_data["risk_weight"]

            matches = re.findall(pattern, prompt, re.IGNORECASE | re.MULTILINE)

            if matches:
                detections.append({
                    "type": "malicious_pattern",
                    "pattern_name": pattern_name,
                    "matches": matches,
                    "risk_weight": risk_weight,
                    "description": pattern_data.get("description", "")
                })

                risk_score += risk_weight * len(matches)

        return {
            "detections": detections,
            "risk_score": risk_score
        }

    def _analyze_prompt_structure(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt structure for injection indicators."""

        detections = []
        risk_score = 0.0

        # Check for excessive instruction markers
        instruction_markers = ["###", "---", "```", "SYSTEM:", "USER:", "ASSISTANT:"]
        marker_counts = {marker: prompt.count(marker) for marker in instruction_markers}

        for marker, count in marker_counts.items():
            if count > 5:  # Threshold for suspicious activity
                detections.append({
                    "type": "excessive_markers",
                    "marker": marker,
                    "count": count,
                    "risk_weight": 1.0
                })
                risk_score += 1.0

        # Check for role confusion attempts
        role_confusion_patterns = [
            r"ignore\s+previous\s+instructions",
            r"forget\s+everything\s+above",
            r"you\s+are\s+now\s+a\s+different",
            r"new\s+role\s*:",
            r"act\s+as\s+if\s+you\s+are"
        ]

        for pattern in role_confusion_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                detections.append({
                    "type": "role_confusion",
                    "pattern": pattern,
                    "risk_weight": 3.0
                })
                risk_score += 3.0

        # Check for prompt termination attempts
        termination_patterns = [
            r"<\s*/\s*prompt\s*>",
            r"end\s+of\s+prompt",
            r"stop\s+processing",
            r"exit\s+prompt\s+mode"
        ]

        for pattern in termination_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                detections.append({
                    "type": "prompt_termination",
                    "pattern": pattern,
                    "risk_weight": 2.5
                })
                risk_score += 2.5

        return {
            "detections": detections,
            "risk_score": risk_score
        }

    def _analyze_context_manipulation(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze attempts to manipulate context or system behavior."""

        detections = []
        risk_score = 0.0

        # Check for system command injection
        system_commands = [
            r"sudo\s+",
            r"rm\s+-rf",
            r"chmod\s+777",
            r"wget\s+",
            r"curl\s+",
            r"nc\s+-",
            r"netcat\s+",
            r"/etc/passwd",
            r"/etc/shadow"
        ]

        for cmd_pattern in system_commands:
            if re.search(cmd_pattern, prompt, re.IGNORECASE):
                detections.append({
                    "type": "system_command_injection",
                    "pattern": cmd_pattern,
                    "risk_weight": 4.0
                })
                risk_score += 4.0

        # Check for data exfiltration attempts
        exfiltration_patterns = [
            r"send\s+to\s+http",
            r"post\s+to\s+",
            r"upload\s+file",
            r"email\s+contents",
            r"save\s+to\s+external"
        ]

        for pattern in exfiltration_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                detections.append({
                    "type": "data_exfiltration",
                    "pattern": pattern,
                    "risk_weight": 3.5
                })
                risk_score += 3.5

        return {
            "detections": detections,
            "risk_score": risk_score
        }

    def _detect_encoding_attacks(self, prompt: str) -> Dict[str, Any]:
        """Detect encoding-based injection attacks."""

        detections = []
        risk_score = 0.0

        # Check for base64 encoded content
        base64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
        base64_matches = re.findall(base64_pattern, prompt)

        if len(base64_matches) > 3:  # Multiple base64 strings suspicious
            detections.append({
                "type": "excessive_base64",
                "count": len(base64_matches),
                "risk_weight": 2.0
            })
            risk_score += 2.0

        # Check for URL encoding
        url_encoded_pattern = r"%[0-9A-Fa-f]{2}"
        url_encoded_count = len(re.findall(url_encoded_pattern, prompt))

        if url_encoded_count > 10:  # Excessive URL encoding
            detections.append({
                "type": "excessive_url_encoding",
                "count": url_encoded_count,
                "risk_weight": 1.5
            })
            risk_score += 1.5

        # Check for unicode escape sequences
        unicode_pattern = r"\\u[0-9A-Fa-f]{4}"
        unicode_count = len(re.findall(unicode_pattern, prompt))

        if unicode_count > 5:  # Excessive unicode escapes
            detections.append({
                "type": "excessive_unicode_escapes",
                "count": unicode_count,
                "risk_weight": 1.0
            })
            risk_score += 1.0

        return {
            "detections": detections,
            "risk_score": risk_score
        }

    def _calculate_threat_level(self, risk_score: float) -> ThreatLevel:
        """Calculate threat level based on risk score."""

        if risk_score >= 8.0:
            return ThreatLevel.CRITICAL
        elif risk_score >= 6.0:
            return ThreatLevel.HIGH
        elif risk_score >= 4.0:
            return ThreatLevel.MEDIUM
        elif risk_score >= 2.0:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NONE

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results."""

        recommendations = []

        threat_level = analysis["threat_level"]
        detections = analysis["detected_patterns"]

        if threat_level == ThreatLevel.CRITICAL:
            recommendations.append("BLOCK: Critical threat detected - do not execute")
            recommendations.append("Escalate to security team immediately")

        elif threat_level == ThreatLevel.HIGH:
            recommendations.append("CAUTION: High risk prompt - require human approval")
            recommendations.append("Review detected patterns before execution")

        elif threat_level == ThreatLevel.MEDIUM:
            recommendations.append("WARNING: Medium risk detected - enhanced monitoring recommended")

        # Specific recommendations based on detection types
        detection_types = [d["type"] for d in detections]

        if "system_command_injection" in detection_types:
            recommendations.append("Sanitize system commands before execution")

        if "role_confusion" in detection_types:
            recommendations.append("Validate agent role and context before processing")

        if "data_exfiltration" in detection_types:
            recommendations.append("Block external network access during execution")

        if not recommendations:
            recommendations.append("Prompt appears safe for execution")

        return recommendations

    def _load_detection_patterns(self) -> Dict[str, Any]:
        """Load malicious pattern detection rules."""

        return {
            "instruction_override": {
                "regex": r"(ignore|forget|disregard)\s+(previous|all|above)\s+(instructions|prompts|rules)",
                "risk_weight": 4.0,
                "description": "Attempts to override previous instructions"
            },
            "role_hijacking": {
                "regex": r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+.{1,50}(admin|root|system|developer)",
                "risk_weight": 3.5,
                "description": "Attempts to hijack agent role"
            },
            "command_execution": {
                "regex": r"(exec|eval|system|shell|subprocess|os\.system)\s*\(",
                "risk_weight": 4.5,
                "description": "Direct command execution attempts"
            }
        }

    def _load_whitelist_patterns(self) -> List[str]:
        """Load patterns that are considered safe."""

        return [
            r"test\s+case",
            r"example\s+usage",
            r"documentation\s+string"
        ]


class PromptInjectionProtector:
    """
    Main prompt injection protection system.

    Provides comprehensive protection against prompt injection attacks
    with configurable security levels and response strategies.
    """

    def __init__(self, security_level: str = "standard"):
        self.security_level = security_level
        self.detector = InjectionDetector()
        self.protection_config = self._load_protection_config()
        self.blocked_prompts = []

        # Protection storage
        self.protection_dir = Path("qa-automation/prompt-protection")
        self.protection_dir.mkdir(exist_ok=True)

    async def protect_prompt(self,
                           prompt: str,
                           agent_type: str,
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Protect against prompt injection attacks.

        Args:
            prompt: The prompt to protect
            agent_type: Type of agent processing the prompt
            context: Additional context

        Returns:
            Protection result with sanitized prompt or block decision
        """

        context = context or {}

        # Analyze prompt for threats
        analysis = self.detector.analyze_prompt(prompt, context)

        # Determine protection action
        protection_action = self._determine_protection_action(
            analysis["threat_level"],
            agent_type
        )

        result = {
            "protection_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "original_prompt": prompt,
            "agent_type": agent_type,
            "analysis": analysis,
            "protection_action": protection_action,
            "safe_to_execute": protection_action != "block",
            "sanitized_prompt": prompt if protection_action != "block" else None,
            "block_reason": "Threat level too high" if protection_action == "block" else None
        }

        if protection_action == "block":
            await self._log_blocked_prompt(result)

        return result

    def _determine_protection_action(self,
                                   threat_level: ThreatLevel,
                                   agent_type: str) -> str:
        """Determine what protection action to take."""

        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            return "block"
        elif threat_level == ThreatLevel.MEDIUM:
            return "sanitize"
        else:
            return "allow"

    def _load_protection_config(self) -> Dict[str, Any]:
        """Load protection configuration."""

        return {
            "block_high_risk": True,
            "sanitize_medium_risk": True,
            "log_all_prompts": True
        }

    async def _log_blocked_prompt(self, result: Dict[str, Any]):
        """Log a blocked prompt."""

        self.blocked_prompts.append(result)

        blocked_file = self.protection_dir / "blocked_prompts.jsonl"
        with open(blocked_file, "a") as f:
            f.write(json.dumps({
                "timestamp": result["timestamp"],
                "protection_id": result["protection_id"],
                "agent_type": result["agent_type"],
                "threat_level": result["analysis"]["threat_level"].value,
                "risk_score": result["analysis"]["risk_score"]
            }) + "\n")

        logger.warning(f"Blocked malicious prompt: {result['protection_id']}")
