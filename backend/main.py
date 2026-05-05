from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db_connection
from scanner import scan_network, analyze_and_record
from excel_sync import sync_excel_to_db, sync_db_to_excel
import ipaddress
from logger import get_logger

logger = get_logger(__name__)

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

# Synchronize master database on startup
sync_excel_to_db()

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
        logger.error(f"Error checking db health: {e}", exc_info=True)
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
                SELECT change_type, old_value, new_value FROM device_history 
                WHERE device_id = %s AND changed_at >= %s
                ORDER BY changed_at DESC LIMIT 1
            """, (device['device_id'], seven_days_ago))
            recent_change = cursor.fetchone()
            device['has_recent_ip_change'] = False
            device['remark'] = ""
            
            if recent_change:
                ctype = recent_change['change_type']
                if ctype == 'UPDATE_IP':
                    device['has_recent_ip_change'] = True
                    device['remark'] = f"IP moved from {recent_change['old_value']}"
                elif ctype == 'UPDATE_HOSTNAME':
                    device['remark'] = f"Hostname updated to {recent_change['new_value']}"
                elif ctype == 'SUSPICIOUS_CHANGE':
                    device['remark'] = f"Spoofing Attempt! Expected MAC: {recent_change['old_value']}"
                elif ctype == 'STATUS_CHANGE':
                    device['remark'] = f"Turned {recent_change['new_value']}"
                elif ctype == 'INSERT':
                    device['remark'] = "Newly Registered"
                    
        conn.close()
        return {"data": devices}
    except Exception as e:
        logger.error(f"Error computing devices: {e}", exc_info=True)
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
        cursor.execute("SELECT device_id FROM devices WHERE mac_address = %s", (device.mac_address.lower(),))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="MAC Address already exists in database")
            
        cursor.execute('''
            INSERT INTO devices (hostname, ip_address, mac_address, status, is_reserved, first_seen, last_seen)
            VALUES (%s, %s, %s, 'online', %s, %s, %s) RETURNING device_id
        ''', (device.hostname, device.ip_address, device.mac_address.lower(), True if device.is_reserved else False, now_str, now_str))
        
        device_id = cursor.fetchone()['device_id']
        
        # Log the manual insertion
        cursor.execute('''
            INSERT INTO device_history (device_id, change_type, field_changed, new_value, changed_at)
            VALUES (%s, 'INSERT', 'manual_registration', %s, %s)
        ''', (device_id, device.mac_address, now_str))
        
        conn.commit()
        conn.close()
        return {"message": "Device registered successfully", "device_id": device_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}", exc_info=True)
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
        logger.error(f"Error getting logs: {e}", exc_info=True)
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
            cursor.execute("SELECT * FROM devices WHERE device_id = %s", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM devices WHERE hostname = %s", (identifier,))
            
        device = cursor.fetchone()
        conn.close()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
            
        device_dict = dict(device)
        return device_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up device: {e}", exc_info=True)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/network/unused")
def get_unused_ips(subnet: str = "192.168.1.0/24"):
    try:
        network = ipaddress.IPv4Network(subnet, strict=False)
        all_ips = [str(ip) for ip in network.hosts()]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address FROM devices")
        used_ips = set(r['ip_address'] for r in cursor.fetchall())
        conn.close()
        
        unused = [ip for ip in all_ips if ip not in used_ips]
        return {"subnet": subnet, "unused_ips": unused, "total_unused": len(unused)}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subnet CIDR format")
    except Exception as e:
        logger.error(f"Error getting unused IPs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
