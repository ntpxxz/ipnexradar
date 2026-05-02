import sys
from scanner import analyze_and_record

def simulate_scenarios():
    print("--- 🔄 IPNEX Multi-Scenario Simulator ---")
    
    # In database.json, Admin-PC is 192.168.1.100 (MAC: 00:11:22:33:44:55)
    
    # ------------------ SCAN 1 ------------------
    mock_scan_1 = [
        # 1. NORMAL (Admin PC is online and unchanged)
        {"ip": "192.168.1.100", "mac": "00:11:22:33:44:55"},
        
        # 2. NEW_DEVICE (A brand new phone/laptop joined the Wi-Fi)
        {"ip": "192.168.1.105", "mac": "aa:bb:cc:dd:ee:ff"},
    ]
    
    print("\n[Simulator] Scan 1: Adding a NEW_DEVICE and verifying NORMAL...")
    analyze_and_record(mock_scan_1)
    
    # ------------------ SCAN 2 ------------------
    mock_scan_2 = [
        # 3. IP_MOVED (The new phone changed its IP from .105 to .110 due to DHCP)
        {"ip": "192.168.1.110", "mac": "aa:bb:cc:dd:ee:ff"},
        
        # 4. SPOOFING_ATTEMPT (A hacker takes the Admin PC's IP 192.168.1.100 with a fake MAC)
        {"ip": "192.168.1.100", "mac": "99:88:77:66:55:44"}
    ]
    
    print("\n[Simulator] Scan 2: Triggering IP_MOVED and SPOOFING_ATTEMPT...")
    analyze_and_record(mock_scan_2)
    
    print("\n[Simulator] Complete! Check your Dashboard to see the new device and check scan_logs for the events.")

if __name__ == "__main__":
    simulate_scenarios()
