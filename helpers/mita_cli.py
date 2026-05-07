"""
Mita CLI Helper Functions
Handles all interactions with the mita command-line interface
"""

import subprocess
import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MitaCLIError(Exception):
    """Custom exception for Mita CLI errors"""
    pass


def run_mita_command(args: List[str], capture_output: bool = True) -> Tuple[str, str, int]:
    """
    Run a mita command with proper error handling

    Args:
        args: List of command arguments (e.g., ['status', 'get', 'metrics'])
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (stdout, stderr, return_code)

    Raises:
        MitaCLIError: If command fails
    """
    try:
        cmd = ['mita'] + args
        logger.debug(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )

        if result.returncode != 0 and capture_output:
            logger.error(f"Mita command failed: {result.stderr}")
            raise MitaCLIError(f"Command failed: {result.stderr}")

        return result.stdout, result.stderr, result.returncode

    except FileNotFoundError:
        raise MitaCLIError("mita command not found. Please ensure mita is installed.")
    except Exception as e:
        raise MitaCLIError(f"Error running mita command: {str(e)}")


def get_status() -> Dict:
    """
    Get mita server status

    Returns:
        Dict with status information
    """
    try:
        stdout, _, _ = run_mita_command(['status'])

        # Parse status output
        status = {
            'running': False,
            'message': stdout.strip()
        }

        if 'RUNNING' in stdout or 'running' in stdout:
            status['running'] = True

        return status

    except MitaCLIError as e:
        logger.error(f"Failed to get status: {e}")
        return {'running': False, 'message': str(e)}


def get_metrics() -> Dict:
    """
    Get traffic metrics from mita

    Returns:
        Dict with metrics data (download, upload, etc.)
    """
    try:
        stdout, _, _ = run_mita_command(['get', 'metrics'])

        # Parse JSON output
        metrics = json.loads(stdout)

        return {
            'download_bytes': metrics.get('download', 0),
            'upload_bytes': metrics.get('upload', 0),
            'total_bytes': metrics.get('download', 0) + metrics.get('upload', 0),
            'raw': metrics
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metrics JSON: {e}")
        return {
            'download_bytes': 0,
            'upload_bytes': 0,
            'total_bytes': 0,
            'raw': {}
        }
    except MitaCLIError as e:
        logger.error(f"Failed to get metrics: {e}")
        return {
            'download_bytes': 0,
            'upload_bytes': 0,
            'total_bytes': 0,
            'raw': {}
        }


def get_connections() -> List[Dict]:
    """
    Get active connections from mita

    Returns:
        List of connection dictionaries
    """
    try:
        stdout, _, _ = run_mita_command(['get', 'connections'])

        connections = []
        for line in stdout.strip().split('\n'):
            if line.strip():
                # Parse connection line
                # Format may vary, try to extract key info
                parts = line.split()
                if len(parts) >= 4:
                    connections.append({
                        'session_id': parts[0] if len(parts) > 0 else '',
                        'protocol': parts[1] if len(parts) > 1 else '',
                        'local_addr': parts[2] if len(parts) > 2 else '',
                        'remote_addr': parts[3] if len(parts) > 3 else '',
                        'raw': line
                    })

        return connections

    except MitaCLIError as e:
        logger.error(f"Failed to get connections: {e}")
        return []


def get_config() -> Dict:
    """
    Read current server configuration

    Returns:
        Dict with server configuration
    """
    try:
        with open('/etc/mita/server.conf.json', 'r') as f:
            config = json.load(f)
        return config

    except FileNotFoundError:
        logger.error("Config file not found: /etc/mita/server.conf.json")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config JSON: {e}")
        return {}


def save_config(config: Dict) -> bool:
    """
    Save server configuration and apply it

    Args:
        config: Configuration dictionary to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Write config file
        with open('/etc/mita/server.conf.json', 'w') as f:
            json.dump(config, f, indent=2)

        # Apply configuration
        stdout, stderr, code = run_mita_command(['apply', 'config', '/etc/mita/server.conf.json'])

        return True

    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def reload_service() -> bool:
    """
    Reload mita service (applies config changes without disconnecting users)

    Returns:
        True if successful, False otherwise
    """
    try:
        stdout, stderr, code = run_mita_command(['reload'])
        logger.info("Mita service reloaded successfully")
        return True

    except MitaCLIError as e:
        logger.error(f"Failed to reload service: {e}")
        return False


def restart_service() -> bool:
    """
    Restart mita service (required for port changes)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Stop
        run_mita_command(['stop'], capture_output=False)
        # Start
        run_mita_command(['start'], capture_output=False)

        logger.info("Mita service restarted successfully")
        return True

    except MitaCLIError as e:
        logger.error(f"Failed to restart service: {e}")
        return False


def get_users() -> List[Dict]:
    """
    Get list of users from config

    Returns:
        List of user dictionaries
    """
    config = get_config()
    return config.get('users', [])


def add_user(username: str, password: str, daily_limit: int = 0, monthly_limit: int = 0) -> bool:
    """
    Add a new user to the configuration

    Args:
        username: Username for the new user
        password: Password for the new user
        daily_limit: Daily traffic limit in MB (0 = unlimited)
        monthly_limit: Monthly traffic limit in MB (0 = unlimited)

    Returns:
        True if successful, False otherwise
    """
    try:
        config = get_config()

        # Check if user already exists
        for user in config.get('users', []):
            if user.get('username') == username:
                raise MitaCLIError(f"User '{username}' already exists")

        # Add new user
        new_user = {
            'username': username,
            'password': password
        }

        if daily_limit > 0:
            new_user['dailyLimitMB'] = daily_limit
        if monthly_limit > 0:
            new_user['monthlyLimitMB'] = monthly_limit

        if 'users' not in config:
            config['users'] = []

        config['users'].append(new_user)

        return save_config(config)

    except Exception as e:
        logger.error(f"Failed to add user: {e}")
        return False


def update_user(username: str, password: Optional[str] = None,
                daily_limit: Optional[int] = None, monthly_limit: Optional[int] = None) -> bool:
    """
    Update an existing user

    Args:
        username: Username to update
        password: New password (None to keep existing)
        daily_limit: New daily limit in MB (None to keep existing)
        monthly_limit: New monthly limit in MB (None to keep existing)

    Returns:
        True if successful, False otherwise
    """
    try:
        config = get_config()

        # Find and update user
        user_found = False
        for user in config.get('users', []):
            if user.get('username') == username:
                user_found = True
                if password is not None:
                    user['password'] = password
                if daily_limit is not None:
                    if daily_limit > 0:
                        user['dailyLimitMB'] = daily_limit
                    elif 'dailyLimitMB' in user:
                        del user['dailyLimitMB']
                if monthly_limit is not None:
                    if monthly_limit > 0:
                        user['monthlyLimitMB'] = monthly_limit
                    elif 'monthlyLimitMB' in user:
                        del user['monthlyLimitMB']
                break

        if not user_found:
            raise MitaCLIError(f"User '{username}' not found")

        return save_config(config)

    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        return False


def delete_user(username: str) -> bool:
    """
    Delete a user from the configuration

    Args:
        username: Username to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        config = get_config()

        # Remove user
        users = config.get('users', [])
        original_count = len(users)
        config['users'] = [u for u in users if u.get('username') != username]

        if len(config['users']) == original_count:
            raise MitaCLIError(f"User '{username}' not found")

        return save_config(config)

    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        return False


def update_server_config(port_bindings: Optional[List[Dict]] = None,
                        logging_level: Optional[str] = None,
                        mtu: Optional[int] = None) -> bool:
    """
    Update server configuration parameters

    Args:
        port_bindings: List of port binding dicts
        logging_level: Logging level (INFO, DEBUG, ERROR)
        mtu: MTU value (1280-1500)

    Returns:
        True if successful, False otherwise
    """
    try:
        config = get_config()

        # Check if ports changed (requires restart)
        ports_changed = False
        if port_bindings is not None:
            current_ports = config.get('portBindings', [])
            if current_ports != port_bindings:
                config['portBindings'] = port_bindings
                ports_changed = True

        if logging_level is not None:
            config['loggingLevel'] = logging_level

        if mtu is not None:
            if not 1280 <= mtu <= 1500:
                raise MitaCLIError("MTU must be between 1280 and 1500")
            config['mtu'] = mtu

        # Save config
        if not save_config(config):
            return False

        # Restart if ports changed
        if ports_changed:
            return restart_service()
        else:
            return reload_service()

    except Exception as e:
        logger.error(f"Failed to update server config: {e}")
        return False
