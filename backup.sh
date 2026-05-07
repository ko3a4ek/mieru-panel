#!/bin/bash

# Mieru Panel - Backup Script
# Creates backups of configuration and database

BACKUP_DIR="/opt/mieru-panel/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mieru_panel_backup_${TIMESTAMP}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "=== Mieru Panel - Backup ==="
echo "Creating backup: $BACKUP_NAME"
echo ""

# Create backup archive
tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" \
    /etc/mita/server.conf.json \
    /opt/mieru-panel/data/ \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "Backup created successfully: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"

    # Calculate backup size
    SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)
    echo "Backup size: $SIZE"

    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t mieru_panel_backup_*.tar.gz | tail -n +11 | xargs -r rm --
    echo "Old backups cleaned up (keeping last 10)"
else
    echo "Error: Failed to create backup"
    exit 1
fi
