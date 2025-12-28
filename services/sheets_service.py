import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import json
import base64
import config
from datetime import datetime

class SheetsService:
    def __init__(self):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = self._get_creds()
        self.client = None
    
    def _get_creds(self):
        try:
            if not config.CREDENTIALS_B64:
                print("Warning: CREDENTIALS_B64 is not set.")
                return None
            
            # Decode B64
            # Add padding if needed
            b64_str = config.CREDENTIALS_B64.strip()
            padding = len(b64_str) % 4
            if padding == 1:
                # Invalid length (1 more than multiple of 4), likely a missing char or extra char. 
                # Try adding 3 equals? Or maybe remove 1? 
                # Usually standard b64 doesn't have remainder 1. 
                # But let's try standard padding fix.
                print("Warning: Invalid Base64 length (mod 4 == 1). Attempting to fix...")
                b64_str += "===" # excessive but maybe works? 
                # Actually, remainder 1 is impossible in valid b64 unless corrupted.
                # Remainder 2 needs '=='
                # Remainder 3 needs '='
                # But let's just make it robust.
            elif padding == 2:
                b64_str += "=="
            elif padding == 3:
                b64_str += "="
                
            # Extra safety: try/except the decode
            try:
                json_str = base64.b64decode(b64_str).decode('utf-8')
            except Exception as e:
                # Try adding one more padding just in case
                json_str = base64.b64decode(b64_str + "=").decode('utf-8')

            creds_dict = json.loads(json_str)
            
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
        except Exception as e:
            print(f"Failed to decode credentials: {e}")
            return None

    async def connect(self):
        """Connects to gspread in a thread."""
        if not self.creds:
            return
        
        def _connect():
            self.client = gspread.authorize(self.creds)
        
        await asyncio.to_thread(_connect)

    async def get_worksheet(self, sheet_name, tab_name):
        """
        Opens a spreadsheet by name and gets the specific tab. 
        Note: The prompt implies one main spreadsheet or using open_by_url? 
        The prompt says 'read Google Sheet tab "Schedule"'. It doesn't specify if it's the SAME spreadsheet as streaks/logs.
        Usually bots use one main sheet. I will assume one main spreadsheet name is configured or I'll search for one.
        Wait, prompt says "read Google Sheet tab 'Schedule'".
        It also mentions "CrashLogs" sheet, "Streaks" sheet.
        Likely all in ONE spreadsheet. The user probably has a specific spreadsheet Name. 
        Ah, the prompt doesn't specify the SPREADSHEET_NAME env var.
        But it says "read Google Sheet tab...".
        Maybe it uses `gspread.open('MyBotSheet')`? Or key?
        I'll add SPREADSHEET_NAME to config with a default or assume the user sets it.
        Actually, looking at the previous specific functionality: "CrashLogs sheet (create it with headers if missing)".
        I'll implement a `get_worksheet` that tries to open the spreadsheet (let's call it "DiscordBotData" or configurable).
        I'll add `SHEET_NAME` to config, default "DiscordBot".
        """
        def _get():
            try:
                # Use a default name if not in env, or maybe I should check if there IS an env for it.
                # The prompt listed SPECIFIC env vars to KEEP. It didn't list SHEET_NAME.
                # Maybe the previous code had it hardcoded.
                # I will define `SHEET_NAME` in config as "DiscordBot" or allow override.
                sheet_name_to_use = getattr(config, "SHEET_NAME", "DiscordBot") 
                # Or maybe the key is used? 
                # To be safe, I'll log if I can't find it.
                sh = self.client.open(sheet_name_to_use)
                try:
                    return sh.worksheet(tab_name)
                except gspread.WorksheetNotFound:
                    # Create if missing (required for CrashLogs)
                    # For Schedule/Streaks, we expect them to exist, but creating is safer?
                    # Prompt says "CrashLogs... create it...". Doesn't explicitly say for others.
                    # I'll enable creation logic if needed.
                    if tab_name == "CrashLogs":
                        ws = sh.add_worksheet(title="CrashLogs", rows=100, cols=10)
                        ws.append_row(["Timestamp", "Error", "Traceback"])
                        return ws
                    elif tab_name == "UserExport": # Mentioned in prompt
                         ws = sh.add_worksheet(title=tab_name, rows=1000, cols=3)
                         ws.append_row(["User ID", "Username", "Nickname"])
                         return ws
                    return None
            except Exception as e:
                print(f"Error opening sheet {sheet_name_to_use}/{tab_name}: {e}")
                return None

        return await asyncio.to_thread(_get)

    async def append_row(self, worksheet, row_data):
        def _append():
             worksheet.append_row(row_data)
        await asyncio.to_thread(_append)

    async def get_all_records(self, worksheet):
        def _get():
            return worksheet.get_all_records()
        return await asyncio.to_thread(_get)
    
    async def get_all_values(self, worksheet):
        def _get():
            return worksheet.get_all_values()
        return await asyncio.to_thread(_get)

    async def update_cell(self, worksheet, row, col, value):
        def _update():
            worksheet.update_cell(row, col, value)
        await asyncio.to_thread(_update)
