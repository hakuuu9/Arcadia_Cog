import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL
import random

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    @app_commands.command(name="work", description="Earn money with your custom work phrase.")
    async def work(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user_data = self.db.find_one({"_id": user_id})

        if not user_data:
            return await interaction.response.send_message("❌ You don't have an account yet. Please start by earning some money first.", ephemeral=True)

        # Generate random salary between ₱100 and ₱500
        salary = random.randint(100, 500)
        new_balance = user_data.get("balance", 0) + salary

        # Retrieve custom work phrase
        work_phrase = user_data.get("custom_work_phrase", None)

        if not work_phrase:
            # Default work message
            message = (
                f"💼 You worked diligently and earned ₱{salary:,}!\n"
                f"💰 New balance: ₱{new_balance:,}.\n"
                f"Use `/buy work` to set your own custom work phrase!"
            )
        else:
            # Replace placeholders in custom work phrase
            message = work_phrase.replace("{salary}", f"₱{salary:,}").replace("{new_balance}", f"₱{new_balance:,}")

        # Update user's balance
        self.db.update_one({"_id": user_id}, {"$set": {"balance": new_balance}}, upsert=True)

        await interaction.response.send_message(message)

    def cog_unload(self):
        self.client.close()
        print("Work MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Work(bot))
