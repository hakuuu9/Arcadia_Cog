import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from pymongo import MongoClient
from config import MONGO_URL

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users
        self.emoji = "<:arcadiacoin:1378656679704395796>"
        self.symbols = ["🍒", "🍋", "💎", "🍀", "7️⃣"]
        self.payouts = {
            "🍒": 2,
            "🍋": 2,
            "💎": 5,
            "🍀": 3,
            "7️⃣": 10,
        }

    async def spin_slots(self, user, amount):
        user_data = self.db.find_one({'_id': str(user.id)})
        balance = user_data['balance'] if user_data and 'balance' in user_data else 0

        if amount <= 0:
            return None, "❌ Bet must be more than 0."
        if balance < amount:
            return None, f"❌ Not enough coins! Your balance is ₱{balance:,} {self.emoji}"

        # Deduct bet
        self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': -amount}}, upsert=True)

        # Spin results
        result = [random.choice(self.symbols) for _ in range(3)]

        # Determine win
        if result.count(result[0]) == 3:
            win_symbol = result[0]
            winnings = amount * self.payouts.get(win_symbol, 2)
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': winnings}}, upsert=True)
            message = f"🎉 **Jackpot!** You won ₱{winnings:,} {self.emoji}"
        elif result.count(result[0]) == 2 or result.count(result[1]) == 2:
            winnings = int(amount * 1.5)
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': winnings}}, upsert=True)
            message = f"✨ You got a pair! You won ₱{winnings:,} {self.emoji}"
        else:
            message = f"💔 You lost ₱{amount:,} {self.emoji}"

        return result, message

    def animated_display(self, result):
        stages = [
            "`[ ❔ ❔ ❔ ]`",
            f"`[ {result[0]} ❔ ❔ ]`",
            f"`[ {result[0]} {result[1]} ❔ ]`",
            f"`[ {result[0]} {result[1]} {result[2]} ]`",
        ]
        return stages

    # $slot command
    @commands.command(name="slot")
    async def slot_text(self, ctx, amount: int):
        result, outcome = await self.spin_slots(ctx.author, amount)
        if result is None:
            return await ctx.send(outcome)

        stages = self.animated_display(result)
        msg = await ctx.send("🎰 Rolling...\n" + stages[0])
        for stage in stages[1:]:
            await asyncio.sleep(0.5)
            await msg.edit(content="🎰 Rolling...\n" + stage)

        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 Final Result:\n{stages[-1]}\n\n{outcome}")

    # /slots command
    @app_commands.command(name="slots", description="Spin the slot machine and win coins!")
    @app_commands.describe(amount="The amount you want to bet")
    async def slot_slash(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer()
        result, outcome = await self.spin_slots(interaction.user, amount)
        if result is None:
            return await interaction.followup.send(outcome, ephemeral=True)

        stages = self.animated_display(result)
        msg = await interaction.followup.send("🎰 Rolling...\n" + stages[0])
        for stage in stages[1:]:
            await asyncio.sleep(0.5)
            await msg.edit(content="🎰 Rolling...\n" + stage)

        await asyncio.sleep(0.5)
        await msg.edit(content=f"🎰 Final Result:\n{stages[-1]}\n\n{outcome}")

async def setup(bot):
    await bot.add_cog(Slots(bot))
