import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import json
import base64
import config
from datetime import datetime
import os

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
            # Priority 1: Local File 'credentials.json' (Bypasses broken env var)
            if os.path.exists("credentials.json"):
                print("Found credentials.json, using it...")
                try:
                    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", self.scope)
                except Exception as e:
                    print(f"Failed to load credentials.json: {e}")

            if not config.CREDENTIALS_B64:            
                print("Warning: CREDENTIALS_B64 is not set and credentials.json not found.")
                return None
            
            # Check if it's already JSON (starts with {)
            raw_val = config.CREDENTIALS_B64.strip()
            print(f"DEBUG: CREDENTIALS_B64 start: '{raw_val[:20]}...'")
            print(f"DEBUG: Length: {len(raw_val)}")

            # Try parsing as JSON directly first (regardless of start char)
            try:
                creds_dict = json.loads(raw_val)
                print("DEBUG: Successfully parsed as Raw JSON")
                return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
            except json.JSONDecodeError:
                print("DEBUG: Not valid JSON. Attempting Base64...")
            except Exception as e:
                print(f"DEBUG: JSON parse error: {e}")

            # Decode B64
            # Robust cleanup: Remove ALL whitespace
            b64_str = "".join(raw_val.split())
            
            # Brute force padding (Standard logic failed for some reason)
            decoded_json = None
            last_error = None
            
            for pad in ["", "=", "==", "==="]:
                try:
                    current_try = b64_str + pad
                    decoded_bytes = base64.b64decode(current_try, validate=True) # Validating might be stricter, but try it.
                    decoded_json = decoded_bytes.decode('utf-8')
                    # If we got here, it worked!
                    print(f"DEBUG: Base64 decode successful with padding '{pad}'")
                    break
                except Exception as e:
                    last_error = e
                    # Continue to next padding
            
            if decoded_json is None:
                print(f"Failed to decode credentials after all attempts. Last error: {last_error}")
                # Fallback: Try non-validated decode if available or just crash gracefully
                try:
                     # One last hail mary: standard b64decode usually handles missing padding if not strict?
                     # Actually Python's b64decode is strict about length.
                     return None
                except:
                    return None

            creds_dict = json.loads(decoded_json)
            
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
        except Exception as e:
            print(f"Failed to load credentials: {e}")
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
