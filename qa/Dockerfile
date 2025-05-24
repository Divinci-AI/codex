# Codex QA Automation Container
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /workspace/qa

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic utilities
    curl \
    wget \
    git \
    unzip \
    jq \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    # Network tools
    netcat-openbsd \
    telnet \
    nmap \
    # Security tools
    gnupg2 \
    ca-certificates \
    # Browser dependencies for Playwright
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Docker CLI for container management
    docker.io \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r qauser && useradd -r -g qauser -d /workspace/qa -s /bin/bash qauser

# Install Node.js for Codex CLI integration
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium \
    && playwright install-deps chromium

# Copy QA system files
COPY . .

# Create necessary directories
RUN mkdir -p \
    /workspace/qa/logs \
    /workspace/qa/reports \
    /workspace/qa/test-data \
    /workspace/qa/fixtures \
    /workspace/qa/backups \
    /workspace/qa/tmp

# Set up proper permissions
RUN chown -R qauser:qauser /workspace/qa \
    && chmod +x /workspace/qa/run_qa.py \
    && chmod +x /workspace/qa/scripts/*.sh

# Install Codex CLI (if available)
RUN if [ -f "/workspace/codex-cli/dist/codex.tgz" ]; then \
        npm install -g /workspace/codex-cli/dist/codex.tgz; \
    fi

# Create entrypoint script
RUN cat > /workspace/qa/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

# Initialize logging
mkdir -p /workspace/qa/logs
touch /workspace/qa/logs/qa.log

# Set up environment
export PYTHONPATH="/workspace/qa:$PYTHONPATH"
export PATH="/workspace/qa/scripts:$PATH"

# Validate environment
python -c "import autogen_agentchat, autogen_ext; print('Magentic-One dependencies OK')"
python -c "import playwright; print('Playwright OK')"

# Run health check
python /workspace/qa/scripts/health_check.py

# Execute the main command
exec "$@"
EOF

RUN chmod +x /workspace/qa/entrypoint.sh

# Security hardening
RUN echo "qauser ALL=(ALL) NOPASSWD: /usr/bin/docker" >> /etc/sudoers \
    && echo "qauser ALL=(ALL) NOPASSWD: /bin/kill" >> /etc/sudoers

# Switch to non-root user
USER qauser

# Set up Python path
ENV PYTHONPATH="/workspace/qa:$PYTHONPATH"

# Expose ports for webhook testing
EXPOSE 8080 8081 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /workspace/qa/scripts/health_check.py || exit 1

# Set entrypoint
ENTRYPOINT ["/workspace/qa/entrypoint.sh"]

# Default command
CMD ["python", "run_qa.py", "--help"]
