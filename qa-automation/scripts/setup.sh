#!/bin/bash
# Setup script for Magentic-One QA Automation

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

# Check if running from correct directory
if [ ! -f "qa-automation/scripts/setup.sh" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Setting up Magentic-One QA Automation for Codex Hooks..."

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "Found Python $python_version"

# Check Node.js and pnpm
if ! command -v node &> /dev/null; then
    print_error "Node.js is required but not installed"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    print_error "pnpm is required but not installed"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    print_warning "Docker not found. Container isolation will not be available."
else
    print_status "Found Docker $(docker --version)"
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "qa-automation/venv" ]; then
    python3 -m venv qa-automation/venv
    print_success "Created virtual environment"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source qa-automation/venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r qa-automation/requirements.txt

# Install Playwright browsers
print_status "Installing Playwright browsers..."
playwright install chromium

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
cd codex-cli
pnpm install
pnpm run build
cd ..

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p qa-automation/{logs,output,reports,test-data}

# Copy environment configuration
if [ ! -f "qa-automation/config/.env" ]; then
    print_status "Creating environment configuration..."
    cp qa-automation/config/.env.example qa-automation/config/.env
    print_warning "Please edit qa-automation/config/.env with your OpenAI API key and other settings"
else
    print_status "Environment configuration already exists"
fi

# Set executable permissions
chmod +x qa-automation/scripts/*.sh
chmod +x qa-automation/magentic-one/*.py

# Create test data
print_status "Creating test data..."
cat > qa-automation/test-data/sample-hooks.toml << 'EOF'
# Sample hooks configuration for testing
[hooks]
enabled = true
timeout_seconds = 30

[[hooks.session]]
event = "session_start"
type = "script"
command = ["echo", "Session started: $CODEX_SESSION_ID"]
description = "Test session start hook"
enabled = true

[[hooks.session]]
event = "session_end"
type = "webhook"
url = "http://localhost:8080/webhook/test"
description = "Test session end webhook"
enabled = true
EOF

# Create a simple test script
cat > qa-automation/test-data/test-hook.sh << 'EOF'
#!/bin/bash
echo "Test hook executed successfully"
echo "Event: $CODEX_EVENT_TYPE"
echo "Session: $CODEX_SESSION_ID"
echo "Timestamp: $CODEX_TIMESTAMP"
exit 0
EOF
chmod +x qa-automation/test-data/test-hook.sh

# Validate installation
print_status "Validating installation..."

# Test Python imports
python3 -c "
try:
    import autogen_agentchat
    import autogen_ext
    print('✓ AutoGen packages imported successfully')
except ImportError as e:
    print(f'✗ AutoGen import failed: {e}')
    exit(1)
"

# Test Playwright
python3 -c "
try:
    from playwright.sync_api import sync_playwright
    print('✓ Playwright imported successfully')
except ImportError as e:
    print(f'✗ Playwright import failed: {e}')
    exit(1)
"

print_success "Magentic-One QA Automation setup completed successfully!"

echo ""
echo "Next steps:"
echo "1. Edit qa-automation/config/.env with your OpenAI API key"
echo "2. Run the QA orchestrator: python qa-automation/magentic-one/qa_orchestrator.py"
echo "3. Or use Docker: cd qa-automation/docker && docker-compose -f docker-compose.qa.yml up"
echo ""
echo "For more information, see qa-automation/README.md"
