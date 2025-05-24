#!/bin/bash
# Codex QA System Setup Script
# This script sets up the QA environment and dependencies

set -e

echo "🤖 Setting up Codex QA System..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "run_qa.py" ]; then
    print_error "Please run this script from the qa/ directory"
    exit 1
fi

# Create necessary directories
print_info "Creating directory structure..."
mkdir -p logs reports test-data tmp backups

# Set up Python virtual environment (optional)
if command -v python3 &> /dev/null; then
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        print_status "Virtual environment created"
    fi
    
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Python dependencies installed"
else
    print_warning "Python3 not found. Please install Python 3.9+ manually."
fi

# Install Playwright browsers
if command -v playwright &> /dev/null; then
    print_info "Installing Playwright browsers..."
    playwright install chromium
    print_status "Playwright browsers installed"
else
    print_warning "Playwright not found. Browser automation may not work."
fi

# Check Docker availability
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        print_status "Docker is available and running"
        
        # Build QA container
        print_info "Building QA container..."
        docker build -t codex-qa .
        print_status "QA container built successfully"
    else
        print_warning "Docker is installed but not running"
    fi
else
    print_warning "Docker not found. Container isolation will not be available."
fi

# Set up environment file
if [ ! -f ".env" ]; then
    print_info "Creating environment file..."
    cp .env.example .env
    print_warning "Please edit .env file with your OpenAI API key and other settings"
else
    print_status "Environment file already exists"
fi

# Make scripts executable
print_info "Setting script permissions..."
chmod +x run_qa.py
chmod +x scripts/health_check.py
find test-data/scripts -name "*.sh" -exec chmod +x {} \;
print_status "Script permissions set"

# Run health check
print_info "Running health check..."
if python3 scripts/health_check.py; then
    print_status "Health check passed"
else
    print_warning "Health check failed. Please review the issues above."
fi

# Create sample test data
print_info "Setting up test data..."
if [ ! -f "test-data/hooks/sample.toml" ]; then
    cat > test-data/hooks/sample.toml << 'EOF'
# Sample hooks configuration for testing
[hooks.sample_hook]
type = "script"
script = "/workspace/qa/test-data/scripts/sample.sh"
conditions = ["event_type == 'test'"]
description = "Sample hook for testing"
EOF
    print_status "Sample test data created"
fi

# Create sample script
if [ ! -f "test-data/scripts/sample.sh" ]; then
    cat > test-data/scripts/sample.sh << 'EOF'
#!/bin/bash
echo "Sample hook executed successfully"
echo "Timestamp: $(date)"
exit 0
EOF
    chmod +x test-data/scripts/sample.sh
    print_status "Sample script created"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OpenAI API key"
echo "2. Run: python run_qa.py --help"
echo "3. Try: python run_qa.py --suite hooks-validation"
echo ""
echo "For more information, see README.md"
