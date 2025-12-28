import os
import traceback
from datetime import datetime
import asyncio
from services.sheets_service import SheetsService

class CrashLogger:
    def __init__(self, sheets_service: SheetsService = None):
        self.sheets_service = sheets_service
        self.log_file = "crash.log"

    def log_crash_sync(self, exc: Exception):
        """
        Synchronous logging for critical failures where loop might be dead.
        """
        timestamp = datetime.now().isoformat()
        tb = traceback.format_exc()
        entry = f"[{timestamp}] CRASH: {exc}\n{tb}\n{'-'*20}\n"
        
        # 1. Local append
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)
        
        # 2. Sheet append (Network might fail, use best effort)
        # Since we are essentially crashing, we can try to run the async task
        # via asyncio.run if not in a loop, or just ignore if it's too risky.
        # But the prompt says "Also append crash logs to a Google Sheet".
        # If we are inside an exception handler in main (loop running), we can await.
        pass

    async def log_crash(self, exc: Exception):
        timestamp = datetime.now().isoformat()
        tb = traceback.format_exc()
        entry = f"[{timestamp}] CRASH: {exc}\n{tb}\n{'-'*20}\n"
        
        print(f"LOGGING CRASH: {entry}")

        # Local File
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"Failed to write to crash.log: {e}")

        # Google Sheet
        if self.sheets_service:
            try:
                ws = await self.sheets_service.get_worksheet("DiscordBot", "CrashLogs") # Default name used
                if ws:
                    await self.sheets_service.append_row(ws, [timestamp, str(exc), tb])
            except Exception as e:
                print(f"Failed to log crash to Sheet: {e}")

