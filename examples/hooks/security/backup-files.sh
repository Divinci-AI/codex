#!/bin/bash
# File Backup Hook
# This script creates backups of important files before Codex sessions

# Configuration
BACKUP_DIR="${HOME}/.codex/backups"
MAX_BACKUPS=10  # Keep last 10 backups
BACKUP_PATTERNS=(
    "*.py"
    "*.js"
    "*.ts"
    "*.jsx"
    "*.tsx"
    "*.go"
    "*.rs"
    "*.java"
    "*.cpp"
    "*.c"
    "*.h"
    "*.hpp"
    "*.sh"
    "*.bash"
    "*.zsh"
    "*.fish"
    "Dockerfile"
    "docker-compose.yml"
    "package.json"
    "requirements.txt"
    "Cargo.toml"
    "go.mod"
    "pom.xml"
    "build.gradle"
    "Makefile"
    "CMakeLists.txt"
    "*.md"
    "*.yml"
    "*.yaml"
    "*.toml"
    "*.json"
    "*.xml"
    "*.ini"
    "*.conf"
    "*.config"
)

# Only run on session start
if [ "$CODEX_EVENT_TYPE" != "session_start" ]; then
    exit 0
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create session-specific backup directory
SESSION_BACKUP_DIR="$BACKUP_DIR/session_${CODEX_SESSION_ID}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SESSION_BACKUP_DIR"

echo "Creating backup for session $CODEX_SESSION_ID..."

# Function to backup files matching patterns
backup_files() {
    local pattern="$1"
    local count=0
    
    # Use find to locate files matching the pattern
    while IFS= read -r -d '' file; do
        # Skip if file is in .git, node_modules, or other common ignore directories
        if [[ "$file" == *"/.git/"* ]] || \
           [[ "$file" == *"/node_modules/"* ]] || \
           [[ "$file" == *"/.venv/"* ]] || \
           [[ "$file" == *"/venv/"* ]] || \
           [[ "$file" == *"/__pycache__/"* ]] || \
           [[ "$file" == *"/target/"* ]] || \
           [[ "$file" == *"/build/"* ]] || \
           [[ "$file" == *"/dist/"* ]]; then
            continue
        fi
        
        # Create directory structure in backup
        rel_path="${file#./}"
        backup_file="$SESSION_BACKUP_DIR/$rel_path"
        backup_dir=$(dirname "$backup_file")
        mkdir -p "$backup_dir"
        
        # Copy file
        cp "$file" "$backup_file" 2>/dev/null
        if [ $? -eq 0 ]; then
            ((count++))
        fi
    done < <(find . -name "$pattern" -type f -print0 2>/dev/null)
    
    echo "  Backed up $count files matching $pattern"
}

# Backup files for each pattern
total_files=0
for pattern in "${BACKUP_PATTERNS[@]}"; do
    backup_files "$pattern"
done

# Count total files backed up
total_files=$(find "$SESSION_BACKUP_DIR" -type f | wc -l)

if [ "$total_files" -gt 0 ]; then
    echo "✅ Backup completed: $total_files files backed up to $SESSION_BACKUP_DIR"
    
    # Create a manifest file
    cat > "$SESSION_BACKUP_DIR/MANIFEST.txt" << EOF
Codex Session Backup
===================
Session ID: $CODEX_SESSION_ID
Timestamp: $(date -Iseconds)
Working Directory: $(pwd)
Total Files: $total_files
Model: ${CODEX_MODEL:-unknown}
Provider: ${CODEX_PROVIDER:-openai}

Files backed up:
$(find "$SESSION_BACKUP_DIR" -type f -not -name "MANIFEST.txt" | sort)
EOF
    
    # Cleanup old backups
    cleanup_old_backups
else
    echo "⚠️  No files found to backup"
    rmdir "$SESSION_BACKUP_DIR" 2>/dev/null
fi

# Function to cleanup old backups
cleanup_old_backups() {
    local backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "session_*" | wc -l)
    
    if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
        echo "Cleaning up old backups (keeping last $MAX_BACKUPS)..."
        
        # Remove oldest backups
        find "$BACKUP_DIR" -maxdepth 1 -type d -name "session_*" -printf '%T@ %p\n' | \
        sort -n | \
        head -n -"$MAX_BACKUPS" | \
        cut -d' ' -f2- | \
        while read -r old_backup; do
            echo "  Removing old backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
        done
    fi
}

# Log backup activity
LOG_FILE="${HOME}/.codex/backup.log"
echo "[$(date -Iseconds)] SESSION_BACKUP: Session $CODEX_SESSION_ID - $total_files files backed up" >> "$LOG_FILE"
