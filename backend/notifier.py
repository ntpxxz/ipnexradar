import os
import requests
from dotenv import load_dotenv
from logger import get_logger

load_dotenv()
logger = get_logger(__name__)

LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN")

def send_line_notify(message: str):
    """
    Sends a Line Notify alert.
    Requires LINE_NOTIFY_TOKEN in .env
    """
    if not LINE_NOTIFY_TOKEN or LINE_NOTIFY_TOKEN == "your_line_notify_token_here":
        logger.warning(f"Skipping Line Notify (Token not configured). Message: {message}")
        return False
        
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    data = {"message": message}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            logger.info("✅ Successfully sent LINE Notify alert.")
            return True
        else:
            logger.error(f"❌ Failed to send LINE alert: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending LINE alert: {e}", exc_info=True)
        return False
