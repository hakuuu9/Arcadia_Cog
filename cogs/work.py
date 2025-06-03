import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL
import random

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users  # Collection for user balances

        self.emoji = "<:arcadiacoin:1378656679704395796>"
        self.messages = [
            # Informal Tagalog
            "Totoy, nagbanat ng buto pero ang sweldo ₱{salary} {emoji} para na rin sa mga pang hugas ng luha mo.\n\n"
            "Bagong balance mo: ₱{balance} {emoji}\nLaban lang, kapit lang, pre!",

            "Grabe ang sipag mo, pre! ₱{salary} {emoji} ang pasalubong mo ngayon.\n"
            "Balance mo ay ₱{balance} {emoji} na!",

            "Ayos 'to, ₱{salary} {emoji} ang pasok mo! Keep it up, kapatid.\n"
            "Ngayon ₱{balance} {emoji} na ang pera mo.",

            # Casual English
            "You worked hard and earned ₱{salary} {emoji}!\n"
            "Your new balance is ₱{balance} {emoji}. Keep grinding!",

            "Nice hustle! ₱{salary} {emoji} added to your wallet.\n"
            "Total balance: ₱{balance} {emoji}. Don't stop now!",

            "Your effort paid off: ₱{salary} {emoji} earned.\n"
            "Balance now: ₱{balance} {emoji}. Keep up the good work!",

            # Formal English
            "Congratulations! You have received a salary of ₱{salary} {emoji}.\n"
            "Your updated balance is ₱{balance} {emoji}. Well done on your dedication.",

            "Your work has been compensated with ₱{salary} {emoji}.\n"
            "The current balance in your account is ₱{balance} {emoji}.\nKeep maintaining your excellence.",

            "You earned ₱{salary} {emoji} for your efforts today.\n"
            "Your new balance stands at ₱{balance} {emoji}.\nContinue your productive work."
        ]

        self.slash_cooldown = commands.CooldownMapping.from_cooldown(1, 300.0, commands.BucketType.user)

    @commands.command(name='work')
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown
    async def work_text(self, ctx):
        await self.handle_work(ctx.author, ctx)

    @app_commands.command(name='work', description='Work to earn a small salary (5m cooldown)')
    async def work_slash(self, interaction: discord.Interaction):
        bucket = self.slash_cooldown.get_bucket(interaction.user)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await interaction.response.send_message(
                f"You're tired! You can work again in {round(retry_after)} seconds. Take a break!",
                ephemeral=True
            )
            return
        await self.handle_work(interaction.user, interaction)

    async def handle_work(self, user, ctx_or_interaction):
        salary = random.randint(1, 200)

        user_data = self.db.find_one({'_id': str(user.id)})
        balance = user_data['balance'] if user_data and 'balance' in user_data else 0

        new_balance = balance + salary
        self.db.update_one({'_id': str(user.id)}, {'$set': {'balance': new_balance}}, upsert=True)

        message_template = random.choice(self.messages)
        message = message_template.format(salary=salary, balance=new_balance, emoji=self.emoji)

        await self.send_response(ctx_or_interaction, message)

    async def send_response(self, ctx_or_interaction, message):
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(message)
        else:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(message)
            else:
                await ctx_or_interaction.response.send_message(message)

    @work_text.error
    async def work_cooldown_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            seconds = round(error.retry_after)
            await ctx.send(f"You're tired! You can work again in {seconds} seconds. Take a break!")

async def setup(bot):
    await bot.add_cog(Work(bot))