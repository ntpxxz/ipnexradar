import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "database.json")

def _load_db():
    # If no file exists, create a default database with a mock device
    if not os.path.exists(DB_FILE):
        return {
            "devices": [
                {
                    "id": 1,
                    "mac_address": "00:11:22:33:44:55",
                    "last_known_ip": "192.168.1.100",
                    "last_known_hostname": "Admin-PC",
                    "category": "PC",
                    "is_authorized": "TRUE",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            ],
            "scan_logs": []
        }
    with open(DB_FILE, "r") as f:
        return json.load(f)

def _save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

class MockSheet:
    def __init__(self, table_name):
        self.table_name = table_name

    def get_all_records(self):
        db = _load_db()
        return db.get(self.table_name, [])

    def append_rows(self, rows):
        db = _load_db()
        table = db.get(self.table_name, [])
        
        # Map array to dictionary based on our schema
        if self.table_name == "devices":
            headers = ["id", "mac_address", "last_known_ip", "last_known_hostname", "category", "is_authorized", "created_at", "updated_at"]
        elif self.table_name == "scan_logs":
            headers = ["id", "device_id", "ip_address", "hostname", "status_tag", "scan_time", "is_alert_sent"]
        else:
            headers = []

        for row in rows:
            record = dict(zip(headers, row))
            table.append(record)
        
        db[self.table_name] = table
        _save_db(db)

def get_database_sheets():
    """
    Overrides the Google Sheets connection and uses local JSON instead.
    Returns duck-typed objects that behave like gspread worksheets.
    """
    return {
        "devices": MockSheet("devices"),
        "scan_logs": MockSheet("scan_logs")
    }
