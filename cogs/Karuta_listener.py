import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL
import asyncio
from datetime import datetime, timedelta

class KarutaAutoReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.karuta_reminders
        self.active_cooldowns = {}  # {user_id: datetime}

    @app_commands.command(name="kdropremind", description="Toggle automatic reminders for your Karuta drops")
    async def toggle_reminder(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = self.db.find_one({"_id": user_id})

        if user_data:
            self.db.delete_one({"_id": user_id})
            await interaction.response.send_message("❌ Karuta drop reminders have been **disabled**.", ephemeral=True)
        else:
            self.db.insert_one({"_id": user_id})
            await interaction.response.send_message("✅ Karuta drop reminders have been **enabled**!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.lower().strip() != "k!drop":
            return

        user_id = str(message.author.id)

        if not self.db.find_one({"_id": user_id}):
            return

        now = datetime.utcnow()
        if user_id in self.active_cooldowns and now < self.active_cooldowns[user_id]:
            return

        self.active_cooldowns[user_id] = now + timedelta(minutes=30)

        await message.channel.send(
            f"⏳ Okay {message.author.mention}, I'll remind you in 30 minutes for your next Karuta drop!"
        )

        await asyncio.sleep(30 * 60)

        await message.channel.send(
            f"🎴 Hey {message.author.mention}, your **Karuta drop** is ready again! Use `k!drop` now!"
        )

async def setup(bot):
    await bot.add_cog(KarutaAutoReminder(bot))
