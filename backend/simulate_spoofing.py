import sys
from scanner import analyze_and_record

def simulate_spoofing():
    print("--- 🚨 IPNEX Spoofing Simulator (Local DB Mode) ---")
    
    # We have a mock device in local_db.py:
    # IP: 192.168.1.100, MAC: 00:11:22:33:44:55
    target_ip = "192.168.1.100"
    fake_mac = "ff:aa:bb:cc:dd:ee"
    
    print(f"\n[Simulator] Injecting scan result: IP {target_ip} is now using Fake MAC {fake_mac}...")
    
    # Mock the output format of scan_network()
    mock_scanned_devices = [
        {"ip": target_ip, "mac": fake_mac}
    ]
    
    print("[Simulator] Analyzing...")
    analyze_and_record(mock_scanned_devices)
    print("\n[Simulator] Complete! Check your Dashboard in the browser. You should see Spoofing Alerts go up!")

if __name__ == "__main__":
    simulate_spoofing()
