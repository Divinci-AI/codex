#!/bin/bash

# Hook System Test Runner
# This script provides convenient commands for running the hook system tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if cargo is available
check_cargo() {
    if ! command -v cargo &> /dev/null; then
        print_error "Cargo is not installed or not in PATH"
        print_error "Please install Rust: https://rustup.rs/"
        exit 1
    fi
}

# Function to run tests with proper error handling
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_status "Running $test_name..."
    
    if eval "$test_command"; then
        print_success "$test_name completed successfully"
        return 0
    else
        print_error "$test_name failed"
        return 1
    fi
}

# Change to the codex-rs directory
cd "$(dirname "$0")"

# Check if we're in the right directory
if [ ! -f "Cargo.toml" ]; then
    print_error "Not in the codex-rs directory. Please run this script from the codex-rs root."
    exit 1
fi

# Check cargo availability
check_cargo

# Parse command line arguments
case "${1:-all}" in
    "all")
        print_status "Running all hook system tests..."
        run_test "All Hook Tests" "cargo test hooks"
        ;;
    
    "unit")
        print_status "Running unit tests..."
        run_test "Unit Tests" "cargo test hooks::tests"
        ;;
    
    "executors")
        print_status "Running executor tests..."
        run_test "Executor Tests" "cargo test hooks::executors::tests"
        ;;
    
    "integration")
        print_status "Running integration tests..."
        run_test "Integration Tests" "cargo test hooks::integration_tests"
        ;;
    
    "manager")
        print_status "Running hook manager tests..."
        run_test "Manager Tests" "cargo test hooks::tests::manager_tests"
        ;;
    
    "script")
        print_status "Running script executor tests..."
        run_test "Script Executor Tests" "cargo test script_executor"
        ;;
    
    "webhook")
        print_status "Running webhook executor tests..."
        run_test "Webhook Executor Tests" "cargo test webhook_executor"
        ;;
    
    "mcp")
        print_status "Running MCP executor tests..."
        run_test "MCP Executor Tests" "cargo test mcp_executor"
        ;;
    
    "timeout")
        print_status "Running timeout and error handling tests..."
        run_test "Timeout Tests" "cargo test timeout"
        ;;
    
    "verbose")
        print_status "Running all tests with verbose output..."
        run_test "Verbose Tests" "cargo test hooks -- --nocapture"
        ;;
    
    "check")
        print_status "Checking test compilation without running..."
        run_test "Test Compilation Check" "cargo test hooks --no-run"
        ;;
    
    "coverage")
        print_status "Running tests with coverage (requires cargo-tarpaulin)..."
        if command -v cargo-tarpaulin &> /dev/null; then
            run_test "Coverage Tests" "cargo tarpaulin --out Html --output-dir coverage"
            print_success "Coverage report generated in coverage/tarpaulin-report.html"
        else
            print_warning "cargo-tarpaulin not found. Install with: cargo install cargo-tarpaulin"
            run_test "Regular Tests" "cargo test hooks"
        fi
        ;;
    
    "bench")
        print_status "Running performance benchmarks..."
        run_test "Benchmark Tests" "cargo test --release bench"
        ;;
    
    "help"|"-h"|"--help")
        echo "Hook System Test Runner"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  all         Run all hook system tests (default)"
        echo "  unit        Run unit tests only"
        echo "  executors   Run executor-specific tests"
        echo "  integration Run integration tests"
        echo "  manager     Run hook manager tests"
        echo "  script      Run script executor tests"
        echo "  webhook     Run webhook executor tests"
        echo "  mcp         Run MCP executor tests"
        echo "  timeout     Run timeout and error handling tests"
        echo "  verbose     Run tests with verbose output"
        echo "  check       Check test compilation without running"
        echo "  coverage    Run tests with coverage report"
        echo "  bench       Run performance benchmarks"
        echo "  help        Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 all              # Run all tests"
        echo "  $0 unit             # Run only unit tests"
        echo "  $0 script           # Run only script executor tests"
        echo "  $0 verbose          # Run tests with output"
        echo ""
        ;;
    
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' to see available commands"
        exit 1
        ;;
esac

print_success "Test execution completed!"
