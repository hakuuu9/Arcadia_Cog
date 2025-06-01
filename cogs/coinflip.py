import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Your MongoDB URI

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users  # Adjust your DB/collection

    @app_commands.command(name="coinflip", description="Flip a coin and bet your ₱")
    @app_commands.describe(choice="Choose head or tail", amount="Amount to bet")
    async def coinflip(self, interaction: discord.Interaction, choice: str, amount: int):
        choice = choice.lower()
        if choice not in ["head", "tail"]:
            return await interaction.response.send_message("❌ Choose either `head` or `tail`.", ephemeral=True)

        user_id = str(interaction.user.id)

        await interaction.response.defer()

        user_data = self.db.find_one({"_id": user_id})
        balance = int(user_data.get("balance", 0)) if user_data else 0

        if amount <= 0:
            return await interaction.followup.send("❌ Bet amount must be greater than ₱0.", ephemeral=True)

        if balance < amount:
            return await interaction.followup.send(f"❌ You only have ₱{balance}.", ephemeral=True)

        await interaction.followup.send(f"You chose **{choice.capitalize()}** <a:flipcoin:1378662039966453880>\nFlipping the coin...")

        await asyncio.sleep(2)

        result = random.choice(["head", "tail"])
        result_emoji = "<:headcoin:1378662273836384256>" if result == "head" else "<:tailcoin:1378662544054554726>"
        win_emoji = "<:wincf:1378659531546165301>"
        lose_emoji = "<:losecf:1378659630837665874>"

        if choice == result:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)
            new_balance = balance + amount
            await interaction.followup.send(
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{win_emoji} You won ₱{amount}!\n"
                f"Your new balance is ₱{new_balance}."
            )
        else:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            new_balance = balance - amount
            await interaction.followup.send(
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{lose_emoji} You lost ₱{amount}.\n"
                f"Your new balance is ₱{new_balance}."
            )

    # Prefix version: $coinflip
    @commands.command(name="coinflip")
    async def coinflip_prefix(self, ctx, choice: str = None, amount: str = None):
        if not choice or not amount:
            return await ctx.send("❌ Usage: `$coinflip <head/tail> <amount>`\nExample: `$coinflip head 100`")

        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send("❌ Please enter a valid number for the amount.")

        await self.handle_coinflip(ctx, choice, amount, is_slash=False)

    # Shared logic for both slash and prefix commands
    async def handle_coinflip(self, ctx_or_interaction, choice: str, amount: int, is_slash: bool):
        choice = choice.lower()
        if choice not in ["head", "tail"]:
            msg = "❌ Choose either `head` or `tail`."
            return await (ctx_or_interaction.send(msg) if not is_slash else ctx_or_interaction.response.send_message(msg, ephemeral=True))

        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        user_data = self.db.find_one({"_id": user_id})
        balance = int(user_data.get("balance", 0)) if user_data else 0

        if amount <= 0:
            msg = "❌ Bet amount must be greater than ₱0."
            return await (ctx_or_interaction.send(msg) if not is_slash else ctx_or_interaction.response.send_message(msg, ephemeral=True))

        if balance < amount:
            msg = f"❌ You only have ₱{balance}."
            return await (ctx_or_interaction.send(msg) if not is_slash else ctx_or_interaction.response.send_message(msg, ephemeral=True))

        send = ctx_or_interaction.send if not is_slash else ctx_or_interaction.followup.send
        await send(f"You chose **{choice.capitalize()}** <a:flipcoin:1378662039966453880>\nFlipping the coin...")

        await asyncio.sleep(2)

        result = random.choice(["head", "tail"])
        result_emoji = "<:headcoin:1378662273836384256>" if result == "head" else "<:tailcoin:1378662544054554726>"
        win_emoji = "<:wincf:1378659531546165301>"
        lose_emoji = "<:losecf:1378659630837665874>"

        if choice == result:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)
            new_balance = balance + amount
            await send(
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{win_emoji} You won ₱{amount}!\n"
                f"Your new balance is ₱{new_balance}."
            )
        else:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            new_balance = balance - amount
            await send(
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{lose_emoji} You lost ₱{amount}.\n"
                f"Your new balance is ₱{new_balance}."
            )

    def cog_unload(self):
        self.client.close()
        print("CoinFlip MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(CoinFlip(bot))
