# Hooks E2E Testing Guide

This document describes the end-to-end testing strategy for the Codex hooks system integration with the CLI.

## Overview

The E2E testing suite validates the complete integration between the TypeScript CLI and the Rust hooks backend, ensuring that lifecycle events are properly emitted, hooks are executed, and results are handled correctly.

## Test Structure

### 1. **E2E Tests** (`tests/hooks-e2e.test.ts`)
Tests the core hook functionality and event system:

- **Hook Event Integration**: Event creation, emission, and handling
- **Hook Status Display**: CLI output for hook execution results
- **Configuration Loading**: Hook configuration file parsing and validation
- **Real Hook Execution**: Script execution with environment variables
- **Webhook Integration**: HTTP webhook configuration and execution
- **MCP Tool Integration**: MCP tool hook configuration
- **Performance Testing**: Multiple hooks execution and metrics

### 2. **CLI Integration Tests** (`tests/hooks-cli-integration.test.ts`)
Tests the complete CLI workflow with hooks enabled:

- **CLI Configuration**: Loading hooks config from files
- **Command Execution**: Hook execution during CLI operations
- **Error Handling**: Graceful failure handling and recovery
- **Priority Ordering**: Hook execution order based on priority
- **Environment Variables**: Proper variable passing to hooks
- **Performance**: Scalability with multiple hooks
- **Timeout Handling**: Hook timeout and cancellation

## Running Tests

### Quick Start
```bash
# Run all E2E tests
./run_hooks_e2e_tests.sh all

# Run specific test categories
./run_hooks_e2e_tests.sh e2e
./run_hooks_e2e_tests.sh integration
```

### Available Commands
```bash
./run_hooks_e2e_tests.sh [COMMAND]

Commands:
  all             # Run all hooks E2E tests
  e2e             # Run hooks E2E tests only
  integration     # Run CLI integration tests only
  events          # Run hook event tests
  config          # Run configuration tests
  execution       # Run hook execution tests
  webhook         # Run webhook hook tests
  mcp             # Run MCP hook tests
  performance     # Run performance tests
  error-handling  # Run error handling tests
  verbose         # Run tests with verbose output
  watch           # Run tests in watch mode
  coverage        # Run tests with coverage report
  setup           # Set up test environment
  clean           # Clean test artifacts
```

### Using npm/vitest directly
```bash
# Run specific test files
npm test -- hooks-e2e
npm test -- hooks-cli-integration

# Run with specific patterns
npm test -- hooks-e2e --grep "Hook Event Integration"
npm test -- hooks-cli-integration --grep "Performance"

# Run in watch mode
npm test -- hooks-e2e --watch

# Run with coverage
npm test -- hooks-e2e hooks-cli-integration --coverage
```

## Test Scenarios

### 1. Hook Event Lifecycle
```typescript
// Test session start/end events
const sessionStartEvent = createSessionStartEvent("session-123", "gpt-4");
const result = await emitLifecycleEvent(sessionStartEvent, config);
expect(result?.success).toBe(true);
```

### 2. Configuration Loading
```toml
# Test hooks.toml configuration
[hooks]
enabled = true
timeout_seconds = 30

[[hooks.session]]
event = "session.start"
type = "script"
command = ["./test-hook.sh"]
```

### 3. Script Hook Execution
```bash
#!/bin/bash
# Test hook script
echo "Hook executed: $CODEX_EVENT_TYPE"
echo "Session: $CODEX_SESSION_ID"
exit 0
```

### 4. Webhook Hook Testing
```toml
[[hooks.task]]
event = "task.complete"
type = "webhook"
url = "https://httpbin.org/post"
method = "POST"
timeout = 10
```

### 5. MCP Tool Hook Testing
```toml
[[hooks.exec]]
event = "exec.before"
type = "mcp_tool"
server = "security_scanner"
tool = "scan_command"
```

## Test Environment

### Temporary Directories
Tests use isolated temporary directories:
```typescript
testDir = join(tmpdir(), `codex-hooks-test-${Date.now()}`);
mkdirSync(testDir, { recursive: true });
```

### Mock Scripts
Tests create executable scripts for hook testing:
```typescript
writeFileSync(scriptPath, `#!/bin/bash
echo "Hook executed: $CODEX_EVENT_TYPE"
exit 0
`, { mode: 0o755 });
```

### Configuration Files
Tests generate TOML configuration files:
```typescript
const hooksConfig = `
[hooks]
enabled = true

[[hooks.session]]
event = "session.start"
type = "script"
command = ["${scriptPath}"]
`;
writeFileSync(configPath, hooksConfig);
```

## Integration Points

### 1. CLI Event Emission
The CLI emits lifecycle events at key points:
- Session start/end
- Task start/completion
- Command execution (before/after)
- Error occurrences

### 2. Hook Configuration
The CLI loads hook configuration from:
- `hooks.toml` in project directory
- Global configuration files
- Environment variable overrides

### 3. Backend Communication
The CLI communicates with the Rust backend via:
- Process spawning (calling Rust binary)
- IPC mechanisms
- Shared configuration files

## Test Coverage

### ✅ Currently Tested
- [x] Hook event creation and emission
- [x] Configuration file loading and parsing
- [x] Script hook execution simulation
- [x] Webhook hook configuration
- [x] MCP tool hook configuration
- [x] Error handling and recovery
- [x] Performance with multiple hooks
- [x] Environment variable passing
- [x] Hook priority and ordering
- [x] Timeout handling

### 🔄 Future Testing (Requires Backend Integration)
- [ ] Real Rust backend communication
- [ ] Actual script execution via backend
- [ ] Real webhook HTTP calls
- [ ] MCP tool integration
- [ ] Hook result aggregation
- [ ] Performance benchmarking
- [ ] Memory usage testing
- [ ] Concurrent hook execution

## Debugging Tests

### Enable Verbose Logging
```bash
# Run with verbose output
./run_hooks_e2e_tests.sh verbose

# Or with npm
npm test -- hooks-e2e --reporter=verbose
```

### Check Test Artifacts
```bash
# View temporary test files
ls /tmp/codex-*hooks-test-*

# Check hook execution logs
cat /tmp/codex-hooks-test-*/hook-execution.log
```

### Debug Individual Tests
```bash
# Run single test with debugging
npm test -- hooks-e2e --grep "should emit session start events" --reporter=verbose
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Hooks E2E Tests
on: [push, pull_request]

jobs:
  hooks-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: ./run_hooks_e2e_tests.sh all
      - run: ./run_hooks_e2e_tests.sh coverage
```

### Test Reports
```bash
# Generate test reports
npm test -- hooks-e2e hooks-cli-integration --reporter=json --outputFile=test-results.json

# Generate coverage reports
npm test -- hooks-e2e hooks-cli-integration --coverage --coverage.reporter=html
```

## Best Practices

### 1. Test Isolation
- Each test uses a unique temporary directory
- Tests clean up after themselves
- No shared state between tests

### 2. Realistic Scenarios
- Use actual hook scripts and configurations
- Test real-world use cases
- Include error scenarios

### 3. Performance Considerations
- Test with multiple hooks
- Measure execution times
- Test timeout scenarios

### 4. Error Handling
- Test hook failures
- Test configuration errors
- Test network failures (webhooks)

## Troubleshooting

### Common Issues

1. **Tests Hanging**
   - Check for infinite loops in hook scripts
   - Verify timeout configurations
   - Look for missing exit conditions

2. **Permission Errors**
   - Ensure hook scripts are executable (`chmod +x`)
   - Check temporary directory permissions
   - Verify file creation permissions

3. **Configuration Errors**
   - Validate TOML syntax
   - Check file paths in configuration
   - Verify hook type specifications

4. **Environment Issues**
   - Ensure Node.js and npm are installed
   - Check Vitest configuration
   - Verify test dependencies

### Getting Help

1. **Check Test Output**
   ```bash
   ./run_hooks_e2e_tests.sh verbose
   ```

2. **Review Test Logs**
   ```bash
   find /tmp -name "*hooks-test-*" -type d
   ```

3. **Run Individual Tests**
   ```bash
   npm test -- hooks-e2e --grep "specific test name"
   ```

4. **Check Dependencies**
   ```bash
   npm list
   node --version
   ```

## Future Enhancements

### 1. Real Backend Integration
- Connect to actual Rust hook execution
- Test complete CLI → Rust → Hook flow
- Validate hook results and metrics

### 2. Advanced Testing
- Load testing with many hooks
- Stress testing with complex configurations
- Integration with real external services

### 3. Test Automation
- Automated test generation
- Property-based testing
- Mutation testing for robustness

### 4. Monitoring and Metrics
- Test execution time tracking
- Hook performance benchmarking
- Resource usage monitoring

## Conclusion

The E2E testing suite provides comprehensive coverage of the hooks system integration with the CLI. While some tests currently use mocks and simulations, the framework is designed to easily integrate with the real Rust backend as it becomes available.

The tests ensure that:
- Hook events are properly emitted from the CLI
- Configuration loading works correctly
- Error handling is robust
- Performance is acceptable
- Integration points are well-defined

This testing foundation will support the continued development and maintenance of the hooks system.
