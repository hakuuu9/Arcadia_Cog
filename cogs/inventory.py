import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URL

CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
ANTI_ROB_EMOJI = "<:lock:1378669263325495416>"
CUSTOM_ROLE_EMOJI = "<:role:1378669470737891419>"
WORK_PHRASE_EMOJI = "📝"
CUSTOM_ROLE_CHANNEL_ID = 1357656511974871202  # Replace with your actual channel ID

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    @app_commands.command(name="inventory", description="View your owned items and protection status.")
    async def inventory(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = datetime.utcnow()
        await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id})
        balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0
        anti_rob_items_owned = int(user_data.get("anti_rob_items", 0)) if user_data else 0
        custom_role_items = int(user_data.get("custom_roles", 0)) if user_data else 0
        work_phrase_tokens = int(user_data.get("work_phrase_tokens", 0)) if user_data else 0
        anti_rob_expires_at = user_data.get("anti_rob_expires_at") if user_data else None

        # Anti-Rob status
        anti_rob_status = "Inactive"
        if anti_rob_expires_at and current_time < anti_rob_expires_at:
            remaining = anti_rob_expires_at - current_time
            days = remaining.days
            hours, rem = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            time_parts = []
            if days: time_parts.append(f"{days} day{'s' if days > 1
::contentReference[oaicite:0]{index=0}
 
