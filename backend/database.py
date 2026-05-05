import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from logger import get_logger

load_dotenv()
logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rootpg:123456@host.docker.internal:5432/netipdb")

class DBConnWrapper:
    def __init__(self, conn):
        self.conn = conn
    def cursor(self):
        # Always return RealDictCursor to match previous sqlite3.Row dict-like behaviour
        return self.conn.cursor(cursor_factory=RealDictCursor)
    def commit(self):
        self.conn.commit()
    def close(self):
        self.conn.close()
    def execute(self, *args, **kwargs):
        with self.cursor() as cur:
            cur.execute(*args, **kwargs)

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def ensure_database_exists():
    from urllib.parse import urlparse
    result = urlparse(DATABASE_URL)
    db_name = result.path.lstrip('/')
    if not db_name or db_name == 'postgres':
        return
        
    temp_url = DATABASE_URL.replace(f"/{db_name}", "/postgres")
    try:
        conn = psycopg2.connect(temp_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {db_name}")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Auto-create DB check failed: {e}", exc_info=True)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return DBConnWrapper(conn)

def init_db():
    ensure_database_exists()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create devices table
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id SERIAL PRIMARY KEY,
                hostname VARCHAR(255),
                ip_address VARCHAR(50) UNIQUE NOT NULL,
                mac_address VARCHAR(50) UNIQUE,
                status VARCHAR(20) DEFAULT 'offline',
                is_reserved BOOLEAN DEFAULT FALSE,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        ''')
        # Add new columns gracefully
        cursor.execute('ALTER TABLE devices ADD COLUMN IF NOT EXISTS model VARCHAR(255)')
        cursor.execute('ALTER TABLE devices ADD COLUMN IF NOT EXISTS process VARCHAR(255)')
    except Exception as e:
        logger.warning(f"Database schema patch warning: {e}", exc_info=True)
    
    # Create history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_history (
        log_id SERIAL PRIMARY KEY,
        device_id INTEGER NOT NULL,
        change_type VARCHAR(50) NOT NULL,
        field_changed VARCHAR(50),
        old_value TEXT,
        new_value TEXT,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES devices(device_id)
    )
    ''')
    
    # Create indexes for fast lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mac ON devices (mac_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip ON devices (ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changed ON device_history (changed_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON device_history (device_id)')
    
    conn.commit()
    conn.close()

# Initialize DB on load unless in test mode
if not os.environ.get("TESTING"):
    init_db()
