#!/bin/bash
"""
AutoGen Server Startup Script

This script starts the AutoGen server that receives Codex lifecycle
hook callbacks and coordinates with the Magentic-One QA system.
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
NC='\033[0m' # No Color

# Logging function
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

# Configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="5000"
DEFAULT_CONFIG="$QA_ROOT/config/autogen-server.json"

# Parse command line arguments
HOST="${1:-$DEFAULT_HOST}"
PORT="${2:-$DEFAULT_PORT}"
CONFIG_FILE="${3:-$DEFAULT_CONFIG}"

# Environment setup
export PYTHONPATH="$QA_ROOT:$QA_ROOT/agents:$QA_ROOT/safety:$PYTHONPATH"

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required environment variables
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        error "OPENAI_API_KEY environment variable is required"
        exit 1
    fi
    
    # Check if port is available
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        error "Port $PORT is already in use"
        exit 1
    fi
    
    # Check required directories
    if [ ! -d "$QA_ROOT" ]; then
        error "QA automation directory not found: $QA_ROOT"
        exit 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$QA_ROOT/logs"
    
    success "Prerequisites check passed"
}

# Install dependencies
install_dependencies() {
    log "Installing/checking dependencies..."
    
    # Check if FastAPI is installed
    if ! python3 -c "import fastapi" 2>/dev/null; then
        log "Installing FastAPI..."
        pip install fastapi uvicorn
    fi
    
    # Check if AutoGen is installed
    if ! python3 -c "import autogen_ext" 2>/dev/null; then
        error "AutoGen extensions not found. Please install with: pip install autogen-ext"
        exit 1
    fi
    
    success "Dependencies ready"
}

# Start the server
start_server() {
    log "Starting AutoGen server..."
    log "Host: $HOST"
    log "Port: $PORT"
    log "Config: $CONFIG_FILE"
    log "Working Directory: $PROJECT_ROOT"
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export AUTOGEN_CONFIG="$CONFIG_FILE"
    export AUTOGEN_HOST="$HOST"
    export AUTOGEN_PORT="$PORT"
    
    # Start the server
    python3 "$QA_ROOT/server/autogen_server.py" 2>&1 | tee "$QA_ROOT/logs/server_startup.log"
}

# Signal handlers for graceful shutdown
cleanup() {
    log "Shutting down AutoGen server..."
    # Kill any background processes
    jobs -p | xargs -r kill
    exit 0
}

trap cleanup SIGINT SIGTERM

# Main execution
main() {
    log "Starting AutoGen Server for Codex Integration"
    log "============================================="
    
    check_prerequisites
    install_dependencies
    
    # Create PID file
    echo $$ > "$QA_ROOT/logs/autogen_server.pid"
    
    # Start server
    start_server
}

# Help function
show_help() {
    cat << EOF
AutoGen Server Startup Script

Usage: $0 [HOST] [PORT] [CONFIG_FILE]

Arguments:
  HOST         Server host (default: $DEFAULT_HOST)
  PORT         Server port (default: $DEFAULT_PORT)
  CONFIG_FILE  Configuration file path (default: $DEFAULT_CONFIG)

Environment Variables:
  OPENAI_API_KEY    Required: OpenAI API key for the QA system
  AUTOGEN_CONFIG    Optional: Override config file path
  PYTHONPATH        Automatically set to include QA modules

Examples:
  $0                                    # Start with defaults
  $0 localhost 8000                    # Custom host and port
  $0 0.0.0.0 5000 /path/to/config.json # Full custom configuration

The server will:
1. Listen for Codex lifecycle hook webhooks
2. Coordinate with Magentic-One QA system
3. Provide real-time QA analysis and feedback
4. Maintain session state and logging

Server endpoints:
  GET  /                    - Server status
  GET  /health             - Health check
  POST /webhook/codex      - Codex lifecycle events
  POST /webhook/qa-complete - QA completion notifications
  GET  /sessions           - Active sessions
  GET  /sessions/{id}      - Session details

Logs are written to: $QA_ROOT/logs/
EOF
}

# Check for help flag
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"
