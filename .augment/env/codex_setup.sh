#!/bin/bash
set -euo pipefail

echo "Setting up Codex development environment..."

# Update system packages
sudo apt-get update

# Install Node.js 22 (required by package.json engines)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install pnpm globally (version 10.8.1 as specified in package.json)
sudo npm install -g pnpm@10.8.1

# Install Rust and Cargo
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env

# Install required system dependencies for Rust compilation
sudo apt-get install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    libc6-dev

# Add Rust to PATH in user's profile instead of system-wide
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc

# Enable corepack for pnpm with sudo
sudo corepack enable

# Change to workspace directory
cd /mnt/persist/workspace

# Install Node.js dependencies using pnpm
pnpm install

# Build the TypeScript CLI
pnpm --filter @openai/codex run build

# Build the Rust workspace (in the codex-rs directory)
cd codex-rs
cargo build

echo "Development environment setup complete!"
echo "Available commands:"
echo "  - TypeScript tests: pnpm --filter @openai/codex run test"
echo "  - Rust tests: cargo test"
echo "  - Build TypeScript: pnpm --filter @openai/codex run build"
echo "  - Build Rust: cargo build"