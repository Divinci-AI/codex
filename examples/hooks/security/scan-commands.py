#!/usr/bin/env python3
"""
Command Security Scanner Hook
This script scans commands for potentially dangerous operations
"""

import os
import sys
import re
import json
from datetime import datetime

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    # File system operations
    r'\brm\s+(-[rf]*\s+)?/',  # rm with root paths
    r'\brm\s+(-[rf]*\s+)?\*',  # rm with wildcards
    r'\bchmod\s+777',  # overly permissive permissions
    r'\bchown\s+.*root',  # changing ownership to root
    
    # Network operations
    r'\bcurl\s+.*\|\s*sh',  # piping curl to shell
    r'\bwget\s+.*\|\s*sh',  # piping wget to shell
    r'\bnc\s+.*-e',  # netcat with execute
    
    # System operations
    r'\bsudo\s+rm',  # sudo rm
    r'\bsu\s+root',  # switching to root
    r'\bmkfs\.',  # formatting filesystems
    r'\bdd\s+.*of=/dev/',  # writing to devices
    
    # Package management
    r'\bapt\s+install.*--force',  # forced package installation
    r'\byum\s+install.*--skip-broken',  # skipping dependency checks
    
    # Process operations
    r'\bkill\s+-9\s+1',  # killing init process
    r'\bkillall\s+-9',  # force killing all processes
    
    # Archive operations
    r'\btar\s+.*--absolute-names',  # tar with absolute paths
    r'\bunzip.*\|\s*sh',  # piping unzip to shell
]

# Warning patterns (less severe)
WARNING_PATTERNS = [
    r'\bsudo\s+',  # any sudo usage
    r'\bchmod\s+[0-7]*[4-7][0-7]*',  # world-readable permissions
    r'\bcp\s+.*--force',  # forced copy operations
    r'\bmv\s+.*/',  # moving files to directories
    r'\bfind\s+.*-exec',  # find with exec
]

def analyze_command(command_str):
    """Analyze a command for security issues"""
    issues = []
    warnings = []
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command_str, re.IGNORECASE):
            issues.append({
                'type': 'danger',
                'pattern': pattern,
                'description': f'Potentially dangerous command pattern: {pattern}'
            })
    
    # Check for warning patterns
    for pattern in WARNING_PATTERNS:
        if re.search(pattern, command_str, re.IGNORECASE):
            warnings.append({
                'type': 'warning',
                'pattern': pattern,
                'description': f'Potentially risky command pattern: {pattern}'
            })
    
    return issues, warnings

def log_scan_result(command, issues, warnings):
    """Log the scan result"""
    log_file = os.path.expanduser('~/.codex/security.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    session_id = os.getenv('CODEX_SESSION_ID', 'unknown')
    
    log_entry = {
        'timestamp': timestamp,
        'session_id': session_id,
        'command': command,
        'issues': issues,
        'warnings': warnings,
        'risk_level': 'high' if issues else ('medium' if warnings else 'low')
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def main():
    """Main function"""
    event_type = os.getenv('CODEX_EVENT_TYPE', '')
    
    # Only scan command start events
    if event_type != 'command_start':
        return
    
    # Get command from environment
    command_env = os.getenv('CODEX_COMMAND', '')
    if not command_env:
        print("Warning: No command found in CODEX_COMMAND")
        return
    
    # Parse command (it might be JSON array)
    try:
        if command_env.startswith('['):
            command_parts = json.loads(command_env)
            command_str = ' '.join(command_parts)
        else:
            command_str = command_env
    except json.JSONDecodeError:
        command_str = command_env
    
    # Analyze the command
    issues, warnings = analyze_command(command_str)
    
    # Log the result
    log_scan_result(command_str, issues, warnings)
    
    # Report findings
    if issues:
        print(f"🚨 SECURITY ALERT: Dangerous command detected!")
        print(f"Command: {command_str}")
        for issue in issues:
            print(f"  - {issue['description']}")
        print(f"Logged to ~/.codex/security.log")
        
        # Optionally exit with error to prevent execution
        # Uncomment the next line to block dangerous commands
        # sys.exit(1)
    
    elif warnings:
        print(f"⚠️  Security warning for command: {command_str}")
        for warning in warnings:
            print(f"  - {warning['description']}")
        print(f"Logged to ~/.codex/security.log")
    
    else:
        print(f"✅ Command security scan passed: {command_str}")

if __name__ == "__main__":
    main()
