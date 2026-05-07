# Mieru Panel - Quick Start Guide

## Installation

### Quick Install (Recommended)

```bash
# Download and run installer
chmod +x install.sh
sudo ./install.sh
```

### Manual Install

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git sqlite3 nginx

# 2. Install mita
wget https://github.com/enfein/mieru/releases/latest/download/mita_latest_amd64.deb
sudo dpkg -i mita_latest_amd64.deb

# 3. Setup panel
cd /opt
sudo git clone <your-repo> mieru-panel
cd mieru-panel
sudo python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Create data directory
sudo mkdir -p data

# 5. Setup systemd services
sudo cp mieru-panel.service /etc/systemd/system/
sudo cp mita.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mita mieru-panel
sudo systemctl start mita mieru-panel

# 6. Setup nginx (optional)
sudo cp nginx.conf /etc/nginx/sites-available/mieru-panel
sudo ln -s /etc/nginx/sites-available/mieru-panel /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

## First Steps

1. **Access the panel**
   - Without nginx: `http://your-server-ip:5000`
   - With nginx: `http://your-server-ip`

2. **Login with default credentials**
   - Username: `admin`
   - Password: `admin123`

3. **Change admin password**
   ```bash
   sudo ./change_admin_password.sh
   ```

4. **Add your first user**
   - Go to Users page
   - Click "Add User"
   - Enter username and password
   - Set quotas if needed

## Common Tasks

### View Server Status
- Dashboard shows real-time status
- CPU, RAM, and traffic metrics
- Active connections

### Manage Users
- Add/Edit/Delete users
- Set daily/monthly traffic limits
- View user statistics

### Configure Server
- Change port bindings
- Adjust logging level
- Modify MTU settings

### View Logs
- Active connections
- Activity history
- System events

## Backup & Restore

### Create Backup
```bash
sudo ./backup.sh
```

### Restore from Backup
```bash
sudo ./restore.sh
```

Backups are stored in `/opt/mieru-panel/backups/`

## Service Management

```bash
# Check status
sudo systemctl status mieru-panel
sudo systemctl status mita

# Restart services
sudo systemctl restart mieru-panel
sudo systemctl restart mita

# View logs
sudo journalctl -u mieru-panel -f
sudo journalctl -u mita -f
```

## Security Recommendations

1. **Change default password** immediately
2. **Use HTTPS** in production (configure SSL with nginx)
3. **Restrict access** to trusted networks
4. **Keep software updated**
5. **Use strong passwords** for proxy users
6. **Regular backups** of configuration

## Troubleshooting

### Panel not accessible
```bash
# Check if service is running
sudo systemctl status mieru-panel

# Check logs
sudo journalctl -u mieru-panel -n 50

# Check firewall
sudo ufw status
```

### Mita commands failing
```bash
# Check mita installation
which mita
mita --version

# Check mita service
sudo systemctl status mita

# Test mita manually
sudo mita status
```

### Database errors
```bash
# Check data directory
ls -la /opt/mieru-panel/data/

# Recreate database
cd /opt/mieru-panel
source venv/bin/activate
python3 -c "from helpers.db import init_db; init_db()"
```

## API Usage

The panel provides REST API endpoints for automation:

```bash
# Get server status
curl http://localhost:5000/api/status

# Get metrics
curl http://localhost:5000/api/metrics

# List users
curl http://localhost:5000/api/users

# Add user (requires authentication)
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'
```

## Support

- **Mieru Documentation**: https://github.com/enfein/mieru
- **Issue Tracker**: Report bugs in your repository
- **Logs**: Check `journalctl -u mieru-panel` for errors
