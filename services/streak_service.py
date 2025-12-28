import config
from datetime import datetime
from services.sheets_service import SheetsService

class StreakService:
    def __init__(self, sheets_service: SheetsService):
        self.sheets = sheets_service
        self.tab_name = "Streaks"

    async def update_streak(self, user_id, username):
        """
        Updates the streak for a user.
        Logic:
        - If LastActive is today (ShownDate checked separately?), do nothing (or just update username).
        - If LastActive was yesterday, streak += 1.
        - If LastActive was older, streak = 1.
        - Update LastActive = Today.
        
        Wait, the prompt says:
        "One streak '🔥 …' message per user per day (use ShownDate to prevent duplicates)"
        "Persist in Google Sheet... Columns: UserID, Username, LastActive, Streak, ShownDate"
        "Commands: /streak -> show current streak (should also update/touch streak like current behavior)"
        
        So this method is called by /streak OR by the daily message logic? 
        Actually, the "Streak system" bullet says:
        "Only track messages in STREAK_CHANNEL_ID" -> So normal messages trigger it?
        AND "Commands... /streak -> show... also update/touch".
        
        So we need a generic "touch_streak" method.
        """
        ws = await self.sheets.get_worksheet("DiscordBot", self.tab_name)
        if not ws:
            return None, None # Sheet error
        
        # Get all data
        records = await self.sheets.get_all_values(ws)
        # Assuming header row 1
        header = records[0]
        rows = records[1:]
        
        now = config.get_current_time() # Naive local time
        today_str = now.strftime("%Y-%m-%d")
        
        # Find user row
        user_row_idx = -1
        # Columns: UserID (0), Username (1), LastActive (2), Streak (3), ShownDate (4)
        for i, r in enumerate(rows):
            if str(r[0]) == str(user_id):
                user_row_idx = i + 2 # 1-based, +1 for header
                current_user_data = r
                break
        
        new_streak = 1
        
        if user_row_idx != -1:
            # User exists
            last_active = current_user_data[2]
            current_streak = int(current_user_data[3]) if current_user_data[3] else 0
            
            # Check dates
            if last_active:
                last_date = datetime.strptime(last_active, "%Y-%m-%d")
                # Diff
                diff = (now - last_date).days
                if diff == 0:
                    # Same day
                    new_streak = current_streak
                elif diff == 1:
                    # Yesterday
                    new_streak = current_streak + 1
                else:
                    # Broken streak
                    new_streak = 1
            else:
                new_streak = 1
            
            # Update row
            # Helper to update multiple cells? Or just recreate row?
            # gspread update_cell is slow one by one. 
            # Ideally use batch update or just update specific cells. 
            # Update LastActive, Streak, Username
            # Columns 2, 3, 4 (1-indexed based on list, but GSheet is 1-indexed)
            # Username=Col 2, LastActive=Col 3, Streak=Col 4
            
            await self.sheets.update_cell(ws, user_row_idx, 2, username)
            await self.sheets.update_cell(ws, user_row_idx, 3, today_str)
            await self.sheets.update_cell(ws, user_row_idx, 4, new_streak)
            
            # Return streak and shown_date for caller to decide on messaging
            shown_date = current_user_data[4] if len(current_user_data) > 4 else ""
            return new_streak, shown_date
            
        else:
            # New User
            row = [str(user_id), username, today_str, 1, ""]
            await self.sheets.append_row(ws, row)
            return 1, ""

    async def mark_shown(self, user_id, date_str):
        """Updates ShownDate to prevent duplicate messages."""
        ws = await self.sheets.get_worksheet("DiscordBot", self.tab_name)
        if not ws: return
        
        rows = await self.sheets.get_all_values(ws)
        for i, r in enumerate(rows[1:]):
            if str(r[0]) == str(user_id):
                row_idx = i + 2
                await self.sheets.update_cell(ws, row_idx, 5, date_str) # Col 5 is ShownDate
                break

    async def reset_streak(self, user_id):
        ws = await self.sheets.get_worksheet("DiscordBot", self.tab_name)
        if not ws: return False
        
        rows = await self.sheets.get_all_values(ws)
        for i, r in enumerate(rows[1:]):
            if str(r[0]) == str(user_id):
                row_idx = i + 2
                today_str = config.get_current_time().strftime("%Y-%m-%d")
                await self.sheets.update_cell(ws, row_idx, 3, today_str) # LastActive today
                await self.sheets.update_cell(ws, row_idx, 4, 0) # Streak 0
                await self.sheets.update_cell(ws, row_idx, 5, "") # Clear ShownDate
                return True
        return False

    async def get_top_streaks(self, limit=10):
        try:
            ws = await self.sheets.get_worksheet("DiscordBot", self.tab_name)
            if not ws: return []
            
            records = await self.sheets.get_all_records(ws) 
            # Sort by Streak desc
            # Ensure Streak is int
            for r in records:
                try:
                    r['Streak'] = int(r['Streak'])
                except:
                    r['Streak'] = 0
            
            sorted_recs = sorted(records, key=lambda x: x['Streak'], reverse=True)
            return sorted_recs[:limit]
        except Exception as e:
            print(f"Error getting top streaks: {e}")
            return []
