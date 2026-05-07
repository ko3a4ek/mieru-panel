#!/bin/bash

# Mieru Panel - Admin Password Change Script
# Allows changing the admin password without accessing the web interface

PANEL_DIR="/opt/mieru-panel"
VENV="$PANEL_DIR/venv"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Check if panel directory exists
if [ ! -d "$PANEL_DIR" ]; then
    echo "Error: Panel directory not found at $PANEL_DIR"
    exit 1
fi

echo "=== Mieru Panel - Admin Password Change ==="
echo ""

# Get username
read -p "Enter admin username (default: admin): " username
username=${username:-admin}

# Get new password
read -s -p "Enter new password: " password
echo ""
read -s -p "Confirm new password: " password_confirm
echo ""

if [ "$password" != "$password_confirm" ]; then
    echo "Error: Passwords do not match"
    exit 1
fi

if [ -z "$password" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

# Update password
echo "Updating password..."
cd "$PANEL_DIR"
source "$VENV/bin/activate"

python3 << EOF
import sys
sys.path.insert(0, '$PANEL_DIR')
from helpers.db import update_admin_password

if update_admin_password('$username', '$password'):
    print("Password updated successfully!")
else:
    print("Error: Failed to update password")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "Password for user '$username' has been changed successfully."
    echo "You can now login with the new password."
else
    echo ""
    echo "Failed to update password. Please check the logs."
    exit 1
fi
