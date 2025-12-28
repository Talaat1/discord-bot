import discord
import os
import sys
import time
import asyncio
import traceback
import config
import webserver # Keepalive
from services.sheets_service import SheetsService
from services.streak_service import StreakService
from services.crash_logger import CrashLogger
from cogs.scheduler_cog import SchedulerCog
from cogs.streaks_cog import StreaksCog
from cogs.admin_cog import AdminCog

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Services
# Services that don't depend on loop can stay global or move in.
# SheetsService is fine global or local, but safer local to ensure clean state on restart.
# let's move everything into main to be safe.

async def main():
    try:
        # Start Webserver Thread
        webserver.keep_alive()

        # Initialize Bot inside the loop
        bot = discord.Bot(intents=intents)
        
        # Initialize Services
        sheets_service = SheetsService()
        streak_service = StreakService(sheets_service)
        crash_logger = CrashLogger(sheets_service)

        # Global error handler (needs to be attached to the local 'bot')
        @bot.event
        async def on_application_command_error(ctx, error):
            if isinstance(error, discord.ext.commands.CommandOnCooldown):
                await ctx.respond(str(error), ephemeral=True)
            elif isinstance(error, discord.ext.commands.MissingRole):
                await ctx.respond("You do not have permission to use this command.", ephemeral=True)
            else:
                print(f"Command Error: {error}")
                await crash_logger.log_crash(error)
                await ctx.respond("An error occurred.", ephemeral=True)

        @bot.event
        async def on_ready():
            print(f"Logged in as {bot.user} (ID: {bot.user.id})")
            
            # Init sheets connection
            await sheets_service.connect()
            if sheets_service.client:
                print("Sheets service connected.")
            else:
                print("WARNING: Sheets service FAILED to connect (Check CREDENTIALS_B64).")

        # Load Cogs
        bot.add_cog(SchedulerCog(bot, sheets_service))
        bot.add_cog(StreaksCog(bot, streak_service))
        bot.add_cog(AdminCog(bot, sheets_service))
        
        # Run Bot
        if not config.DISCORD_BOT_TOKEN:
            print("Error: DISCORD_BOT_TOKEN not found.")
            return

        await bot.start(config.DISCORD_BOT_TOKEN)

    except Exception as e:
        # General Crash Handling
        print("CRITICAL ERROR IN MAIN LOOP")
        # Need access to crash_logger if it exists
        try:
            if 'crash_logger' in locals():
                await crash_logger.log_crash(e)
            else:
                print(f"Crash before logger init: {e}")
        except:
            traceback.print_exc()

        # Restart
        print("Restarting in 5 seconds...")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Fallback for asyncio.run failure
        crash_logger.log_crash_sync(e)
        print("Fatal startup error. Restarting...")
        time.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)
