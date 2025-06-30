import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL

class HighLow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users
        self.emoji = "<:arcadiacoin:1378656679704395796>"

    async def play_highlow(self, user, amount, guess):
        user_data = self.db.find_one({'_id': str(user.id)})
        balance = user_data['balance'] if user_data and 'balance' in user_data else 0

        guess = guess.lower()
        if guess not in ["high", "low"]:
            return None, "❌ Your guess must be 'high' or 'low'."

        if amount <= 0:
            return None, "❌ Bet must be more than 0."
        if balance < amount:
            return None, f"❌ Not enough coins! Your balance is ₱{balance:,} {self.emoji}"

        self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': -amount}}, upsert=True)

        number = random.randint(1, 10)
        win = (guess == "high" and number >= 6) or (guess == "low" and number <= 5)

        if win:
            winnings = amount * 2
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': winnings}}, upsert=True)
            message = f"🎉 You guessed **{guess.upper()}** and the number was {number}. You won ₱{winnings:,} {self.emoji}!"
        else:
            message = f"💔 You guessed **{guess.upper()}** but the number was {number}. You lost ₱{amount:,} {self.emoji}."

        return number, message

    def animated_display(self, number):
        stages = [
            "`[ ? ]`",
            f"`[ {number} ]`",
        ]
        return stages

    # Prefix command with error handling
    @commands.command(name="highlow")
    async def highlow_text(self, ctx, amount: int = None, guess: str = None):
        if amount is None or guess is None:
            return await ctx.send("❌ Usage: `$highlow <amount> <high|low>`\nExample: `$highlow 100 high`")

        number, outcome = await self.play_highlow(ctx.author, amount, guess)
        if number is None:
            return await ctx.send(outcome)

        stages = self.animated_display(number)
        msg = await ctx.send("🎲 Rolling...\n" + stages[0])
        await asyncio.sleep(1)
        await msg.edit(content="🎲 Rolling...\n" + stages[1])
        await asyncio.sleep(0.5)
        await msg.edit(content=outcome)

    # Slash command remains unchanged
    @app_commands.command(name="highlow", description="Play highlow and win coins!")
    @app_commands.describe(amount="The amount you want to bet")
    @app_commands.choices(guess=[
        app_commands.Choice(name="high", value="high"),
        app_commands.Choice(name="low", value="low"),
    ])
    async def highlow_slash(self, interaction: discord.Interaction, amount: int, guess: app_commands.Choice[str]):
        await interaction.response.defer()
        number, outcome = await self.play_highlow(interaction.user, amount, guess.value)
        if number is None:
            return await interaction.followup.send(outcome, ephemeral=True)

        stages = self.animated_display(number)
        msg = await interaction.followup.send("🎲 Rolling...\n" + stages[0])
        await asyncio.sleep(1)
        await msg.edit(content="🎲 Rolling...\n" + stages[1])
        await asyncio.sleep(0.5)
        await msg.edit(content=outcome)

async def setup(bot):
    await bot.add_cog(HighLow(bot))
