"""
Mieru Panel - Main Flask Application
Web interface for managing Mieru (mita) proxy server
"""

import os
import logging
import psutil
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

from helpers.mita_cli import (
    get_status, get_metrics, get_connections, get_config,
    add_user, update_user, delete_user, update_server_config, reload_service, restart_service,
    MitaCLIError
)
from helpers.db import (
    init_db, get_admin_user, record_traffic, get_traffic_history,
    get_traffic_summary, log_activity, get_activity_log, cleanup_old_traffic_history
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


class AdminUser:
    """Admin user class for Flask-Login"""

    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    user_dict = get_admin_user_by_id(int(user_id))
    if user_dict:
        return AdminUser(user_dict)
    return None


def get_admin_user_by_id(user_id: int):
    """Get admin user by ID"""
    import sqlite3
    try:
        conn = sqlite3.connect('data/mieru_panel.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Failed to get admin user by ID: {e}")
        return None


# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")


# Background scheduler for metrics collection
scheduler = BackgroundScheduler()


def collect_metrics():
    """Background task to collect and store metrics"""
    try:
        metrics = get_metrics()
        record_traffic(metrics['download_bytes'], metrics['upload_bytes'])
        logger.debug(f"Collected metrics: {metrics['total_bytes']} bytes")
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")


def cleanup_old_data():
    """Background task to cleanup old data"""
    try:
        deleted = cleanup_old_traffic_history(days=90)
        logger.info(f"Cleaned up {deleted} old traffic records")
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")


# Start scheduler
try:
    scheduler.add_job(collect_metrics, 'interval', minutes=1, id='collect_metrics')
    scheduler.add_job(cleanup_old_data, 'interval', hours=24, id='cleanup_old_data')
    scheduler.start()
    logger.info("Background scheduler started")
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")


# Helper functions
def get_system_info():
    """Get system information (CPU, RAM, uptime)"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        uptime = timedelta(seconds=int(psutil.boot_time()))

        return {
            'cpu_percent': cpu_percent,
            'ram_total': ram.total,
            'ram_used': ram.used,
            'ram_percent': ram.percent,
            'ram_available': ram.available,
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime)
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {
            'cpu_percent': 0,
            'ram_total': 0,
            'ram_used': 0,
            'ram_percent': 0,
            'ram_available': 0,
            'uptime_seconds': 0,
            'uptime_formatted': 'Unknown'
        }


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


# Routes
@app.route('/')
@login_required
def index():
    """Redirect to dashboard"""
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user_dict = get_admin_user(username)
        if user_dict and check_password_hash(user_dict['password_hash'], password):
            user = AdminUser(user_dict)
            login_user(user)
            log_activity('login', f'User {username} logged in', username)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout"""
    log_activity('logout', f'User {current_user.username} logged out', current_user.username)
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    try:
        # Get server status
        status = get_status()

        # Get current metrics
        metrics = get_metrics()

        # Get system info
        system_info = get_system_info()

        # Get traffic summaries
        traffic_day = get_traffic_summary('day')
        traffic_week = get_traffic_summary('week')
        traffic_month = get_traffic_summary('month')

        # Get recent activity
        recent_activity = get_activity_log(limit=10)

        return render_template('dashboard.html',
                             status=status,
                             metrics=metrics,
                             system_info=system_info,
                             traffic_day=traffic_day,
                             traffic_week=traffic_week,
                             traffic_month=traffic_month,
                             recent_activity=recent_activity,
                             format_bytes=format_bytes)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
                             status={'running': False, 'message': str(e)},
                             metrics={'download_bytes': 0, 'upload_bytes': 0, 'total_bytes': 0},
                             system_info=get_system_info(),
                             traffic_day={'total_bytes': 0},
                             traffic_week={'total_bytes': 0},
                             traffic_month={'total_bytes': 0},
                             recent_activity=[],
                             format_bytes=format_bytes)


@app.route('/users')
@login_required
def users():
    """Users management page"""
    try:
        users_list = get_users()
        return render_template('users.html', users=users_list, format_bytes=format_bytes)
    except Exception as e:
        logger.error(f"Users page error: {e}")
        flash(f'Error loading users: {str(e)}', 'error')
        return render_template('users.html', users=[], format_bytes=format_bytes)


@app.route('/config')
@login_required
def config():
    """Server configuration page"""
    try:
        config_data = get_config()
        return render_template('config.html', config=config_data)
    except Exception as e:
        logger.error(f"Config page error: {e}")
        flash(f'Error loading config: {str(e)}', 'error')
        return render_template('config.html', config={})


@app.route('/logs')
@login_required
def logs():
    """Connections logs page"""
    try:
        connections = get_connections()
        activity_log = get_activity_log(limit=100)
        return render_template('logs.html',
                             connections=connections,
                             activity_log=activity_log)
    except Exception as e:
        logger.error(f"Logs page error: {e}")
        flash(f'Error loading logs: {str(e)}', 'error')
        return render_template('logs.html', connections=[], activity_log=[])


# API Routes
@app.route('/api/status')
@login_required
def api_status():
    """Get server status"""
    status = get_status()
    return jsonify(status)


@app.route('/api/metrics')
@login_required
def api_metrics():
    """Get current metrics"""
    metrics = get_metrics()
    return jsonify(metrics)


@app.route('/api/traffic-history')
@login_required
def api_traffic_history():
    """Get traffic history for charts"""
    hours = request.args.get('hours', 24, type=int)
    history = get_traffic_history(hours)
    return jsonify(history)


@app.route('/api/connections')
@login_required
def api_connections():
    """Get active connections"""
    connections = get_connections()
    return jsonify(connections)


@app.route('/api/users', methods=['GET'])
@login_required
def api_users_get():
    """Get all users"""
    users_list = get_users()
    return jsonify(users_list)


@app.route('/api/users', methods=['POST'])
@login_required
def api_users_add():
    """Add a new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        daily_limit = data.get('daily_limit', 0)
        monthly_limit = data.get('monthly_limit', 0)

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400

        if add_user(username, password, daily_limit, monthly_limit):
            log_activity('user_add', f'Added user: {username}', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add user'}), 500

    except MitaCLIError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"API add user error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<username>', methods=['PUT'])
@login_required
def api_users_update(username):
    """Update a user"""
    try:
        data = request.get_json()
        password = data.get('password')
        daily_limit = data.get('daily_limit')
        monthly_limit = data.get('monthly_limit')

        if update_user(username, password, daily_limit, monthly_limit):
            log_activity('user_update', f'Updated user: {username}', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update user'}), 500

    except MitaCLIError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"API update user error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def api_users_delete(username):
    """Delete a user"""
    try:
        if delete_user(username):
            log_activity('user_delete', f'Deleted user: {username}', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete user'}), 500

    except MitaCLIError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"API delete user error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
@login_required
def api_config_get():
    """Get server configuration"""
    config_data = get_config()
    return jsonify(config_data)


@app.route('/api/config', methods=['PUT'])
@login_required
def api_config_update():
    """Update server configuration"""
    try:
        data = request.get_json()
        port_bindings = data.get('port_bindings')
        logging_level = data.get('logging_level')
        mtu = data.get('mtu')

        if update_server_config(port_bindings, logging_level, mtu):
            log_activity('config_update', 'Updated server configuration', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update configuration'}), 500

    except MitaCLIError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"API update config error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reload', methods=['POST'])
@login_required
def api_reload():
    """Reload mita service"""
    try:
        if reload_service():
            log_activity('service_reload', 'Reloaded mita service', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to reload service'}), 500

    except Exception as e:
        logger.error(f"API reload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/restart', methods=['POST'])
@login_required
def api_restart():
    """Restart mita service"""
    try:
        if restart_service():
            log_activity('service_restart', 'Restarted mita service', current_user.username)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to restart service'}), 500

    except Exception as e:
        logger.error(f"API restart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system')
@login_required
def api_system():
    """Get system information"""
    system_info = get_system_info()
    return jsonify(system_info)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message='Internal server error'), 500


if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
