import discord
from discord.ext import commands
import config

class CustomCooldown:
    def __init__(self):
        # 60s cooldown, 1 per bucket
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

    def __call__(self, ctx: "discord.ApplicationContext"):
        # Admin bypass
        if ctx.user is None or isinstance(ctx.user, discord.User):
            # Probably DM or user not in guild
            pass 
        elif isinstance(ctx.user, discord.Member):
            role_names = [role.name for role in ctx.user.roles]
            if config.ADMIN_ROLE_NAME in role_names:
                return True # Bypass

        # Check cooldown
        bucket = self.cooldown.get_bucket(ctx.message if hasattr(ctx, 'message') else ctx.interaction)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(self.cooldown, retry_after, commands.BucketType.user)
        return True

def apply_cooldown():
    """
    Decorator that applies the custom cooldown.
    Usage: @apply_cooldown()
    """
    # For py-cord application commands, checks are different.
    # We can use commands.check(predicate)
    return commands.check(CustomCooldown())
