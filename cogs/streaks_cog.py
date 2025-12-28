import discord
from discord.ext import commands
import config
from utils import cooldown
from services.streak_service import StreakService

class StreaksCog(commands.Cog):
    def __init__(self, bot, streak_service: StreakService):
        self.bot = bot
        self.streak_service = streak_service

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Only track in STREAK_CHANNEL_ID
        if config.STREAK_CHANNEL_ID and message.channel.id != config.STREAK_CHANNEL_ID:
            return
            
        # Update username in sheet and tick streak
        # "One streak '🔥 …' message per user per day"
        new_streak, shown_date = await self.streak_service.update_streak(
            message.author.id, message.author.name
        )
        
        if new_streak:
            today_str = config.get_current_time().strftime("%Y-%m-%d")
            # If shown_date != today, send message and mark shown
            if shown_date != today_str:
                await message.reply(f"🔥 Current streak for {message.author.mention}: {new_streak} days!")
                await self.streak_service.mark_shown(message.author.id, today_str)

    @discord.slash_command(name="streak", description="Show your current streak")
    @cooldown.apply_cooldown()
    async def streak(self, ctx):
        # "should also update/touch streak like current behavior"
        new_streak, shown_date = await self.streak_service.update_streak(
            ctx.author.id, ctx.author.name
        )
        await ctx.respond(f"🔥 {ctx.author.mention}, your streak is: {new_streak} days!")
        
        # Should we mark shown? Usually explicit checks don't burn the daily notification if it wasn't automatic, but prompt says "One streak... per day".
        # If they check it manually, maybe that counts as the "message"? 
        # But `on_message` handles the automatic one. 
        # I'll update shown_date if it wasn't shown, to avoid double pinging? 
        # Or maybe /streak is separate. Let's leave it as just showing.
    
    @discord.slash_command(name="topstreaks", description="Show top streaks leaderboard")
    @cooldown.apply_cooldown()
    async def topstreaks(self, ctx):
        top = await self.streak_service.get_top_streaks(limit=10)
        if not top:
            await ctx.respond("No streaks found.", ephemeral=True)
            return
            
        msg = "**Top Streaks**\n"
        for i, entry in enumerate(top):
            # entry columns matching sheet headers
            username = entry.get('Username', 'Unknown')
            streak = entry.get('Streak', 0)
            msg += f"{i+1}. {username}: {streak} 🔥\n"
        
        await ctx.respond(msg)

    @discord.slash_command(name="resetstreak", description="Admin: Reset a user's streak")
    @commands.has_role(config.ADMIN_ROLE_NAME)
    async def resetstreak(self, ctx, user: discord.Member):
        success = await self.streak_service.reset_streak(user.id)
        if success:
            await ctx.respond(f"Reset streak for {user.mention}.", ephemeral=True)
        else:
            await ctx.respond(f"Could not find entry for {user.mention}.", ephemeral=True)
