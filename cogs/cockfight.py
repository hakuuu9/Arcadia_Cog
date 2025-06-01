import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Assuming config.py is in the same directory

CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
WIN_EMOJI = "<:losecf:1378659630837665874>"
LOSE_EMOJI = "<:wincf:1378659531546165301>"
FIGHT_EMOJI = "⚔️"

class Cockfight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def run_cockfight(self, ctx_or_interaction, bet_amount: int, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        # Defer for slash commands
        if is_slash:
            await ctx_or_interaction.response.defer()

        # Fetch user data
        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0

        # Input validation
        if bet_amount <= 0:
            msg = "❌ You must bet a positive amount."
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        if chickens_owned <= 0:
            msg = (
                f"❌ You don’t have any {CHICKEN_EMOJI} Chickens!\n"
                f"Please use `/shop` then `/buy chicken` to get one."
            )
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        if current_balance < bet_amount:
            msg = (
                f"❌ You don't have enough money! You have ₱{current_balance:,} "
                f"but tried to bet ₱{bet_amount:,}."
            )
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        # Fight intro
        await self._send(ctx_or_interaction,
            f"{user.mention}'s {CHICKEN_EMOJI} Chicken enters the arena, betting ₱{bet_amount:,}! {FIGHT_EMOJI}\n"
            f"The fight is on... (Result in 3 seconds)",
            is_slash)

        await asyncio.sleep(3)
        is_win = random.choice([True, False])

        if is_win:
            new_balance = current_balance + bet_amount
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": bet_amount}}, upsert=True)
            msg = (
                f"🎉 {user.mention}'s {CHICKEN_EMOJI} Chicken fought bravely and WON ₱{bet_amount:,}!\n"
                f"{WIN_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You still have {chickens_owned} {CHICKEN_EMOJI} Chicken(s)."
            )
        else:
            new_balance = current_balance - bet_amount
            new_chickens = chickens_owned - 1
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -bet_amount, "chickens_owned": -1}},
                upsert=True
            )
            msg = (
                f"💔 {user.mention}'s {CHICKEN_EMOJI} Chicken lost ₱{bet_amount:,} and one of its own!\n"
                f"{LOSE_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You now have {new_chickens} {CHICKEN_EMOJI} Chicken(s) left."
            )

        await self._send(ctx_or_interaction, msg, is_slash)

    async def _send(self, ctx_or_interaction, message: str, is_slash: bool, ephemeral: bool = False):
        if is_slash:
            await ctx_or_interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.send(message)

    @commands.command(name="cockfight")
    async def cockfight_text(self, ctx, bet_amount: str = None):
        if not bet_amount or not bet_amount.isdigit() or int(bet_amount) <= 0:
            return await ctx.send("❌ Correct usage: `$cockfight <bet_amount>` (e.g. `$cockfight 500`)")
        await self.run_cockfight(ctx, int(bet_amount), is_slash=False)

    @app_commands.command(name="cockfight", description="Bet an amount of ₱ on a cockfight!")
    @app_commands.describe(bet_amount="The amount of ₱ to bet.")
    async def cockfight_slash(self, interaction: discord.Interaction, bet_amount: int):
        await self.run_cockfight(interaction, bet_amount, is_slash=True)

    def cog_unload(self):
        self.client.close()
        print("Cockfight MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Cockfight(bot))
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Assuming config.py is in the same directory

CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
WIN_EMOJI = "<:losecf:1378659630837665874>"
LOSE_EMOJI = "<:wincf:1378659531546165301>"
FIGHT_EMOJI = "⚔️"

class Cockfight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def run_cockfight(self, ctx_or_interaction, bet_amount: int, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        # Defer for slash commands
        if is_slash:
            await ctx_or_interaction.response.defer()

        # Fetch user data
        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0

        # Input validation
        if bet_amount <= 0:
            msg = "❌ You must bet a positive amount."
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        if chickens_owned <= 0:
            msg = (
                f"❌ You don’t have any {CHICKEN_EMOJI} Chickens!\n"
                f"Please use `/shop` then `/buy chicken` to get one."
            )
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        if current_balance < bet_amount:
            msg = (
                f"❌ You don't have enough money! You have ₱{current_balance:,} "
                f"but tried to bet ₱{bet_amount:,}."
            )
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        # Fight intro
        await self._send(ctx_or_interaction,
            f"{user.mention}'s {CHICKEN_EMOJI} Chicken enters the arena, betting ₱{bet_amount:,}! {FIGHT_EMOJI}\n"
            f"The fight is on... (Result in 3 seconds)",
            is_slash)

        await asyncio.sleep(3)
        is_win = random.choice([True, False])

        if is_win:
            new_balance = current_balance + bet_amount
            self.db.update_one({"_id": user_id}, {"$inc": {"balance": bet_amount}}, upsert=True)
            msg = (
                f"🎉 {user.mention}'s {CHICKEN_EMOJI} Chicken fought bravely and WON ₱{bet_amount:,}!\n"
                f"{WIN_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You still have {chickens_owned} {CHICKEN_EMOJI} Chicken(s)."
            )
        else:
            new_balance = current_balance - bet_amount
            new_chickens = chickens_owned - 1
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -bet_amount, "chickens_owned": -1}},
                upsert=True
            )
            msg = (
                f"💔 {user.mention}'s {CHICKEN_EMOJI} Chicken lost ₱{bet_amount:,} and one of its own!\n"
                f"{LOSE_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You now have {new_chickens} {CHICKEN_EMOJI} Chicken(s) left."
            )

        await self._send(ctx_or_interaction, msg, is_slash)

    async def _send(self, ctx_or_interaction, message: str, is_slash: bool, ephemeral: bool = False):
        if is_slash:
            await ctx_or_interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.send(message)

    @commands.command(name="cockfight")
    async def cockfight_text(self, ctx, bet_amount: str = None):
        if not bet_amount or not bet_amount.isdigit() or int(bet_amount) <= 0:
            return await ctx.send("❌ Correct usage: `$cockfight <bet_amount>` (e.g. `$cockfight 500`)")
        await self.run_cockfight(ctx, int(bet_amount), is_slash=False)

    @app_commands.command(name="cockfight", description="Bet an amount of ₱ on a cockfight!")
    @app_commands.describe(bet_amount="The amount of ₱ to bet.")
    async def cockfight_slash(self, interaction: discord.Interaction, bet_amount: int):
        await self.run_cockfight(interaction, bet_amount, is_slash=True)

    def cog_unload(self):
        self.client.close()
        print("Cockfight MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Cockfight(bot))
