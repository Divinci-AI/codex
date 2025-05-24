# Codex QA Automation with Magentic-One

This directory contains the Magentic-One multi-agent system for automated QA testing of the Codex lifecycle hooks system.

## Overview

The QA system uses Microsoft's Magentic-One framework to orchestrate multiple specialized agents that work together to validate, test, and monitor the lifecycle hooks functionality.

## Architecture

### Agent Team Composition

1. **Orchestrator Agent** - Coordinates the entire QA workflow
2. **FileSurfer Agent** - Validates configuration files and file operations
3. **WebSurfer Agent** - Tests webhook endpoints and web-based integrations
4. **Coder Agent** - Generates test scripts and analyzes code
5. **ComputerTerminal Agent** - Executes CLI commands and automation

### Safety Features

- **Container Isolation**: All agents run in secure Docker containers
- **Access Restrictions**: Limited file system and network access
- **Human Oversight**: Critical operations require human approval
- **Prompt Injection Protection**: Input sanitization and validation
- **Comprehensive Logging**: All agent actions are logged and monitored

## Quick Start

### Prerequisites

1. Python 3.9+ with pip
2. Docker and Docker Compose
3. OpenAI API key
4. Playwright browser dependencies

### Installation

```bash
# Install Magentic-One and dependencies
pip install -r requirements.txt
playwright install --with-deps chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your OpenAI API key and other settings

# Build the QA container
docker build -t codex-qa .
```

### Running QA Tests

```bash
# Run full QA suite
python run_qa.py --suite full

# Run specific test category
python run_qa.py --suite hooks-validation
python run_qa.py --suite performance-benchmarks
python run_qa.py --suite security-tests

# Run with custom configuration
python run_qa.py --config custom-qa-config.json
```

## Directory Structure

```
qa/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── Dockerfile               # QA container definition
├── docker-compose.yml       # Multi-container setup
├── run_qa.py               # Main QA runner script
├── agents/                 # Agent implementations
│   ├── __init__.py
│   ├── orchestrator.py     # Main orchestrator agent
│   ├── file_surfer.py      # File validation agent
│   ├── web_surfer.py       # Web testing agent
│   ├── coder.py           # Code generation agent
│   └── terminal.py        # CLI automation agent
├── configs/               # Configuration files
│   ├── agent_config.json  # Agent team configuration
│   ├── safety_config.json # Safety and security settings
│   └── test_scenarios.json # Test scenario definitions
├── workflows/             # QA workflow definitions
│   ├── __init__.py
│   ├── hooks_validation.py # Hook configuration validation
│   ├── e2e_testing.py     # End-to-end testing workflows
│   ├── performance.py     # Performance benchmarking
│   └── security.py        # Security testing workflows
├── reports/               # Generated test reports
│   └── .gitkeep
├── logs/                  # QA execution logs
│   └── .gitkeep
└── tests/                 # Unit tests for QA system
    ├── __init__.py
    ├── test_agents.py
    ├── test_workflows.py
    └── test_safety.py
```

## Configuration

### Agent Configuration

The `configs/agent_config.json` file defines the agent team setup:

```json
{
  "orchestrator": {
    "model": "gpt-4o",
    "max_tokens": 4000,
    "temperature": 0.1
  },
  "agents": {
    "file_surfer": {
      "enabled": true,
      "max_file_size": "10MB",
      "allowed_extensions": [".toml", ".json", ".yaml", ".sh", ".py"]
    },
    "web_surfer": {
      "enabled": true,
      "timeout": 30,
      "allowed_domains": ["localhost", "127.0.0.1"]
    },
    "coder": {
      "enabled": true,
      "languages": ["python", "bash", "javascript", "typescript"]
    },
    "terminal": {
      "enabled": true,
      "sandbox": true,
      "timeout": 300
    }
  }
}
```

### Safety Configuration

The `configs/safety_config.json` file defines security settings:

```json
{
  "container_isolation": true,
  "network_restrictions": {
    "allowed_domains": ["localhost", "127.0.0.1", "api.openai.com"],
    "blocked_ports": [22, 23, 3389]
  },
  "file_system_restrictions": {
    "read_only_paths": ["/etc", "/usr", "/bin"],
    "writable_paths": ["/tmp", "/workspace"],
    "max_file_size": "100MB"
  },
  "execution_limits": {
    "max_execution_time": 600,
    "max_memory_usage": "2GB",
    "max_cpu_usage": "80%"
  },
  "human_oversight": {
    "require_approval_for": [
      "file_deletion",
      "network_requests",
      "system_commands"
    ],
    "auto_approve_safe_operations": true
  }
}
```

## Test Scenarios

The QA system supports various test scenarios:

### 1. Hook Configuration Validation

- Syntax and structure validation
- Parameter type checking
- Condition expression testing
- File path and permission verification

### 2. End-to-End Testing

- Hook execution workflows
- Error handling scenarios
- Integration testing
- Regression testing

### 3. Performance Benchmarking

- Hook execution overhead measurement
- Concurrent hook testing
- Memory and CPU usage analysis
- Performance regression detection

### 4. Security Testing

- Input validation testing
- Permission boundary testing
- Injection attack prevention
- Access control verification

## Monitoring and Reporting

### Real-time Monitoring

- Agent execution status
- Resource usage metrics
- Error rates and patterns
- Performance indicators

### Report Generation

- Comprehensive test reports
- Performance benchmarks
- Security assessment reports
- Trend analysis and recommendations

## Troubleshooting

### Common Issues

1. **Agent Connection Failures**

   - Check OpenAI API key configuration
   - Verify network connectivity
   - Review container logs

2. **Permission Errors**

   - Ensure proper file permissions
   - Check Docker container privileges
   - Verify workspace directory access

3. **Performance Issues**
   - Monitor resource usage
   - Adjust container limits
   - Optimize test scenarios

### Debug Mode

Enable debug mode for detailed logging:

```bash
python run_qa.py --debug --verbose
```

## Contributing

When adding new QA capabilities:

1. Follow the agent interface patterns
2. Add comprehensive safety checks
3. Include unit tests
4. Update documentation
5. Test in isolated environment first

## License

This QA system is part of the Codex project and follows the same license terms.
