import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from random import randint, choice
from config import MONGO_URL

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        self.cooldowns = {}  # user_id: datetime of last work

    @app_commands.command(name="work", description="Work to earn money.")
    async def work(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.utcnow()

        cooldown_time = timedelta(seconds=15)  # 15 seconds cooldown
        last_work_time = self.cooldowns.get(user_id)

        if last_work_time and now - last_work_time < cooldown_time:
            remaining = cooldown_time - (now - last_work_time)
            seconds = int(remaining.total_seconds()) + 1
            return await interaction.response.send_message(
                f"⏳ You are still tired! Try again in {seconds} second(s).", ephemeral=True
            )

        user_data = self.db.find_one({"_id": user_id}) or {}
        balance = int(user_data.get("balance", 0))

        salary = randint(1, 500)
        new_balance = balance + salary

        work_phrases = user_data.get("work_phrases", [])

        if not work_phrases:
            phrase = "You worked hard and earned {salary}!"
            creator_name = interaction.user.display_name
        else:
            entry = choice(work_phrases)
            phrase = entry.get("phrase", "")
            creator_name = entry.get("creator_name", interaction.user.display_name)

            if "{salary}" not in phrase:
                return await interaction.response.send_message(
                    "❌ Your work phrase must include `{salary}` to show your earnings!\n"
                    "Example usage:\n"
                    "`You work hard and earn {salary}!`\n"
                    "Please update your phrase accordingly.",
                    ephemeral=True
                )

        formatted_msg = phrase.replace("{salary}", f"₱{salary:,}")

        self.db.update_one({"_id": user_id}, {"$set": {"balance": new_balance}}, upsert=True)
        self.cooldowns[user_id] = now

        await interaction.response.send_message(
            f"{formatted_msg}\n\n- {creator_name}"
        )

    def cog_unload(self):
        self.client.close()
        print("Work MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Work(bot))
