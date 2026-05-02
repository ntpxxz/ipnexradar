import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
from scanner import scan_network, analyze_and_record

# Modify to match your target subnet
TARGET_SUBNET = os.getenv("TARGET_SUBNET", "192.168.1.0/24")

def scan_job():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Starting Scheduled Scan for {TARGET_SUBNET}")
    try:
        scanned_data = scan_network(TARGET_SUBNET)
        analyze_and_record(scanned_data)
    except Exception as e:
        print(f"❌ Error during scheduled scan: {e}")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Scan Completed.")

if __name__ == "__main__":
    print("Initializing Background Scheduler...")
    
    scheduler = BackgroundScheduler()
    # Schedule the scan to run every 5 minutes
    scheduler.add_job(scan_job, 'interval', minutes=5)
    scheduler.start()
    
    print(f"🚀 Scheduler is active! Scanning {TARGET_SUBNET} every 5 minutes.")
    print("Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive while scheduler runs in background
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping Scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped gracefully.")
