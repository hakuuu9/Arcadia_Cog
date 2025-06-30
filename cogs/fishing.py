import discord
from discord.ext import commands
from discord import app_commands
import random
from pymongo import MongoClient
from config import MONGO_URL
import time

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users
        self.emoji = "<:arcadiacoin:1378656679704395796>"

        self.fish_emojis = [
            "<a:fish1:1389044413002547245>",
            "<a:fish2:1389044609115623556>",
            "<:fish3:1389044625129345064>",
            "<a:fish4:1389044639667064926>",
            "<a:fish5:1389044652581326888>",
        ]

        self.fish_types = {
            "Common Fish": (10, 0),
            "Salmon": (20, 1),
            "Golden Trout": (50, 2),
            "Legendary Dragonfish": (100, 3),
            "Old Boot": (0, 4),
            "Nothing": (0, None),
        }

        self.cooldowns = {}  # Store user_id: last_fish_time

    async def fish(self, user):
        catch = random.choices(
            population=list(self.fish_types.keys()),
            weights=[30, 20, 15, 5, 10, 20],
            k=1
        )[0]

        coins_earned, emoji_index = self.fish_types[catch]
        fish_emoji = self.fish_emojis[emoji_index] if emoji_index is not None else ""

        if coins_earned > 0:
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': coins_earned}}, upsert=True)
            message = f"🎣 You caught a **{fish_emoji} {catch}** and earned ₱{coins_earned:,} {self.emoji}!"
        elif catch == "Old Boot":
            message = f"🎣 You caught an **{fish_emoji} Old Boot**. Better luck next time!"
        else:
            message = "🎣 You didn't catch anything this time. Try again!"

        return message

    def check_cooldown(self, user_id):
        now = time.time()
        last_time = self.cooldowns.get(user_id, 0)
        if now - last_time < 60:
            return 60 - (now - last_time)
        self.cooldowns[user_id] = now
        return 0

    @commands.command(name="fishing")
    async def fishing_text(self, ctx):
        remaining = self.check_cooldown(ctx.author.id)
        if remaining > 0:
            await ctx.send(f"⏳ Please wait {int(remaining)} seconds before fishing again.")
            return

        message = await self.fish(ctx.author)
        await ctx.send(message)

    @app_commands.command(name="fishing", description="Go fishing and catch some coins!")
    async def fishing_slash(self, interaction: discord.Interaction):
        remaining = self.check_cooldown(interaction.user.id)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Please wait {int(remaining)} seconds before fishing again.", ephemeral=True)
            return

        await interaction.response.defer()
        message = await self.fish(interaction.user)
        await interaction.followup.send(message)

async def setup(bot):
    await bot.add_cog(Fishing(bot))
