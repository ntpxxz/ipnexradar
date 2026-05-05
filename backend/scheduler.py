import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
from scanner import scan_network, analyze_and_record
from logger import get_logger

logger = get_logger(__name__)

# Modify to match your target subnet
TARGET_SUBNET = os.getenv("TARGET_SUBNET", "192.168.1.0/24")

def scan_job():
    logger.info(f"⏳ Starting Scheduled Scan for {TARGET_SUBNET}")
    try:
        scanned_data = scan_network(TARGET_SUBNET)
        analyze_and_record(scanned_data)
    except Exception as e:
        logger.error(f"❌ Error during scheduled scan: {e}", exc_info=True)
    logger.info("✅ Scan Completed.")

if __name__ == "__main__":
    logger.info("Initializing Background Scheduler...")
    
    scheduler = BackgroundScheduler()
    # Schedule the scan to run every 5 minutes
    scheduler.add_job(scan_job, 'interval', minutes=5)
    scheduler.start()
    
    logger.info(f"🚀 Scheduler is active! Scanning {TARGET_SUBNET} every 5 minutes.")
    logger.info("Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive while scheduler runs in background
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping Scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped gracefully.")
