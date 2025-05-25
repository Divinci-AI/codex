# Magentic-One QA Automation for Codex Lifecycle Hooks

This directory contains the Magentic-One multi-agent QA automation system for comprehensive testing and validation of the Codex lifecycle hooks system.

## Overview

The QA automation system uses Microsoft's Magentic-One multi-agent architecture to perform automated testing, validation, and quality assurance of the Codex hooks system. It includes:

- **Orchestrator Agent**: Coordinates testing workflows and manages other agents
- **FileSurfer Agent**: Validates configuration files and analyzes code
- **WebSurfer Agent**: Tests webhook endpoints and web-based integrations
- **Coder Agent**: Generates test scripts and analyzes results
- **ComputerTerminal Agent**: Executes CLI commands and tests

## Features

### 🔍 Comprehensive Testing
- Configuration validation and syntax checking
- Functional testing of all hook types
- Performance benchmarking and optimization
- Security vulnerability assessment
- End-to-end integration testing

### 🛡️ Safety and Security
- Container isolation for agent execution
- Resource limits and access restrictions
- Human oversight protocols
- Audit trails and monitoring
- Prompt injection protection

### 📊 Reporting and Analytics
- Detailed test reports in JSON format
- Performance metrics and benchmarks
- Security assessment reports
- Integration test results
- Execution traces and logs

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm
- Docker (optional, for container isolation)
- OpenAI API key

### Installation

1. **Run the setup script:**
   ```bash
   chmod +x qa-automation/scripts/setup.sh
   ./qa-automation/scripts/setup.sh
   ```

2. **Configure environment:**
   ```bash
   cp qa-automation/config/.env.example qa-automation/config/.env
   # Edit .env with your OpenAI API key and settings
   ```

3. **Activate virtual environment:**
   ```bash
   source qa-automation/venv/bin/activate
   ```

### Running QA Tests

#### Option 1: Direct Python Execution
```bash
python qa-automation/magentic-one/qa_orchestrator.py
```

#### Option 2: Docker Container (Recommended)
```bash
cd qa-automation/docker
docker-compose -f docker-compose.qa.yml up
```

#### Option 3: Individual Test Phases
```bash
# Configuration validation only
python -c "
import asyncio
from qa_automation.magentic_one.qa_orchestrator import CodexHooksQAOrchestrator

async def main():
    orchestrator = CodexHooksQAOrchestrator()
    await orchestrator.initialize()
    result = await orchestrator.validate_hooks_configuration()
    print(result)

asyncio.run(main())
"
```

## Configuration

### Main Configuration File: `config/qa-config.toml`

```toml
[qa]
enabled = true
debug = true
timeout_seconds = 300

[openai]
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"

[agents.file_surfer]
enabled = true
model = "gpt-4o"

[safety]
container_isolation = true
execution_time_limit = 600
memory_limit_mb = 1024
```

### Environment Variables: `config/.env`

```bash
OPENAI_API_KEY=your_api_key_here
QA_DEBUG=true
QA_CONTAINER_ISOLATION=true
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QA Orchestrator                         │
│                  (Magentic-One Core)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ FileSurfer  │ │ WebSurfer   │ │    Coder    │
│   Agent     │ │   Agent     │ │   Agent     │
└─────────────┘ └─────────────┘ └─────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
              ┌─────────────┐
              │ComputerTerm │
              │   Agent     │
              └─────────────┘
```

## Testing Phases

### Phase 1: Configuration Validation
- TOML syntax validation
- Hook type verification
- Security configuration checks
- Performance setting analysis

### Phase 2: Functional Testing
- Hook execution testing
- Event triggering validation
- Error handling verification
- Output validation

### Phase 3: Performance Testing
- Execution time benchmarking
- Memory usage analysis
- Scalability testing
- Resource limit validation

### Phase 4: Security Testing
- Input validation testing
- Sandbox isolation verification
- Privilege escalation checks
- Vulnerability assessment

### Phase 5: Integration Testing
- CLI integration testing
- End-to-end workflow validation
- Real-world scenario testing
- User experience validation

## Output and Reports

### Report Structure
```
qa-automation/reports/
├── qa_results_20241201_143022.json
├── configuration_validation_report.json
├── performance_benchmarks.json
├── security_assessment.json
└── integration_test_results.json
```

### Sample Report
```json
{
  "execution_id": "qa-1701434622",
  "start_time": "2024-12-01T14:30:22",
  "end_time": "2024-12-01T14:45:18",
  "overall_status": "passed",
  "configuration_validation": {
    "status": "completed",
    "issues_found": 0,
    "recommendations": [...]
  },
  "performance_testing": {
    "average_execution_time": "0.245s",
    "memory_usage": "45MB",
    "recommendations": [...]
  }
}
```

## Safety Protocols

### Container Isolation
- All agents run in isolated Docker containers
- Limited network access to approved domains
- Read-only file system with specific writable areas
- Resource limits (CPU, memory, execution time)

### Access Restrictions
- No sudo or administrative privileges
- Blocked dangerous commands (rm, chmod, etc.)
- Network restrictions to prevent unauthorized access
- File system restrictions to protect sensitive data

### Human Oversight
- All test executions are logged and auditable
- Critical operations require human approval
- Automatic safety checks and circuit breakers
- Real-time monitoring and alerting

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Found**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Playwright Browser Installation**
   ```bash
   playwright install chromium
   ```

3. **Permission Denied Errors**
   ```bash
   chmod +x qa-automation/scripts/*.sh
   ```

4. **Docker Container Issues**
   ```bash
   docker-compose -f docker-compose.qa.yml down
   docker-compose -f docker-compose.qa.yml up --build
   ```

### Debug Mode
Enable debug logging by setting:
```bash
export QA_DEBUG=true
export AUTOGEN_DEBUG=true
```

### Log Files
- Main logs: `qa-automation/logs/qa-orchestrator.log`
- Agent logs: `qa-automation/logs/agent-*.log`
- Docker logs: `docker-compose logs magentic-one-qa`

## Development

### Adding New Test Scenarios
1. Create test scenario in `qa-automation/test-data/`
2. Add scenario configuration to `qa-config.toml`
3. Implement test logic in `qa_orchestrator.py`
4. Update documentation

### Custom Agents
1. Create agent class in `qa-automation/agents/`
2. Register agent in orchestrator
3. Add agent configuration to `qa-config.toml`
4. Test agent functionality

### Contributing
1. Follow existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation
4. Ensure security and safety protocols are maintained

## Security Considerations

⚠️ **Important Security Notes:**

- Never run QA automation with production API keys
- Always use container isolation in production
- Monitor agent behavior for unexpected actions
- Review all generated code before execution
- Limit network access to necessary domains only
- Regularly update dependencies for security patches

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs in `qa-automation/logs/`
3. Check Docker container status
4. Verify environment configuration
5. Consult the main Codex documentation

## License

This QA automation system is part of the Codex project and follows the same license terms.
