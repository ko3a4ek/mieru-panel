"""
Database Helper Functions
Handles SQLite database operations for the panel
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = 'data/mieru_panel.db'


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Traffic history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                download_bytes INTEGER DEFAULT 0,
                upload_bytes INTEGER DEFAULT 0
            )
        ''')

        # User activity log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                details TEXT,
                admin_user TEXT
            )
        ''')

        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_traffic_timestamp
            ON traffic_history(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp
            ON activity_log(timestamp)
        ''')

        # Create default admin user if not exists
        cursor.execute('SELECT COUNT(*) FROM admin_users')
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash) VALUES (?, ?)',
                ('admin', generate_password_hash('admin123'))
            )
            logger.info("Default admin user created (admin/admin123)")


def get_admin_user(username: str) -> Optional[Dict]:
    """Get admin user by username"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM admin_users WHERE username = ?',
            (username,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def create_admin_user(username: str, password: str) -> bool:
    """Create a new admin user"""
    try:
        from werkzeug.security import generate_password_hash

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO admin_users (username, password_hash) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
        return True
    except sqlite3.IntegrityError:
        logger.error(f"Admin user '{username}' already exists")
        return False
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return False


def update_admin_password(username: str, new_password: str) -> bool:
    """Update admin user password"""
    try:
        from werkzeug.security import generate_password_hash

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE admin_users SET password_hash = ? WHERE username = ?',
                (generate_password_hash(new_password), username)
            )
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to update admin password: {e}")
        return False


def record_traffic(download_bytes: int, upload_bytes: int) -> bool:
    """Record traffic metrics to database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO traffic_history (download_bytes, upload_bytes) VALUES (?, ?)',
                (download_bytes, upload_bytes)
            )
        return True
    except Exception as e:
        logger.error(f"Failed to record traffic: {e}")
        return False


def get_traffic_history(hours: int = 24) -> List[Dict]:
    """Get traffic history for the last N hours"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT timestamp, download_bytes, upload_bytes
                   FROM traffic_history
                   WHERE timestamp >= ?
                   ORDER BY timestamp ASC''',
                (cutoff_time.isoformat(),)
            )

            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get traffic history: {e}")
        return []


def get_traffic_summary(period: str = 'day') -> Dict:
    """Get traffic summary for a period (day, week, month)"""
    try:
        if period == 'day':
            cutoff = datetime.now() - timedelta(days=1)
        elif period == 'week':
            cutoff = datetime.now() - timedelta(weeks=1)
        elif period == 'month':
            cutoff = datetime.now() - timedelta(days=30)
        else:
            cutoff = datetime.now() - timedelta(days=1)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT
                   SUM(download_bytes) as total_download,
                   SUM(upload_bytes) as total_upload,
                   COUNT(*) as record_count
                   FROM traffic_history
                   WHERE timestamp >= ?''',
                (cutoff.isoformat(),)
            )

            row = cursor.fetchone()
            if row:
                return {
                    'download_bytes': row['total_download'] or 0,
                    'upload_bytes': row['total_upload'] or 0,
                    'total_bytes': (row['total_download'] or 0) + (row['total_upload'] or 0),
                    'record_count': row['record_count'] or 0
                }

        return {
            'download_bytes': 0,
            'upload_bytes': 0,
            'total_bytes': 0,
            'record_count': 0
        }

    except Exception as e:
        logger.error(f"Failed to get traffic summary: {e}")
        return {
            'download_bytes': 0,
            'upload_bytes': 0,
            'total_bytes': 0,
            'record_count': 0
        }


def log_activity(action: str, details: str = None, admin_user: str = None) -> bool:
    """Log an admin action"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO activity_log (action, details, admin_user) VALUES (?, ?, ?)',
                (action, details, admin_user)
            )
        return True
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        return False


def get_activity_log(limit: int = 50) -> List[Dict]:
    """Get recent activity log entries"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM activity_log
                   ORDER BY timestamp DESC
                   LIMIT ?''',
                (limit,)
            )

            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get activity log: {e}")
        return []


def cleanup_old_traffic_history(days: int = 90) -> int:
    """Remove traffic history older than N days"""
    try:
        cutoff = datetime.now() - timedelta(days=days)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM traffic_history WHERE timestamp < ?',
                (cutoff.isoformat(),)
            )

            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old traffic records")
            return deleted

    except Exception as e:
        logger.error(f"Failed to cleanup old traffic history: {e}")
        return 0
