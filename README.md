# Mieru Panel

Web-based management panel for Mieru (mita) proxy server.

## Features

- **Dashboard**: Server status, system metrics, and traffic statistics
- **User Management**: Add, edit, and delete users with quota support
- **Configuration**: Manage port bindings, logging level, and MTU settings
- **Logs**: View active connections and activity history
- **Traffic Analytics**: Real-time traffic monitoring with charts

## Requirements

- Debian 11/12 or Ubuntu 20.04/22.04 LTS
- Root access
- Python 3.9+

## Installation

1. Clone or download this repository
2. Run the installation script:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will:
- Update system packages
- Install mita proxy server
- Install Python dependencies
- Configure systemd services
- Set up nginx (optional)

## Default Credentials

- **Username**: admin
- **Password**: admin123

**Important**: Change the default password after first login!

## Usage

After installation, access the panel at:
- `http://your-server-ip:5000` (without nginx)
- `http://your-server-ip` (with nginx)

## Manual Setup

If you prefer manual setup:

1. Install dependencies:
```bash
apt update
apt install -y python3 python3-pip python3-venv git sqlite3
```

2. Install mita:
```bash
wget https://github.com/enfein/mieru/releases/latest/download/mita_latest_amd64.deb
dpkg -i mita_latest_amd64.deb
```

3. Setup Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Create data directory:
```bash
mkdir -p data
```

5. Run the application:
```bash
python app.py
```

## Project Structure

```
mieru-panel/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── install.sh          # Installation script
├── helpers/
│   ├── __init__.py
│   ├── mita_cli.py     # Mita CLI wrapper functions
│   └── db.py           # Database helpers
├── templates/
│   ├── login.html      # Login page
│   ├── dashboard.html  # Main dashboard
│   ├── users.html      # User management
│   ├── config.html     # Server configuration
│   ├── logs.html       # Connection and activity logs
│   └── error.html      # Error page
└── data/               # SQLite database (created at runtime)
```

## API Endpoints

### Status & Metrics
- `GET /api/status` - Server status
- `GET /api/metrics` - Current traffic metrics
- `GET /api/traffic-history?hours=N` - Traffic history
- `GET /api/connections` - Active connections
- `GET /api/system` - System information

### Users
- `GET /api/users` - List all users
- `POST /api/users` - Add new user
- `PUT /api/users/<username>` - Update user
- `DELETE /api/users/<username>` - Delete user

### Configuration
- `GET /api/config` - Get server configuration
- `PUT /api/config` - Update server configuration
- `POST /api/reload` - Reload service
- `POST /api/restart` - Restart service

## Service Management

```bash
# Check panel status
systemctl status mieru-panel

# Restart panel
systemctl restart mieru-panel

# View panel logs
journalctl -u mieru-panel -f

# Check mita status
systemctl status mita

# Restart mita
systemctl restart mita
```

## Security Notes

1. Change default admin password immediately
2. Use HTTPS in production (configure nginx with SSL)
3. Restrict panel access to trusted networks
4. Keep mita and system packages updated
5. Use strong passwords for proxy users

## Troubleshooting

### Panel not accessible
- Check if service is running: `systemctl status mieru-panel`
- Check firewall rules
- Review logs: `journalctl -u mieru-panel`

### Mita commands failing
- Ensure mita is installed: `which mita`
- Check mita service status: `systemctl status mita`
- Verify config file: `/etc/mita/server.conf.json`

### Database errors
- Ensure data directory exists: `mkdir -p data`
- Check file permissions

## License

This project is provided as-is for managing Mieru proxy servers.

## Support

For issues with Mieru itself, visit: https://github.com/enfein/mieru
