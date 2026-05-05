import socket
from datetime import datetime
from scapy.all import ARP, Ether, srp
from database import get_db_connection
from notifier import send_line_notify
from logger import get_logger

logger = get_logger(__name__)

def get_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return ""

def scan_network(ip_range="192.168.1.0/24"):
    logger.info(f"Scanning network: {ip_range}...")
    arp = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    
    try:
        # If scanner fails completely, it throws exception, preserving T-006 logic
        result = srp(packet, timeout=3, verbose=0)[0]
    except Exception as e:
        logger.error(f"SCAN_ERROR: {e}", exc_info=True)
        return None # Graceful failure

    devices = []
    for sent, received in result:
        devices.append({'ip': received.psrc, 'mac': received.hwsrc.lower()})
    
    logger.info(f"Found {len(devices)} active devices.")
    return devices

def analyze_and_record(scanned_devices):
    # T-006: Do NOT mark devices offline if scan completely failed
    if scanned_devices is None:
        logger.error("Scan failed. Skipping database updates to prevent false offline alerts.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM devices")
    db_records = cursor.fetchall()
    
    db_by_mac = {r['mac_address'].lower(): r for r in db_records}
    db_by_ip = {r['ip_address']: r for r in db_records}
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scanned_macs = set()

    for device in scanned_devices:
        ip = device['ip']
        mac = device['mac']
        hostname = get_hostname(ip)
        scanned_macs.add(mac)
        
        existing_device = db_by_ip.get(ip)
        
        if existing_device:
            device_id = existing_device['device_id']
            db_mac = existing_device['mac_address'].lower()
            
            # If the MAC was set to unknown placeholder by Excel Sync
            if db_mac.startswith('unknown-'):
                cursor.execute("UPDATE devices SET mac_address=%s, status='online', last_seen=%s WHERE device_id=%s", (mac, now_str, device_id))
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (%s, 'UPDATE_MAC', 'mac_address', %s, %s, %s)
                ''', (device_id, db_mac, mac, now_str))
                
                db_by_mac[mac] = existing_device
                existing_device['mac_address'] = mac
                existing_device['status'] = 'online'
                
            elif db_mac != mac:
                # Anti-Spoofing: IP matches but MAC is different
                if existing_device['status'] == 'online':
                    alert_msg = f"\n⚠️ [SPOOFING ALERT]\nIP: {ip}\nDetected MAC: {mac}\nExpected MAC: {db_mac}"
                    logger.warning(alert_msg)
                    send_line_notify(alert_msg)
                    
                    cursor.execute('''
                        INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (device_id, 'SUSPICIOUS_CHANGE', 'mac_address', db_mac, mac, now_str))
            
            else:
                # Regular match
                if existing_device['status'] == 'offline':
                    cursor.execute("UPDATE devices SET status='online' WHERE device_id=%s", (device_id,))
                    cursor.execute('''
                        INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                        VALUES (%s, 'STATUS_CHANGE', 'status', 'offline', 'online', %s)
                    ''', (device_id, now_str))
                    
                if hostname and existing_device['hostname'] != hostname:
                    cursor.execute("UPDATE devices SET hostname=%s WHERE device_id=%s", (hostname, device_id))
                    cursor.execute('''
                        INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                        VALUES (%s, 'UPDATE_HOSTNAME', 'hostname', %s, %s, %s)
                    ''', (device_id, existing_device['hostname'], hostname, now_str))
                    
                cursor.execute("UPDATE devices SET last_seen=%s WHERE device_id=%s", (now_str, device_id))
                
        else:
            # IP doesn't exist. Did device move to a new IP?
            if mac in db_by_mac:
                known_device = db_by_mac[mac]
                device_id = known_device['device_id']
                
                cursor.execute("UPDATE devices SET ip_address=%s, status='online', last_seen=%s WHERE device_id=%s", (ip, now_str, device_id))
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (%s, 'UPDATE_IP', 'ip_address', %s, %s, %s)
                ''', (device_id, known_device['ip_address'], ip, now_str))
            else:
                # T-007: Completely New Device
                cursor.execute('''
                    INSERT INTO devices (hostname, ip_address, mac_address, status, first_seen, last_seen)
                    VALUES (%s, %s, %s, 'online', %s, %s) RETURNING device_id
                ''', (hostname, ip, mac, now_str, now_str))
                device_id = cursor.fetchone()['device_id']
                
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, new_value, changed_at)
                    VALUES (%s, 'INSERT', 'mac_address', %s, %s)
                ''', (device_id, mac, now_str))
                
                db_by_mac[mac] = {'device_id': device_id, 'ip_address': ip, 'mac_address': mac, 'status': 'online'}

    # T-009: Offline Detection
    for mac, record in db_by_mac.items():
        if mac not in scanned_macs and record['status'] == 'online':
            cursor.execute("UPDATE devices SET status='offline' WHERE device_id=%s", (record['device_id'],))
            cursor.execute('''
                INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                VALUES (%s, 'STATUS_CHANGE', 'status', 'online', 'offline', %s)
            ''', (record['device_id'], now_str))
            logger.info(f"Device {mac} ({record['ip_address']}) is now OFFLINE.")

    conn.commit()
    conn.close()
    
    # Sync updates back to excel master
    from excel_sync import sync_db_to_excel
    sync_db_to_excel()

if __name__ == "__main__":
    TARGET_SUBNET = "192.168.1.0/24" 
    scanned_data = scan_network(TARGET_SUBNET)
    analyze_and_record(scanned_data)
