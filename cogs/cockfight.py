import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL

CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
WIN_EMOJI = "<:losecf:1378659630837665874>"
LOSE_EMOJI = "<:wincf:1378659531546165301>"
FIGHT_EMOJI = "⚔️"

class Cockfight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    # Slash Command
    @app_commands.command(name="cockfight", description="Bet an amount of ₱ on a cockfight!")
    @app_commands.describe(bet_amount="The amount of ₱ to bet.")
    async def cockfight_slash(self, interaction: discord.Interaction, bet_amount: int):
        await self.start_cockfight(interaction, bet_amount, interaction_type="slash")

    # Manual Text Command
    @commands.command(name="cockfight")
    async def cockfight_text(self, ctx, bet_amount: str = None):
        if bet_amount is None:
            return await ctx.send("❌ Usage: `$cockfight <amount>` — Example: `$cockfight 500`")

        if not bet_amount.isdigit():
            return await ctx.send("❌ The amount must be a **positive number**. Example: `$cockfight 500`")

        bet_amount = int(bet_amount)
        interaction = ctx  # Simulate interaction context
        await self.start_cockfight(interaction, bet_amount, interaction_type="text")

    async def start_cockfight(self, interaction, bet_amount: int, interaction_type="slash"):
        user_id = str(interaction.user.id)
        is_slash = interaction_type == "slash"

        if is_slash:
            await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0

        if bet_amount <= 0:
            return await self.send_message(interaction, "❌ You must bet a positive amount.", is_slash)

        if current_balance < bet_amount:
            return await self.send_message(
                interaction,
                f"❌ You don't have enough money! You have ₱{current_balance:,} but tried to bet ₱{bet_amount:,}.",
                is_slash
            )

        if chickens_owned <= 0:
            return await self.send_message(
                interaction,
                f"❌ You need at least one {CHICKEN_EMOJI} Chicken to participate in a cockfight! Buy one from `/shop`.",
                is_slash
            )

        await self.send_message(
            interaction,
            f"{interaction.user.mention}'s {CHICKEN_EMOJI} Chicken enters the arena, betting ₱{bet_amount:,}! {FIGHT_EMOJI}\n"
            f"The fight is on... (Result in 3 seconds)",
            is_slash
        )

        await asyncio.sleep(3)

        is_win = random.choice([True, False])

        if is_win:
            amount_change_balance = bet_amount
            new_balance = current_balance + bet_amount
            new_chickens_owned = chickens_owned

            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": amount_change_balance}},
                upsert=True
            )

            await self.send_message(
                interaction,
                f"🎉 {interaction.user.mention}'s {CHICKEN_EMOJI} Chicken fought bravely and WON ₱{bet_amount:,}!\n"
                f"{WIN_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You still have {new_chickens_owned} {CHICKEN_EMOJI} Chicken(s).",
                is_slash
            )
        else:
            amount_change_balance = -bet_amount
            amount_change_chickens = -1
            new_balance = current_balance + amount_change_balance
            new_chickens_owned = chickens_owned - 1

            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": amount_change_balance, "chickens_owned": amount_change_chickens}},
                upsert=True
            )

            await self.send_message(
                interaction,
                f"💔 {interaction.user.mention}'s {CHICKEN_EMOJI} Chicken put up a good fight but sadly LOST ₱{bet_amount:,} and one of its own!\n"
                f"{LOSE_EMOJI} Your new balance is ₱{new_balance:,}.\n"
                f"You now have {new_chickens_owned} {CHICKEN_EMOJI} Chicken(s) left.",
                is_slash
            )

    async def send_message(self, interaction, content, is_slash):
        if is_slash:
            await interaction.followup.send(content)
        else:
            await interaction.send(content)

    def cog_unload(self):
        self.client.close()
        print("Cockfight MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Cockfight(bot))
