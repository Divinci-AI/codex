# Hook System Testing Guide

This document describes the comprehensive test suite for the Codex hook system.

## Test Structure

The hook system tests are organized into several modules:

### 1. Unit Tests (`tests.rs`)
- **Manager Tests**: Test `HookManager` creation, configuration, and basic functionality
- **Executor Tests**: Test individual hook executors (Script, Webhook, MCP)
- **Timeout and Error Tests**: Test error handling, timeouts, and failure scenarios
- **Execution Results Tests**: Test result aggregation and metrics collection

### 2. Executor-Specific Tests (`executors/tests.rs`)
- **ScriptExecutor Tests**: Command execution, environment variables, timeouts
- **WebhookExecutor Tests**: HTTP request handling, retries, configuration
- **McpToolExecutor Tests**: MCP tool calls, argument handling
- **Trait Implementation Tests**: Verify all executors implement required traits

### 3. Integration Tests (`integration_tests.rs`)
- **End-to-End Workflows**: Complete hook execution flows
- **Multi-Hook Coordination**: Parallel vs sequential execution
- **Real Event Processing**: Test with actual lifecycle events
- **Performance and Metrics**: Execution time tracking and success rates
- **Error Handling**: Critical failures, timeouts, recovery

## Running Tests

### Prerequisites
Ensure you have Rust and Cargo installed:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### Run All Hook Tests
```bash
cd codex-rs
cargo test hooks
```

### Run Specific Test Modules
```bash
# Unit tests only
cargo test hooks::tests

# Executor tests only
cargo test hooks::executors::tests

# Integration tests only
cargo test hooks::integration_tests
```

### Run Individual Test Functions
```bash
# Test hook manager creation
cargo test test_hook_manager_creation

# Test script executor
cargo test test_script_executor_execution

# Test timeout handling
cargo test test_script_timeout
```

### Run Tests with Output
```bash
# Show test output (useful for debugging)
cargo test hooks -- --nocapture

# Show test output and run ignored tests
cargo test hooks -- --nocapture --ignored
```

## Test Coverage

### What's Tested

#### ✅ Core Functionality
- [x] Hook manager creation and configuration
- [x] Hook execution coordination
- [x] Event subscription and routing
- [x] Executor selection and delegation
- [x] Result aggregation and metrics

#### ✅ Individual Executors
- [x] ScriptExecutor: Command execution, environment, timeouts
- [x] WebhookExecutor: HTTP requests, headers, retries
- [x] McpToolExecutor: Tool calls, argument handling
- [x] ExecutableExecutor: Basic interface (placeholder implementation)

#### ✅ Error Handling
- [x] Hook execution failures
- [x] Timeout handling and cancellation
- [x] Invalid configurations
- [x] Network failures (webhook)
- [x] Critical vs non-critical failures

#### ✅ Performance & Metrics
- [x] Execution time tracking
- [x] Success/failure rates
- [x] Parallel vs sequential execution
- [x] Resource usage monitoring

#### ✅ Integration Scenarios
- [x] Multiple hooks for same event
- [x] Different hook types in same workflow
- [x] Priority-based execution ordering
- [x] Conditional hook execution
- [x] Working directory handling

### What's Not Tested (Future Work)

#### 🔄 Advanced Features
- [ ] Hook dependency chains
- [ ] Dynamic hook registration
- [ ] Hook hot-reloading
- [ ] Advanced retry strategies
- [ ] Circuit breaker patterns

#### 🔄 Real-World Scenarios
- [ ] Large-scale hook execution (100+ hooks)
- [ ] Long-running hook processes
- [ ] Memory usage under load
- [ ] Concurrent event processing
- [ ] Hook execution in sandboxed environments

#### 🔄 External Integrations
- [ ] Real MCP server integration
- [ ] Webhook server mocking
- [ ] File system hook triggers
- [ ] Database integration hooks

## Test Utilities and Helpers

### Configuration Helpers
```rust
// Create basic test configuration
let config = create_test_config();

// Create configuration with hooks
let config = create_test_config_with_hooks();

// Create configuration for timeout testing
let config = create_timeout_test_config();
```

### Context Helpers
```rust
// Create test context for script execution
let context = create_script_context(vec!["echo", "test"]);

// Create test context for webhook execution
let context = create_webhook_context("https://example.com", HttpMethod::Post);

// Create test context for MCP execution
let context = create_mcp_context("server", "tool");
```

### Event Helpers
```rust
// Create test lifecycle events
let event = LifecycleEvent::SessionStart { ... };
let event = LifecycleEvent::TaskComplete { ... };
let event = LifecycleEvent::ErrorOccurred { ... };
```

## Adding New Tests

### 1. Unit Tests for New Features
When adding new functionality to the hook system:

1. Add tests to the appropriate module in `tests.rs`
2. Test both success and failure scenarios
3. Include edge cases and boundary conditions
4. Verify error messages are helpful

Example:
```rust
#[tokio::test]
async fn test_new_feature() {
    let manager = HookManager::new(config).await.unwrap();
    let result = manager.new_feature().await;
    assert!(result.is_ok());
}
```

### 2. Executor Tests for New Hook Types
When adding a new hook executor:

1. Create tests in `executors/tests.rs`
2. Test the `can_execute()` method
3. Test successful execution
4. Test failure scenarios
5. Test timeout behavior
6. Verify trait implementation

Example:
```rust
#[tokio::test]
async fn test_new_executor_basic() {
    let executor = NewExecutor::new();
    assert_eq!(executor.executor_type(), "new_type");
    
    let context = create_new_context();
    assert!(executor.can_execute(&context));
}
```

### 3. Integration Tests for Workflows
When adding new event types or workflows:

1. Add tests to `integration_tests.rs`
2. Test complete end-to-end scenarios
3. Verify metrics collection
4. Test error propagation
5. Include performance considerations

Example:
```rust
#[tokio::test]
async fn test_new_workflow() {
    let config = create_workflow_config();
    let manager = HookManager::new(config).await.unwrap();
    
    let event = LifecycleEvent::NewEvent { ... };
    let result = manager.trigger_event(event).await;
    
    assert!(result.is_ok());
    verify_metrics(&manager);
}
```

## Test Environment Setup

### Temporary Directories
Many tests use temporary directories for isolation:
```rust
use tempfile::TempDir;

let temp_dir = TempDir::new().unwrap();
let manager = HookManager::new_with_working_directory(
    config,
    temp_dir.path().to_path_buf(),
).await.unwrap();
```

### Mock Servers
For webhook testing, consider using `wiremock`:
```rust
use wiremock::{MockServer, Mock, ResponseTemplate};

let mock_server = MockServer::start().await;
Mock::given(method("POST"))
    .respond_with(ResponseTemplate::new(200))
    .mount(&mock_server)
    .await;
```

### Environment Variables
Some tests may need specific environment variables:
```rust
std::env::set_var("TEST_VAR", "test_value");
// Run test
std::env::remove_var("TEST_VAR");
```

## Debugging Tests

### Enable Logging
```bash
RUST_LOG=debug cargo test hooks -- --nocapture
```

### Run Single Test with Debugging
```bash
RUST_LOG=trace cargo test test_specific_function -- --nocapture --exact
```

### Use Test Output
```rust
#[tokio::test]
async fn test_with_debug() {
    let result = some_operation().await;
    println!("Debug: {:?}", result);
    assert!(result.is_ok());
}
```

## Continuous Integration

### Test Commands for CI
```bash
# Run all tests
cargo test

# Run tests with coverage
cargo test --all-features

# Run tests in release mode
cargo test --release

# Check for test compilation without running
cargo test --no-run
```

### Performance Benchmarks
Consider adding benchmark tests for performance-critical paths:
```rust
#[cfg(test)]
mod benches {
    use super::*;
    use std::time::Instant;
    
    #[tokio::test]
    async fn bench_hook_execution() {
        let start = Instant::now();
        // Execute hooks
        let duration = start.elapsed();
        assert!(duration < Duration::from_millis(100));
    }
}
```

## Best Practices

1. **Isolation**: Each test should be independent and not affect others
2. **Cleanup**: Use temporary directories and clean up resources
3. **Deterministic**: Tests should produce consistent results
4. **Fast**: Keep tests fast to encourage frequent running
5. **Readable**: Test names should clearly describe what's being tested
6. **Comprehensive**: Cover both happy path and error scenarios

## Troubleshooting

### Common Issues

1. **Tests hanging**: Check for infinite loops or missing timeouts
2. **Flaky tests**: Look for race conditions or timing dependencies
3. **Resource leaks**: Ensure proper cleanup of files, processes, etc.
4. **Platform differences**: Consider OS-specific behavior in scripts

### Getting Help

1. Check test output with `--nocapture`
2. Enable debug logging with `RUST_LOG=debug`
3. Run individual tests to isolate issues
4. Review the test implementation for edge cases
