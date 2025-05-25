#!/bin/bash
"""
Install Test Dependencies

This script installs the required dependencies for running the AutoAgent test suite.
"""

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log "Installing AutoAgent Test Dependencies"
log "====================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    error "requirements.txt not found. Please run this script from the qa-automation directory."
    exit 1
fi

# Install core dependencies
log "Installing core dependencies..."
pip install -r requirements.txt

# Install additional test dependencies that might not be in requirements.txt
log "Installing additional test dependencies..."
pip install pytest-html pytest-xdist pytest-mock

# Verify installations
log "Verifying installations..."

# Check pytest
if python -c "import pytest" 2>/dev/null; then
    success "pytest installed"
else
    error "pytest installation failed"
    exit 1
fi

# Check pytest-asyncio
if python -c "import pytest_asyncio" 2>/dev/null; then
    success "pytest-asyncio installed"
else
    warning "pytest-asyncio not available - async tests will be skipped"
fi

# Check pytest-cov
if python -c "import pytest_cov" 2>/dev/null; then
    success "pytest-cov installed"
else
    warning "pytest-cov not available - coverage reports will not be generated"
fi

# Check requests
if python -c "import requests" 2>/dev/null; then
    success "requests installed"
else
    warning "requests not available - some integration tests will be skipped"
fi

# Check FastAPI
if python -c "import fastapi" 2>/dev/null; then
    success "fastapi installed"
else
    warning "fastapi not available - server tests will be limited"
fi

log "Running a quick test to verify the framework..."
python -m pytest tests/unit/test_framework.py::TestFramework::test_basic_assertion -v

if [ $? -eq 0 ]; then
    success "Test framework is working correctly!"
    log ""
    log "You can now run tests with:"
    log "  python tests/run_tests.py                    # Run all tests"
    log "  python tests/run_tests.py --quick            # Run only unit tests"
    log "  python tests/run_tests.py --coverage         # Run with coverage"
    log "  python -m pytest tests/unit/ -v              # Run unit tests directly"
else
    error "Test framework verification failed"
    exit 1
fi
