from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db_connection
from scanner import scan_network, analyze_and_record

app = FastAPI(title="IP Monitoring API", description="Using SQLite as Database")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    subnet: str

class DeviceCreate(BaseModel):
    hostname: str
    ip_address: str
    mac_address: str
    is_reserved: bool = False

@app.get("/")
def read_root():
    return {"message": "IP Monitoring & Anti-Spoofing API is running"}

@app.get("/health/db")
def check_db_health():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices")
def get_devices():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all devices
        cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Check for IP changes in the last 7 days for each device
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        
        for device in devices:
            cursor.execute("""
                SELECT 1 FROM device_history 
                WHERE device_id = ? AND change_type = 'UPDATE_IP' AND changed_at >= ?
                LIMIT 1
            """, (device['device_id'], seven_days_ago))
            device['has_recent_ip_change'] = cursor.fetchone() is not None
            
        conn.close()
        return {"data": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/devices")
def register_device(device: DeviceCreate):
    """
    Manually register a new device into the master database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if MAC already exists
        cursor.execute("SELECT device_id FROM devices WHERE mac_address = ?", (device.mac_address.lower(),))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="MAC Address already exists in database")
            
        cursor.execute('''
            INSERT INTO devices (hostname, ip_address, mac_address, status, is_reserved, first_seen, last_seen)
            VALUES (?, ?, ?, 'online', ?, ?, ?)
        ''', (device.hostname, device.ip_address, device.mac_address.lower(), 1 if device.is_reserved else 0, now_str, now_str))
        
        device_id = cursor.lastrowid
        
        # Log the manual insertion
        cursor.execute('''
            INSERT INTO device_history (device_id, change_type, field_changed, new_value, changed_at)
            VALUES (?, 'INSERT', 'manual_registration', ?, ?)
        ''', (device_id, device.mac_address, now_str))
        
        conn.commit()
        conn.close()
        return {"message": "Device registered successfully", "device_id": device_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
def get_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT h.*, d.mac_address, d.ip_address 
            FROM device_history h 
            JOIN devices d ON h.device_id = d.device_id 
            ORDER BY h.changed_at DESC LIMIT 100
        ''')
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lookup/{identifier}")
def lookup_device(identifier: str):
    """
    Looks up a device by ID or Hostname.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if identifier.isdigit():
            cursor.execute("SELECT * FROM devices WHERE device_id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM devices WHERE hostname = ?", (identifier,))
            
        device = cursor.fetchone()
        conn.close()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
            
        device_dict = dict(device)
        return device_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
def trigger_manual_scan(request: ScanRequest):
    """
    Manually trigger a network scan for a specific IP or subnet.
    """
    try:
        scanned_data = scan_network(request.subnet)
        if scanned_data is None:
            raise HTTPException(status_code=500, detail="Scanner failed (Check sudo/root privileges)")
        
        analyze_and_record(scanned_data)
        return {"message": f"Successfully scanned {request.subnet}", "devices_found": len(scanned_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
