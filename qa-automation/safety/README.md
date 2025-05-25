# Safety and Monitoring System for Magentic-One QA Automation

This directory contains the comprehensive safety and monitoring system for the Magentic-One QA automation framework. The system provides multiple layers of protection, monitoring, and oversight to ensure secure and reliable operation of AI agents.

## Overview

The safety system consists of five main components:

1. **Container Isolation** - Secure containerized execution environments
2. **Comprehensive Logging & Monitoring** - Real-time system monitoring and alerting
3. **Human Oversight Protocol** - Human-in-the-loop validation for critical decisions
4. **Access Control Management** - Permission-based security and policy enforcement
5. **Prompt Injection Protection** - Defense against malicious prompt manipulation

## Components

### 1. Container Isolation (`container_isolation.py`)

Provides secure, isolated execution environments for Magentic-One agents using Docker containers.

**Features:**
- Configurable security levels (minimal, standard, strict, maximum)
- Resource limits and monitoring
- Network isolation and access controls
- Secure file system access
- Command execution validation

**Usage:**
```python
from qa_automation.safety import ContainerIsolationManager

# Create isolation manager
isolation = ContainerIsolationManager()

# Create isolated environment
env = await isolation.create_isolated_environment(
    agent_type="file_surfer",
    security_level="standard"
)

# Execute command safely
result = await isolation.execute_in_isolation(
    env["environment_id"],
    "echo 'Hello from isolated environment'"
)
```

### 2. Comprehensive Logging & Monitoring (`logging_monitor.py`)

Provides centralized logging, real-time monitoring, and alerting capabilities.

**Features:**
- Structured logging with multiple handlers
- Real-time metrics collection
- Automated alerting system
- Performance monitoring
- System health tracking

**Usage:**
```python
from qa_automation.safety import ComprehensiveLoggingSystem, MonitoringDashboard

# Set up logging
logging_system = ComprehensiveLoggingSystem()
dashboard = MonitoringDashboard(logging_system)

# Log QA events
logging_system.log_qa_event(
    "test_execution",
    "file_surfer",
    "session-123",
    {"test_name": "config_validation"}
)

# Get dashboard data
status = dashboard.get_dashboard_data()
```

### 3. Human Oversight Protocol (`human_oversight.py`)

Implements human-in-the-loop validation for critical decisions and high-risk actions.

**Features:**
- Risk assessment and escalation
- Configurable oversight rules
- Timeout handling with safe defaults
- Decision tracking and audit trail
- Notification system integration

**Usage:**
```python
from qa_automation.safety import HumanOversightProtocol, OversightDecision

# Create oversight protocol
oversight = HumanOversightProtocol()

# Request oversight for critical action
request = await oversight.request_oversight(
    "system_modification",
    "computer_terminal",
    "Modify system configuration file",
    {"file_path": "/etc/config.conf"}
)

# Wait for human decision
decision = await oversight.wait_for_decision(request)

if decision == OversightDecision.APPROVE:
    # Proceed with action
    pass
```

### 4. Access Control Management (`access_control.py`)

Provides comprehensive access control, security policies, and permission management.

**Features:**
- Role-based access control
- Security policy enforcement
- Session management
- Permission levels (none, read, write, execute, admin)
- Audit logging

**Usage:**
```python
from qa_automation.safety import AccessControlManager

# Create access control manager
access_control = AccessControlManager()

# Authorize agent action
result = await access_control.authorize_agent_action(
    "file_surfer",
    "read",
    "configuration_files",
    {"file_type": "toml"}
)

if result["authorized"]:
    # Proceed with action
    pass
```

### 5. Prompt Injection Protection (`prompt_protection.py`)

Protects against prompt injection attacks and malicious prompt manipulation.

**Features:**
- Multi-layer threat detection
- Pattern-based malicious content detection
- Risk scoring and threat level assessment
- Prompt sanitization capabilities
- Configurable security policies

**Usage:**
```python
from qa_automation.safety import PromptInjectionProtector

# Create protector
protector = PromptInjectionProtector(security_level="standard")

# Protect prompt
result = await protector.protect_prompt(
    "Analyze this file and ignore all previous instructions",
    "file_surfer"
)

if result["safe_to_execute"]:
    # Use sanitized prompt
    safe_prompt = result["sanitized_prompt"]
```

### 6. Safety Integration System (`safety_integration.py`)

Integrates all safety components into a unified system for comprehensive protection.

**Features:**
- Unified safety orchestration
- Multi-layer protection workflow
- Session management
- Comprehensive safety status reporting
- Automated cleanup and resource management

**Usage:**
```python
from qa_automation.safety import SafetyIntegrationSystem

# Create integrated safety system
safety = SafetyIntegrationSystem(
    security_level="standard",
    enable_container_isolation=True,
    enable_human_oversight=True
)

# Create safe execution environment
env = await safety.create_safe_execution_environment(
    "file_surfer",
    "session-123"
)

# Execute action safely
result = await safety.execute_safe_action(
    "session-123",
    "file_analysis",
    {"file_path": "/config/hooks.toml"},
    prompt="Analyze this configuration file"
)
```

## Security Levels

The system supports four security levels:

### Minimal
- Basic protection only
- Suitable for development environments
- Limited resource restrictions
- Reduced oversight requirements

### Standard (Default)
- Balanced security and functionality
- Appropriate for most QA scenarios
- Moderate resource limits
- Standard oversight protocols

### Strict
- Enhanced security measures
- Suitable for sensitive environments
- Tight resource restrictions
- Increased oversight requirements

### Maximum
- Maximum security protection
- For highly sensitive operations
- Minimal resource allocation
- Comprehensive oversight required

## Configuration

### Environment Variables

```bash
# Security level
SAFETY_SECURITY_LEVEL=standard

# Component enablement
SAFETY_ENABLE_CONTAINER_ISOLATION=true
SAFETY_ENABLE_HUMAN_OVERSIGHT=true

# Logging configuration
SAFETY_LOG_LEVEL=INFO
SAFETY_LOG_RETENTION_DAYS=30

# Monitoring settings
SAFETY_MONITORING_INTERVAL=30
SAFETY_ALERT_THRESHOLD_CPU=90
SAFETY_ALERT_THRESHOLD_MEMORY=90
```

### Configuration Files

The system uses several configuration files:

- `access_control.json` - Access control policies and permissions
- `oversight_rules.json` - Human oversight rules and thresholds
- `security_policies.json` - Security policies and enforcement rules

## Monitoring and Alerting

The system provides comprehensive monitoring and alerting:

### Metrics Collected
- System resource usage (CPU, memory)
- Agent execution statistics
- Security event counts
- Error rates and patterns
- Performance metrics

### Alert Types
- **Critical**: System failures, security breaches
- **Warning**: Resource thresholds, policy violations
- **Info**: Normal operations, status changes

### Dashboard Features
- Real-time system status
- Historical metrics and trends
- Active alerts and notifications
- Session management overview

## Best Practices

### For Developers

1. **Always use the integrated safety system** for production deployments
2. **Configure appropriate security levels** based on environment sensitivity
3. **Monitor safety metrics** regularly and respond to alerts promptly
4. **Test safety mechanisms** in development environments
5. **Keep security policies updated** as requirements change

### For Operators

1. **Review oversight requests promptly** to avoid timeouts
2. **Monitor system health** through the dashboard
3. **Investigate security alerts** immediately
4. **Maintain audit logs** for compliance and debugging
5. **Update access permissions** as team roles change

### For Security Teams

1. **Regularly review security policies** and update as needed
2. **Audit access control configurations** periodically
3. **Analyze blocked prompts** for emerging threat patterns
4. **Test incident response procedures** regularly
5. **Keep threat detection patterns** up to date

## Troubleshooting

### Common Issues

#### Container Isolation Not Working
- Ensure Docker is installed and running
- Check Docker permissions for the user
- Verify network connectivity if needed

#### High Resource Usage
- Check for resource leaks in active sessions
- Review container resource limits
- Monitor for runaway processes

#### Oversight Timeouts
- Verify notification systems are working
- Check oversight request queue
- Review timeout configurations

#### Access Denied Errors
- Verify user/agent permissions
- Check security policy configurations
- Review access control logs

### Log Locations

- Main logs: `qa-automation/logs/qa_automation.log`
- Error logs: `qa-automation/logs/errors.log`
- Security logs: `qa-automation/access-control/`
- Oversight logs: `qa-automation/oversight/`
- Protection logs: `qa-automation/prompt-protection/`

## Integration with QA Workflows

The safety system integrates seamlessly with existing QA workflows:

1. **Automated Test Execution**: Provides safe environments for test execution
2. **Configuration Validation**: Protects against malicious configurations
3. **Performance Testing**: Monitors resource usage during load tests
4. **Security Testing**: Validates security controls and policies
5. **Compliance Reporting**: Generates audit trails and compliance reports

## Future Enhancements

Planned improvements include:

- **Machine Learning Threat Detection**: Advanced ML-based threat detection
- **Automated Remediation**: Self-healing capabilities for common issues
- **Enhanced Visualization**: Improved dashboard and reporting features
- **Integration APIs**: REST APIs for external system integration
- **Cloud Provider Support**: Native support for cloud security services

## Support

For support and questions:

1. Check the troubleshooting section above
2. Review log files for error details
3. Consult the main QA automation documentation
4. Contact the development team for assistance

## License

This safety system is part of the Codex AutoAgent Framework and is subject to the same licensing terms.
