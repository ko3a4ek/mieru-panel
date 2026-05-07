#!/bin/bash

# Mieru Panel - Restore Script
# Restores configuration and database from backup

BACKUP_DIR="/opt/mieru-panel/backups"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

echo "=== Mieru Panel - Restore ==="
echo ""

# List available backups
if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
    echo "Error: No backups found in $BACKUP_DIR"
    exit 1
fi

echo "Available backups:"
ls -lh "$BACKUP_DIR"/*.tar.gz | awk '{print $9, "(" $5 ")"}'
echo ""

# Get backup to restore
read -p "Enter backup filename (or full path): " backup_file

if [ -z "$backup_file" ]; then
    echo "Error: No backup specified"
    exit 1
fi

# Use full path if not provided
if [[ ! "$backup_file" == /* ]]; then
    backup_file="$BACKUP_DIR/$backup_file"
fi

# Check if backup exists
if [ ! -f "$backup_file" ]; then
    echo "Error: Backup file not found: $backup_file"
    exit 1
fi

# Confirm restore
echo ""
echo "WARNING: This will overwrite current configuration and database!"
read -p "Are you sure you want to restore from $backup_file? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Stop services
echo "Stopping services..."
systemctl stop mieru-panel
systemctl stop mita

# Restore backup
echo "Restoring from backup..."
tar -xzf "$backup_file" -C /

if [ $? -eq 0 ]; then
    echo "Restore completed successfully"

    # Start services
    echo "Starting services..."
    systemctl start mita
    systemctl start mieru-panel

    echo ""
    echo "Restore completed! Services have been restarted."
else
    echo "Error: Failed to restore backup"

    # Try to start services anyway
    systemctl start mita
    systemctl start mieru-panel

    exit 1
fi
