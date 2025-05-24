#!/bin/bash

# Hooks E2E Test Runner for CLI
# This script runs end-to-end tests for the hooks system integration with the CLI

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

# Function to check if required tools are available
check_dependencies() {
    local missing_deps=()
    
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install Node.js and npm"
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

# Change to the codex-cli directory
cd "$(dirname "$0")"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "Not in the codex-cli directory. Please run this script from the codex-cli root."
    exit 1
fi

# Check dependencies
check_dependencies

# Parse command line arguments
case "${1:-all}" in
    "all")
        print_status "Running all hooks E2E tests..."
        run_test "Hooks E2E Tests" "npm test -- hooks-e2e"
        run_test "CLI Integration Tests" "npm test -- hooks-cli-integration"
        ;;
    
    "e2e")
        print_status "Running hooks E2E tests..."
        run_test "Hooks E2E Tests" "npm test -- hooks-e2e"
        ;;
    
    "integration")
        print_status "Running CLI integration tests..."
        run_test "CLI Integration Tests" "npm test -- hooks-cli-integration"
        ;;
    
    "events")
        print_status "Running hook event tests..."
        run_test "Hook Events Tests" "npm test -- hooks-e2e --grep 'Hook Event Integration'"
        ;;
    
    "config")
        print_status "Running configuration tests..."
        run_test "Configuration Tests" "npm test -- hooks-e2e --grep 'Hook Configuration Loading'"
        ;;
    
    "execution")
        print_status "Running hook execution tests..."
        run_test "Execution Tests" "npm test -- hooks-cli-integration --grep 'Hook Execution During CLI Operations'"
        ;;
    
    "webhook")
        print_status "Running webhook hook tests..."
        run_test "Webhook Tests" "npm test -- hooks-cli-integration --grep 'Webhook Hooks Integration'"
        ;;
    
    "mcp")
        print_status "Running MCP hook tests..."
        run_test "MCP Tests" "npm test -- hooks-cli-integration --grep 'MCP Tool Hooks Integration'"
        ;;
    
    "performance")
        print_status "Running performance tests..."
        run_test "Performance Tests" "npm test -- hooks-cli-integration --grep 'Performance and Scalability'"
        ;;
    
    "error-handling")
        print_status "Running error handling tests..."
        run_test "Error Handling Tests" "npm test -- hooks-cli-integration --grep 'Error Handling and Recovery'"
        ;;
    
    "verbose")
        print_status "Running all tests with verbose output..."
        run_test "Verbose E2E Tests" "npm test -- hooks-e2e --reporter=verbose"
        run_test "Verbose Integration Tests" "npm test -- hooks-cli-integration --reporter=verbose"
        ;;
    
    "watch")
        print_status "Running tests in watch mode..."
        print_warning "Press Ctrl+C to stop watching"
        npm test -- hooks-e2e hooks-cli-integration --watch
        ;;
    
    "coverage")
        print_status "Running tests with coverage..."
        if npm list --depth=0 | grep -q "@vitest/coverage"; then
            run_test "Coverage Tests" "npm test -- hooks-e2e hooks-cli-integration --coverage"
        else
            print_warning "Coverage package not found. Install with: npm install --save-dev @vitest/coverage-v8"
            run_test "Regular Tests" "npm test -- hooks-e2e hooks-cli-integration"
        fi
        ;;
    
    "setup")
        print_status "Setting up test environment..."
        
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            print_status "Installing npm dependencies..."
            npm install
        fi
        
        # Check if test files exist
        if [ ! -f "tests/hooks-e2e.test.ts" ]; then
            print_error "E2E test file not found: tests/hooks-e2e.test.ts"
            exit 1
        fi
        
        if [ ! -f "tests/hooks-cli-integration.test.ts" ]; then
            print_error "Integration test file not found: tests/hooks-cli-integration.test.ts"
            exit 1
        fi
        
        print_success "Test environment setup complete"
        ;;
    
    "clean")
        print_status "Cleaning test artifacts..."
        
        # Remove temporary test directories
        find /tmp -name "codex-*hooks-test-*" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Remove any test output files
        rm -f tests/*.log tests/*.marker 2>/dev/null || true
        
        print_success "Test artifacts cleaned"
        ;;
    
    "help"|"-h"|"--help")
        echo "Hooks E2E Test Runner for CLI"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  all             Run all hooks E2E tests (default)"
        echo "  e2e             Run hooks E2E tests only"
        echo "  integration     Run CLI integration tests only"
        echo "  events          Run hook event tests"
        echo "  config          Run configuration tests"
        echo "  execution       Run hook execution tests"
        echo "  webhook         Run webhook hook tests"
        echo "  mcp             Run MCP hook tests"
        echo "  performance     Run performance tests"
        echo "  error-handling  Run error handling tests"
        echo "  verbose         Run tests with verbose output"
        echo "  watch           Run tests in watch mode"
        echo "  coverage        Run tests with coverage report"
        echo "  setup           Set up test environment"
        echo "  clean           Clean test artifacts"
        echo "  help            Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 all              # Run all E2E tests"
        echo "  $0 e2e              # Run only E2E tests"
        echo "  $0 webhook          # Run only webhook tests"
        echo "  $0 watch            # Run tests in watch mode"
        echo "  $0 coverage         # Run tests with coverage"
        echo ""
        echo "Prerequisites:"
        echo "  - Node.js and npm installed"
        echo "  - Vitest test framework configured"
        echo "  - Hooks system implemented in CLI"
        echo ""
        ;;
    
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' to see available commands"
        exit 1
        ;;
esac

print_success "E2E test execution completed!"

# Additional information
echo ""
print_status "Test Information:"
echo "  - E2E tests verify hook event creation and emission"
echo "  - Integration tests verify CLI behavior with hooks enabled"
echo "  - Tests use temporary directories for isolation"
echo "  - Mock scripts simulate real hook execution"
echo ""
print_status "Next Steps:"
echo "  - Run 'npm test' to execute all tests"
echo "  - Check test output for any failures"
echo "  - Review test logs for hook execution details"
echo "  - Integrate with CI/CD pipeline for automated testing"
