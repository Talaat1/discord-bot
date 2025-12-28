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

bot = discord.Bot(intents=intents)

# Services
sheets_service = SheetsService()
streak_service = StreakService(sheets_service)
crash_logger = CrashLogger(sheets_service)

# Global error handler for the bot tree
@bot.event
async def on_application_command_error(ctx, error):
    # Handle cooldown
    if isinstance(error, discord.ext.commands.CommandOnCooldown):
        await ctx.respond(str(error), ephemeral=True)
    elif isinstance(error, discord.ext.commands.MissingRole):
        await ctx.respond("You do not have permission to use this command.", ephemeral=True)
    else:
        # Log unexpected errors
        print(f"Command Error: {error}")
        await crash_logger.log_crash(error)
        await ctx.respond("An error occurred.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Init sheets connection
    await sheets_service.connect()
    print("Sheets service connected.")

async def main():
    try:
        # Start Webserver Thread
        webserver.keep_alive()
        
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
        
        # Log
        # Use sync logging if loop is dead, but we are in async main, so try async first.
        try:
            await crash_logger.log_crash(e)
        except:
            crash_logger.log_crash_sync(e)

        # Notify Owner
        owner_id = config.BOT_OWNER_ID
        if owner_id:
            try:
                # If bot is still capable of fetching user
                # We need a new session maybe if `bot` is dead? 
                # `bot` might be closed or closing.
                # Try simple request if possible? 
                # "Best effort"
                pass 
                # Usually difficult effectively if the loop is crashing. 
                # But if it's an exception `await bot.start` threw, `bot` might be approachable.
            except:
                pass

        # Restart
        print("Restarting in 5 seconds...")
        time.sleep(5)
        # execv
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
