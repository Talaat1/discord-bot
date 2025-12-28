import os
import base64
import json

# Environment Variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CREDENTIALS_B64 = os.getenv("CREDENTIALS_B64")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", 0))
PORT = int(os.getenv("PORT", 8080))

# Constants
TIMEZONE_OFFSET = 3
ADMIN_ROLE_NAME = "Admin"
STREAK_CHANNEL_ID = None # Will be set/used in cogs, or logic if specific ID wasn't provided in prompt (prompt says "Only track messages in STREAK_CHANNEL_ID", implies it might be an env var or constant. Prompt didn't specify env var for it. I will assume it's a constant or look for it. The prompt mentions "STREAK_CHANNEL_ID" in the behavior list. I will better assume it's an int, or an env var. Let's make it an env var with a fallback or just a placeholder if not specified functionality-wise. Wait, the prompt lists STREAK_CHANNEL_ID in the STREAKS section. Only "DISCORD_BOT_TOKEN, CREDENTIALS_B64, BOT_OWNER_ID, PORT" are explicitly listed in "Keep environment variables exactly". So STREAK_CHANNEL_ID likely was hardcoded or is a new requirement. I'll add it as a constant to be safe, maybe 0 for now or os.getenv.)

# Let's assume STREAK_CHANNEL_ID is meant to be configured. Since the user said "Keep environment variables exactly... DISCORD_BOT_TOKEN...", I shouldn't add new ones if strictly forbidden, but STREAK_CHANNEL_ID allows the feature to work. I will add it as valid config, reading from env if possible, else 0.
STREAK_CHANNEL_ID = int(os.getenv("STREAK_CHANNEL_ID", 0))

# User Agent or other identifying info if needed
# (None strictly required by prompt)
