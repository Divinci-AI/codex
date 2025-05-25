#!/bin/bash
# Quick test runner for Magentic-One QA Automation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running from correct directory
if [ ! -f "qa-automation/scripts/run-qa.sh" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Parse command line arguments
PHASE="all"
CONTAINER="false"
DEBUG="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase)
            PHASE="$2"
            shift 2
            ;;
        --container)
            CONTAINER="true"
            shift
            ;;
        --debug)
            DEBUG="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --phase PHASE     Run specific phase: config, functional, performance, security, integration, all"
            echo "  --container       Run in Docker container"
            echo "  --debug           Enable debug logging"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all phases"
            echo "  $0 --phase config                     # Run configuration validation only"
            echo "  $0 --container                        # Run in Docker container"
            echo "  $0 --phase functional --debug         # Run functional tests with debug logging"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Starting Magentic-One QA Automation..."
print_status "Phase: $PHASE"
print_status "Container: $CONTAINER"
print_status "Debug: $DEBUG"

# Set environment variables
if [ "$DEBUG" = "true" ]; then
    export QA_DEBUG=true
    export AUTOGEN_DEBUG=true
    export PYTHONPATH=$(pwd)
fi

# Check prerequisites
if [ "$CONTAINER" = "false" ]; then
    # Check if virtual environment exists
    if [ ! -d "qa-automation/venv" ]; then
        print_error "Virtual environment not found. Please run setup.sh first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "qa-automation/config/.env" ]; then
        print_error "Environment configuration not found. Please copy .env.example to .env and configure it."
        exit 1
    fi
    
    # Load environment variables
    source qa-automation/config/.env
    
    # Check OpenAI API key
    if [ -z "$OPENAI_API_KEY" ]; then
        print_error "OPENAI_API_KEY not set in environment"
        exit 1
    fi
    
    # Activate virtual environment
    source qa-automation/venv/bin/activate
fi

# Create timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_ID="qa-run-$TIMESTAMP"

print_status "Run ID: $RUN_ID"

# Function to run specific phase
run_phase() {
    local phase=$1
    print_status "Running phase: $phase"
    
    if [ "$CONTAINER" = "true" ]; then
        # Run in Docker container
        cd qa-automation/docker
        docker-compose -f docker-compose.qa.yml run --rm \
            -e QA_PHASE="$phase" \
            -e QA_RUN_ID="$RUN_ID" \
            magentic-one-qa \
            python qa-automation/magentic-one/qa_orchestrator.py --phase "$phase"
        cd ../..
    else
        # Run directly
        python qa-automation/magentic-one/qa_orchestrator.py --phase "$phase" --run-id "$RUN_ID"
    fi
}

# Start webhook test server if needed
if [ "$PHASE" = "all" ] || [ "$PHASE" = "functional" ] || [ "$PHASE" = "integration" ]; then
    if [ "$CONTAINER" = "false" ]; then
        print_status "Starting webhook test server..."
        python -c "
from fastapi import FastAPI, Request
import uvicorn
import json
from datetime import datetime
import threading
import time

app = FastAPI()

@app.post('/webhook/test')
async def test_webhook(request: Request):
    body = await request.json()
    print(f'[{datetime.now()}] Received webhook: {json.dumps(body, indent=2)}')
    return {'status': 'success', 'received_at': datetime.now().isoformat()}

@app.get('/health')
async def health():
    return {'status': 'healthy'}

def run_server():
    uvicorn.run(app, host='127.0.0.1', port=8080, log_level='warning')

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2)  # Give server time to start
print('Webhook test server started on http://127.0.0.1:8080')
" &
        WEBHOOK_PID=$!
        sleep 3  # Give server time to start
    fi
fi

# Run the specified phase(s)
case $PHASE in
    "config")
        run_phase "configuration"
        ;;
    "functional")
        run_phase "functional"
        ;;
    "performance")
        run_phase "performance"
        ;;
    "security")
        run_phase "security"
        ;;
    "integration")
        run_phase "integration"
        ;;
    "all")
        print_status "Running comprehensive QA testing..."
        if [ "$CONTAINER" = "true" ]; then
            cd qa-automation/docker
            docker-compose -f docker-compose.qa.yml up --abort-on-container-exit
            cd ../..
        else
            python qa-automation/magentic-one/qa_orchestrator.py --run-id "$RUN_ID"
        fi
        ;;
    *)
        print_error "Unknown phase: $PHASE"
        print_error "Valid phases: config, functional, performance, security, integration, all"
        exit 1
        ;;
esac

# Stop webhook server if we started it
if [ ! -z "$WEBHOOK_PID" ]; then
    kill $WEBHOOK_PID 2>/dev/null || true
fi

# Check results
RESULTS_FILE="qa-automation/reports/qa_results_${TIMESTAMP}.json"
if [ -f "$RESULTS_FILE" ]; then
    print_success "QA testing completed successfully!"
    print_status "Results saved to: $RESULTS_FILE"
    
    # Extract overall status
    OVERALL_STATUS=$(python -c "
import json
try:
    with open('$RESULTS_FILE', 'r') as f:
        data = json.load(f)
    print(data.get('overall_status', 'unknown'))
except:
    print('unknown')
")
    
    case $OVERALL_STATUS in
        "passed")
            print_success "Overall Status: PASSED ✅"
            ;;
        "passed_with_warnings")
            print_warning "Overall Status: PASSED WITH WARNINGS ⚠️"
            ;;
        "failed")
            print_error "Overall Status: FAILED ❌"
            exit 1
            ;;
        *)
            print_warning "Overall Status: UNKNOWN"
            ;;
    esac
else
    print_warning "Results file not found. Check logs for details."
fi

print_status "QA automation run completed."
