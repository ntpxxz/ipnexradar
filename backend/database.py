import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "ipnex.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create devices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        device_id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT,
        ip_address TEXT NOT NULL,
        mac_address TEXT NOT NULL UNIQUE,
        status TEXT DEFAULT 'online',
        is_reserved BOOLEAN DEFAULT 0,
        first_seen DATETIME NOT NULL,
        last_seen DATETIME NOT NULL
    )
    ''')
    
    # Create history table (Append-only Audit Trail)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_history (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        change_type TEXT NOT NULL,
        field_changed TEXT,
        old_value TEXT,
        new_value TEXT,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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

# Initialize DB on load
init_db()
