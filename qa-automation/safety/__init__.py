"""
Safety and Monitoring Module for Magentic-One QA Automation

This module provides security, isolation, and monitoring capabilities
for safe execution of Magentic-One agents.
"""

__version__ = "1.0.0"
__author__ = "Codex AutoAgent Framework"

try:
    from .container_isolation import ContainerIsolationManager, SecurityError
except ImportError:
    ContainerIsolationManager = None
    SecurityError = Exception

from .logging_monitor import ComprehensiveLoggingSystem, MonitoringDashboard
from .human_oversight import HumanOversightProtocol, OversightDecision
from .access_control import AccessControlManager, SecurityPolicy, PermissionLevel
from .prompt_protection import PromptInjectionProtector, InjectionDetector, ThreatLevel
from .safety_integration import SafetyIntegrationSystem

__all__ = [
    "ContainerIsolationManager",
    "SecurityError",
    "ComprehensiveLoggingSystem",
    "MonitoringDashboard",
    "HumanOversightProtocol",
    "OversightDecision",
    "AccessControlManager",
    "SecurityPolicy",
    "PermissionLevel",
    "PromptInjectionProtector",
    "InjectionDetector",
    "ThreatLevel",
    "SafetyIntegrationSystem"
]
