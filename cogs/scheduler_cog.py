import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
from io import BytesIO
import config
from utils import drive, time_utils
from services.sheets_service import SheetsService

class SchedulerCog(commands.Cog):
    def __init__(self, bot, sheets_service: SheetsService):
        self.bot = bot
        self.sheets = sheets_service
        self.schedule_loop.start()

    def cog_unload(self):
        self.schedule_loop.cancel()

    @tasks.loop(minutes=1)
    async def schedule_loop(self):
        try:
            current_time = time_utils.get_current_time()
            # Format: H:MM or HH:MM? The prompt says "Match current minute".
            # Usually we compare H:MM to the sheet's time string.
            current_time_str = current_time.strftime("%H:%M").lstrip('0') # "8:05"
            current_time_str_padded = current_time.strftime("%H:%M") # "08:05"
            current_date_str = current_time.strftime("%Y-%m-%d")

            ws = await self.sheets.get_worksheet("DiscordBot", "Schedule")
            if not ws:
                print("Schedule sheet not found")
                return

            rows = await self.sheets.get_all_values(ws)
            if len(rows) < 2:
                return # header only or empty

            # Schedule columns: A=Content(0), B=Date(1), C=Time(2), D=Sent(3), E=Attach(4), F=ChannelID(5), G=Mentions(6), H=Reactions(7)
            
            # Identify updates needed
            updates = [] # (row_idx, col_idx, value)

            for i, row in enumerate(rows[1:]): # skip header
                row_idx = i + 2 # 1-based index in sheet

                # Safe access
                def get_col(idx):
                    return row[idx] if len(row) > idx else ""

                content = get_col(0)
                date_val = get_col(1)
                time_val = get_col(2)
                sent_flag = get_col(3)
                attach_url = get_col(4)
                channel_id_str = get_col(5)
                mentions = get_col(6)
                reactions = get_col(7)

                if sent_flag.upper() == "TRUE":
                    continue

                # Check Match
                # Handle varying time formats
                # If time_val in sheet is "8:05" or "08:05", match either
                time_match = (time_val == current_time_str or time_val == current_time_str_padded)
                date_match = (date_val == current_date_str)

                if date_match and time_match:
                    # SEND MESSAGE
                    await self.send_message(
                        row_idx, content, attach_url, channel_id_str, mentions, reactions
                    )

        except Exception as e:
            print(f"Scheduler Loop Error: {e}")
            # If we want to log unique errors to crash log we could, but don't spam
            # self.bot.crash_logger.log_crash_sync(e) # Wait, need access to crash logger
            pass

    async def send_message(self, row_idx, content, attach_url, channel_id_str, mentions, reactions):
        try:
            channel_id = int(channel_id_str)
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Try fetch?
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    print(f"Channel {channel_id} not found")
                    return

            final_content = content
            if mentions:
                final_content = f"{mentions} {content}"

            files = []
            if attach_url:
                dl_url = drive.convert_drive_url(attach_url)
                if dl_url.startswith("http"):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(dl_url) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                # Filename? Try to get from header or default
                                filename = "attachment.png" # Simple default
                                files.append(discord.File(BytesIO(data), filename=filename))

            msg = await channel.send(final_content, files=files)

            # Reactions
            if reactions:
                emojis = reactions.split()
                for e in emojis:
                    try:
                        await msg.add_reaction(e)
                    except:
                        pass # Ignore invalid emojis

            # Mark Sent
            ws_schedule = await self.sheets.get_worksheet("DiscordBot", "Schedule")
            task1 = self.sheets.update_cell(ws_schedule, row_idx, 4, "TRUE")
            
            # Log to Logs
            ws_logs = await self.sheets.get_worksheet("DiscordBot", "Logs")
            if ws_logs:
                ts = time_utils.get_current_time().isoformat()
                task2 = self.sheets.append_row(ws_logs, [ts, str(channel_id), row_idx, content])
                
            await asyncio.gather(task1, task2)

        except Exception as e:
            print(f"Failed to send scheduled msg row {row_idx}: {e}")

