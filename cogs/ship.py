import discord
from discord.ext import commands
from discord import app_commands
import random
import requests
import asyncio

class Ship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.couple_nicknames = [
            "Peanut Butter & Jelly",
            "Tom & Jerry",
            "Romeo & Juliet",
            "BTS & Army",
            "Salt & Pepper",
            "Sun & Moon",
            "Coffee & Donut",
            "Mario & Luigi",
            "Batman & Robin",
            "Pineapple & Pizza"
        ]

        self.plot_twists = [
            "Oops! Looks like it's just friendship! 😅",
            "Plot twist: They're actually long lost siblings! 😱",
            "Well... better luck next time! 💔",
            "Destiny says NOPE! 😂",
            "Surprise! They both like pineapple on pizza — scandal! 🍍🍕",
            "Their love story got lost in the Wi-Fi connection. 📶",
            "They’re perfect... for avoiding each other. 🙃",
            "Turns out, they both can't cook. Disaster in the kitchen! 🍳🔥",
            "They matched... but only on their dislike for Mondays. 😴",
            "Plot twist: They both secretly love the same terrible TV show. 📺🤫",
            "Love? Nah. They bonded over hating the same person. 🤐",
            "Turns out, their love language is just memes. Lots and lots of memes. 😂",
            "Their relationship status? 'Complicated.' Mostly because of their Wi-Fi. 📡",
            "Plot twist: One of them is actually a cat in disguise. 🐱‍👤",
            "Turns out, they only liked each other’s food pics. 🍔📸",
        ]

    def get_couple_nickname(self):
        return random.choice(self.couple_nicknames)

    def get_plot_twist(self):
        return random.choice(self.plot_twists)

    async def get_romantic_quote(self):
        url = "https://api.quotable.io/random?tags=love,romance"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return f'"{data["content"]}" — {data["author"]}'
        except Exception:
            # Fallback romantic lines if API fails
            fallback = [
                "Love is composed of a single soul inhabiting two bodies. — Aristotle",
                "You don’t love someone for their looks, or their clothes, or for their fancy car, but because they sing a song only you can hear. — Oscar Wilde",
                "To love and be loved is to feel the sun from both sides. — David Viscott"
            ]
            return random.choice(fallback)

    @commands.command(name="ship")
    async def ship_text(self, ctx, user1: discord.User, user2: discord.User):
        percent = random.randint(0, 100)

        if percent >= 50:
            nickname = self.get_couple_nickname()
            romantic_quote = await self.get_romantic_quote()
            description = (
                f"❤️ Compatibility: {percent}%\n"
                f"Couple Nickname: **{nickname}** 💕\n\n"
                f"💬 Romantic Quote:\n{romantic_quote}"
            )
            color = discord.Color.red()
        else:
            twist = self.get_plot_twist()
            description = f"💔 Compatibility: {percent}%\nPlot Twist: {twist}"
            color = discord.Color.dark_gray()

        embed = discord.Embed(
            title=f"💞 Shipping {user1.display_name} and {user2.display_name}",
            description=description,
            color=color
        )
        embed.set_thumbnail(url=user1.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)

    @app_commands.command(name="ship", description="Ship two users with a plot twist")
    @app_commands.describe(user1="First user", user2="Second user")
    async def ship_slash(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User):
        percent = random.randint(0, 100)

        if percent >= 50:
            nickname = self.get_couple_nickname()
            romantic_quote = await self.get_romantic_quote()
            description = (
                f"❤️ Compatibility: {percent}%\n"
                f"Couple Nickname: **{nickname}** 💕\n\n"
                f"💬 Romantic Quote:\n{romantic_quote}"
            )
            color = discord.Color.red()
        else:
            twist = self.get_plot_twist()
            description = f"💔 Compatibility: {percent}%\nPlot Twist: {twist}"
            color = discord.Color.dark_gray()

        embed = discord.Embed(
            title=f"💞 Shipping {user1.display_name} and {user2.display_name}",
            description=description,
            color=color
        )
        embed.set_thumbnail(url=user1.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ship(bot))
