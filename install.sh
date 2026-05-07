#!/bin/bash

# Mieru Panel Installation Script
# For Debian 11/12 or Ubuntu 20.04/22.04 LTS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Mieru Panel Installation Script ===${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS $VERSION${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
apt update && apt upgrade -y

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
apt install -y python3 python3-pip python3-venv git sqlite3 nginx curl wget

# Install mita
echo -e "${YELLOW}Installing mita...${NC}"
MITA_VERSION=$(curl -s https://api.github.com/repos/enfein/mieru/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
MITA_URL="https://github.com/enfein/mieru/releases/download/${MITA_VERSION}/mita_${MITA_VERSION#v}_amd64.deb"

echo -e "${YELLOW}Downloading mita from: $MITA_URL${NC}"
wget -O /tmp/mita.deb "$MITA_URL"
dpkg -i /tmp/mita.deb || apt install -f -y
rm /tmp/mita.deb

# Create panel directory
PANEL_DIR="/opt/mieru-panel"
echo -e "${YELLOW}Creating panel directory at $PANEL_DIR${NC}"
mkdir -p "$PANEL_DIR"

# Copy panel files (assuming script is run from panel directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$PANEL_DIR" ]; then
    echo -e "${YELLOW}Copying panel files to $PANEL_DIR${NC}"
    cp -r "$SCRIPT_DIR"/* "$PANEL_DIR/"
fi

# Create Python virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
cd "$PANEL_DIR"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create mita config directory
mkdir -p /etc/mita
mkdir -p /var/lib/mita

# Create default server config if not exists
if [ ! -f /etc/mita/server.conf.json ]; then
    echo -e "${YELLOW}Creating default server configuration...${NC}"
    cat > /etc/mita/server.conf.json << 'EOF'
{
  "portBindings": [
    {
      "port": 8443,
      "protocol": "TCP"
    }
  ],
  "loggingLevel": "INFO",
  "mtu": 1420,
  "users": []
}
EOF
fi

# Create database directory
mkdir -p "$PANEL_DIR/data"

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python3 -c "
from helpers.db import init_db
init_db()
print('Database initialized successfully')
"

# Set permissions
chown -R root:root "$PANEL_DIR"
chmod 755 "$PANEL_DIR"

# Create systemd service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/mieru-panel.service << 'EOF'
[Unit]
Description=Mieru Web Panel
After=network.target mita.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mieru-panel
Environment="PATH=/opt/mieru-panel/venv/bin"
ExecStart=/opt/mieru-panel/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create mita service if not exists
if [ ! -f /etc/systemd/system/mita.service ]; then
    echo -e "${YELLOW}Creating mita systemd service...${NC}"
    cat > /etc/systemd/system/mita.service << 'EOF'
[Unit]
Description=Mieru Proxy Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/mita start
ExecStop=/usr/bin/mita stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

# Configure nginx (optional)
read -p "Do you want to configure nginx as reverse proxy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Configuring nginx...${NC}"
    cat > /etc/nginx/sites-available/mieru-panel << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/mieru-panel /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl restart nginx
fi

# Start services
echo -e "${YELLOW}Starting services...${NC}"
systemctl daemon-reload
systemctl enable mita.service
systemctl start mita.service
systemctl enable mieru-panel.service
systemctl start mieru-panel.service

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Success message
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo -e "${GREEN}Mieru Panel is now running!${NC}"
echo ""
echo "Panel URL: http://$SERVER_IP:5000"
echo "Default admin credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo -e "${YELLOW}IMPORTANT: Change the default password after first login!${NC}"
echo ""
echo "Useful commands:"
echo "  systemctl status mieru-panel  - Check panel status"
echo "  systemctl restart mieru-panel - Restart panel"
echo "  journalctl -u mieru-panel -f  - View panel logs"
echo "  systemctl status mita         - Check mita status"
echo ""
echo -e "${GREEN}Installation finished successfully!${NC}"
