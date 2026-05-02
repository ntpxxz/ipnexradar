import socket
from datetime import datetime
from scapy.all import ARP, Ether, srp
from database import get_db_connection
from notifier import send_line_notify

def get_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return ""

def scan_network(ip_range="192.168.1.0/24"):
    print(f"Scanning network: {ip_range}...")
    arp = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    
    try:
        # If scanner fails completely, it throws exception, preserving T-006 logic
        result = srp(packet, timeout=3, verbose=0)[0]
    except Exception as e:
        print(f"SCAN_ERROR: {e}")
        return None # Graceful failure

    devices = []
    for sent, received in result:
        devices.append({'ip': received.psrc, 'mac': received.hwsrc.lower()})
    
    print(f"Found {len(devices)} active devices.")
    return devices

def analyze_and_record(scanned_devices):
    # T-006: Do NOT mark devices offline if scan completely failed
    if scanned_devices is None:
        print("Scan failed. Skipping database updates to prevent false offline alerts.")
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
        
        # T-010: Anti-Spoofing Check
        existing_device_with_ip = db_by_ip.get(ip)
        if existing_device_with_ip and existing_device_with_ip['mac_address'].lower() != mac:
            if existing_device_with_ip['status'] == 'online':
                alert_msg = f"\n⚠️ [SPOOFING ALERT]\nIP: {ip}\nDetected MAC: {mac}\nExpected MAC: {existing_device_with_ip['mac_address']}"
                print(alert_msg)
                send_line_notify(alert_msg)
                
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (existing_device_with_ip['device_id'], 'SUSPICIOUS_CHANGE', 'mac_address', existing_device_with_ip['mac_address'], mac, now_str))
        
        # T-008: Change Detection Engine
        if mac in db_by_mac:
            known_device = db_by_mac[mac]
            device_id = known_device['device_id']
            
            # Reconnect device
            if known_device['status'] == 'offline':
                cursor.execute("UPDATE devices SET status='online' WHERE device_id=?", (device_id,))
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (?, 'STATUS_CHANGE', 'status', 'offline', 'online', ?)
                ''', (device_id, now_str))
            
            # IP Update
            if known_device['ip_address'] != ip:
                cursor.execute("UPDATE devices SET ip_address=? WHERE device_id=?", (ip, device_id))
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (?, 'UPDATE_IP', 'ip_address', ?, ?, ?)
                ''', (device_id, known_device['ip_address'], ip, now_str))
                
            # Hostname Update
            if hostname and known_device['hostname'] != hostname:
                cursor.execute("UPDATE devices SET hostname=? WHERE device_id=?", (hostname, device_id))
                cursor.execute('''
                    INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                    VALUES (?, 'UPDATE_HOSTNAME', 'hostname', ?, ?, ?)
                ''', (device_id, known_device['hostname'], hostname, now_str))
                
            cursor.execute("UPDATE devices SET last_seen=? WHERE device_id=?", (now_str, device_id))
            
        else:
            # T-007: New Device Detection
            cursor.execute('''
                INSERT INTO devices (hostname, ip_address, mac_address, status, first_seen, last_seen)
                VALUES (?, ?, ?, 'online', ?, ?)
            ''', (hostname, ip, mac, now_str, now_str))
            device_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO device_history (device_id, change_type, field_changed, new_value, changed_at)
                VALUES (?, 'INSERT', 'mac_address', ?, ?)
            ''', (device_id, mac, now_str))
            
            db_by_mac[mac] = {'device_id': device_id, 'ip_address': ip, 'mac_address': mac, 'status': 'online'}

    # T-009: Offline Detection
    for mac, record in db_by_mac.items():
        if mac not in scanned_macs and record['status'] == 'online':
            cursor.execute("UPDATE devices SET status='offline' WHERE device_id=?", (record['device_id'],))
            cursor.execute('''
                INSERT INTO device_history (device_id, change_type, field_changed, old_value, new_value, changed_at)
                VALUES (?, 'STATUS_CHANGE', 'status', 'online', 'offline', ?)
            ''', (record['device_id'], now_str))
            print(f"Device {mac} ({record['ip_address']}) is now OFFLINE.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    TARGET_SUBNET = "192.168.1.0/24" 
    scanned_data = scan_network(TARGET_SUBNET)
    analyze_and_record(scanned_data)
