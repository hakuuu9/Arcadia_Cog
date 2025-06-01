import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Assuming config.py is in the same directory

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def handle_coinflip(self, ctx, choice: str, amount: int, is_slash=False):
        choice = choice.lower()
        if choice not in ["head", "tail"]:
            msg = "❌ Choose either `head` or `tail`."
            if is_slash:
                return await ctx.response.send_message(msg, ephemeral=True)
            else:
                return await ctx.send(msg)

        user_id = str(ctx.user.id if is_slash else ctx.author.id)

        if is_slash:
            await ctx.response.defer()
        else:
            await ctx.channel.typing()

        user_data = self.db.find_one({"_id": user_id})
        balance = int(user_data.get("balance", 0)) if user_data else 0

        if amount <= 0:
            msg = "❌ Bet amount must be greater than ₱0."
            if is_slash:
                return await ctx.followup.send(msg, ephemeral=True)
            else:
                return await ctx.send(msg)

        if balance < amount:
            msg = f"❌ You only have ₱{balance}."
            if is_slash:
                return await ctx.followup.send(msg, ephemeral=True)
            else:
                return await ctx.send(msg)

        flip_msg = f"You chose **{choice.capitalize()}** <a:flipcoin:1378662039966453880>\nFlipping the coin..."
        if is_slash:
            await ctx.followup.send(flip_msg)
        else:
            await ctx.send(flip_msg)

        await asyncio.sleep(2)

        result = random.choice(["head", "tail"])
        result_emoji = "<:headcoin:1378662273836384256>" if result == "head" else "<:tailcoin:1378662544054554726>"
        win_emoji = "<:wincf:1378659531546165301>"
        lose_emoji = "<:losecf:1378659630837665874>"

        if choice == result:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)
            new_balance = balance + amount
            result_msg = (
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{win_emoji} You won ₱{amount}!\n"
                f"Your new balance is ₱{new_balance}."
            )
        else:
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": -amount}}, upsert=True)
            new_balance = balance - amount
            result_msg = (
                f"The coin landed on **{result}** {result_emoji}\n"
                f"{lose_emoji} You lost ₱{amount}.\n"
                f"Your new balance is ₱{new_balance}."
            )

        if is_slash:
            await ctx.followup.send(result_msg)
        else:
            await ctx.send(result_msg)

    @app_commands.command(name="coinflip", description="Flip a coin and bet your ₱")
    @app_commands.describe(choice="Choose head or tail", amount="Amount to bet")
    async def coinflip_slash(self, interaction: discord.Interaction, choice: str, amount: int):
        await self.handle_coinflip(interaction, choice, amount, is_slash=True)

    @commands.command(name="coinflip")
    async def coinflip_prefix(self, ctx, choice: str, amount: int):
        await self.handle_coinflip(ctx, choice, amount, is_slash=False)

    def cog_unload(self):
        self.client.close()
        print("CoinFlip MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(CoinFlip(bot))
