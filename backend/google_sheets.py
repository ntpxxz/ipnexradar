import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from logger import get_logger

load_dotenv()
logger = get_logger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service_account.json")

# Define the scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_google_sheet_client():
    try:
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        logger.error(f"Error connecting to Google Sheets: {e}", exc_info=True)
        return None

def get_database_sheets():
    """
    Connects to the Google Spreadsheet and returns the required worksheets.
    Make sure the spreadsheet has tabs named: 'devices', 'scan_logs', 'system_configs'
    """
    client = get_google_sheet_client()
    if not client:
        return None
        
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        
        return {
            "devices": spreadsheet.worksheet("devices"),
            "scan_logs": spreadsheet.worksheet("scan_logs"),
            "system_configs": spreadsheet.worksheet("system_configs")
        }
    except Exception as e:
        logger.error(f"Error opening worksheets: {e}", exc_info=True)
        return None
