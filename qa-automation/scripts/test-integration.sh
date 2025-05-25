#!/bin/bash
"""
Integration Test Script for AutoAgent System

This script tests the complete integration between Codex CLI,
the AutoGen server, and the Magentic-One QA system.
"""

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QA_ROOT="$PROJECT_ROOT/qa-automation"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test configuration
AUTOGEN_SERVER_URL="http://localhost:5000"
TEST_SESSION_ID="test-$(date +%s)"
TEST_TIMEOUT=30

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites for integration test..."
    
    # Check if AutoGen server is running
    if ! curl -s "$AUTOGEN_SERVER_URL/health" >/dev/null 2>&1; then
        error "AutoGen server is not running at $AUTOGEN_SERVER_URL"
        log "Please start the server with: ./scripts/start-autogen-server.sh"
        exit 1
    fi
    
    # Check required tools
    for tool in curl jq; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check environment variables
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        error "OPENAI_API_KEY environment variable is required"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Test AutoGen server health
test_server_health() {
    log "Testing AutoGen server health..."
    
    local response
    response=$(curl -s "$AUTOGEN_SERVER_URL/health")
    
    if echo "$response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
        success "AutoGen server is healthy"
        
        # Display server info
        local components
        components=$(echo "$response" | jq -r '.components | to_entries[] | "\(.key): \(.value)"')
        log "Server components:"
        echo "$components" | while read -r line; do
            log "  - $line"
        done
    else
        error "AutoGen server health check failed"
        log "Response: $response"
        exit 1
    fi
}

# Test webhook endpoint
test_webhook_endpoint() {
    log "Testing webhook endpoint..."
    
    # Create test event payload
    local payload
    payload=$(jq -n \
        --arg eventType "test_event" \
        --arg sessionId "$TEST_SESSION_ID" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            eventType: $eventType,
            sessionId: $sessionId,
            timestamp: $timestamp,
            context: {
                model: "test-model",
                workingDirectory: "/tmp/test",
                eventData: {
                    test: true,
                    message: "Integration test event"
                }
            }
        }'
    )
    
    log "Sending test webhook..."
    local response
    response=$(curl -s \
        --max-time "$TEST_TIMEOUT" \
        --header "Content-Type: application/json" \
        --data "$payload" \
        "$AUTOGEN_SERVER_URL/webhook/codex")
    
    if echo "$response" | jq -e '.status == "received"' >/dev/null 2>&1; then
        success "Webhook endpoint test passed"
        
        local event_id
        event_id=$(echo "$response" | jq -r '.event_id')
        log "Event ID: $event_id"
    else
        error "Webhook endpoint test failed"
        log "Response: $response"
        exit 1
    fi
}

# Test session management
test_session_management() {
    log "Testing session management..."
    
    # Get active sessions
    local sessions_response
    sessions_response=$(curl -s "$AUTOGEN_SERVER_URL/sessions")
    
    if echo "$sessions_response" | jq -e '.active_sessions >= 0' >/dev/null 2>&1; then
        success "Session management test passed"
        
        local active_count
        active_count=$(echo "$sessions_response" | jq -r '.active_sessions')
        log "Active sessions: $active_count"
        
        # Check if our test session exists
        if echo "$sessions_response" | jq -e --arg sid "$TEST_SESSION_ID" '.sessions[] | select(.session_id == $sid)' >/dev/null 2>&1; then
            log "Test session found in active sessions"
            
            # Get session details
            local session_details
            session_details=$(curl -s "$AUTOGEN_SERVER_URL/sessions/$TEST_SESSION_ID")
            
            if echo "$session_details" | jq -e '.session_id' >/dev/null 2>&1; then
                success "Session details retrieved successfully"
                
                local status
                status=$(echo "$session_details" | jq -r '.status // "unknown"')
                log "Session status: $status"
            else
                warning "Could not retrieve session details"
            fi
        else
            log "Test session not found (may have been processed already)"
        fi
    else
        error "Session management test failed"
        log "Response: $sessions_response"
        exit 1
    fi
}

# Test lifecycle hook script
test_lifecycle_hook() {
    log "Testing lifecycle hook script..."
    
    # Set up environment for hook script
    export CODEX_EVENT_TYPE="test_integration"
    export CODEX_SESSION_ID="$TEST_SESSION_ID-hook"
    export CODEX_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    export CODEX_MODEL="test-model"
    export CODEX_WORKING_DIR="$PROJECT_ROOT"
    export AUTOGEN_SERVER_URL="$AUTOGEN_SERVER_URL"
    
    # Create test event data
    local test_data='{"test": true, "integration_test": "lifecycle_hook"}'
    
    # Run the hook script
    if echo "$test_data" | "$QA_ROOT/hooks/autogen-integration.sh"; then
        success "Lifecycle hook test passed"
    else
        error "Lifecycle hook test failed"
        exit 1
    fi
}

# Test QA system components
test_qa_components() {
    log "Testing QA system components..."
    
    # Test if QA system can be imported
    if python3 -c "
import sys
sys.path.append('$QA_ROOT')
sys.path.append('$QA_ROOT/agents')
sys.path.append('$QA_ROOT/safety')

try:
    from integrated_qa_system import IntegratedCodexHooksQASystem
    from safety_integration import SafetyIntegrationSystem
    print('QA system components imported successfully')
except ImportError as e:
    print(f'QA system import failed: {e}')
    exit(1)
"; then
        success "QA system components test passed"
    else
        error "QA system components test failed"
        exit 1
    fi
}

# Cleanup test session
cleanup_test_session() {
    log "Cleaning up test session..."
    
    # Try to cleanup the test session
    if curl -s -X DELETE "$AUTOGEN_SERVER_URL/sessions/$TEST_SESSION_ID" >/dev/null 2>&1; then
        success "Test session cleaned up"
    else
        warning "Could not cleanup test session (may not exist)"
    fi
}

# Main test execution
main() {
    log "Starting AutoAgent Integration Test"
    log "=================================="
    
    # Run all tests
    check_prerequisites
    test_server_health
    test_webhook_endpoint
    test_session_management
    test_lifecycle_hook
    test_qa_components
    
    # Cleanup
    cleanup_test_session
    
    success "All integration tests passed!"
    log ""
    log "✅ AutoAgent system is ready for use"
    log ""
    log "Next steps:"
    log "1. Copy the hooks configuration: cp qa-automation/config/hooks-autogen.toml ~/.codex/hooks.toml"
    log "2. Run Codex with QA integration: codex 'create a simple web app'"
    log "3. Monitor the AutoGen server logs for QA analysis results"
}

# Handle interruption
trap 'error "Test interrupted"; cleanup_test_session; exit 1' INT TERM

# Run main function
main "$@"
