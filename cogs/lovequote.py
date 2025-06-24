import discord
from discord.ext import commands
from discord import app_commands
import requests
import random
import asyncio

class LoveQuotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.local_love_quotes = [
            "Love is composed of a single soul inhabiting two bodies. — Aristotle",
            "You don’t love someone for their looks, or their clothes, or for their fancy car, but because they sing a song only you can hear. — Oscar Wilde",
            "To love and be loved is to feel the sun from both sides. — David Viscott",
            "Love is when the other person's happiness is more important than your own. — H. Jackson Brown Jr.",
            "Where there is love there is life. — Mahatma Gandhi",
            "Love recognizes no barriers. — Maya Angelou",
        ]

    async def fetch_love_quote(self):
        url = "https://api.quotable.io/random?tags=love,romance"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return f'"{data["content"]}" — {data["author"]}'
        except Exception:
            return random.choice(self.local_love_quotes)

    @commands.command(name="lovequote")
    async def lovequote_command(self, ctx):
        loading_msg = await ctx.send("💌 Searching for a beautiful love quote...")
        quote = await self.fetch_love_quote()
        await asyncio.sleep(2)
        embed = discord.Embed(
            title="💖 Love Quote",
            description=quote,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await loading_msg.edit(content=None, embed=embed)

    @app_commands.command(name="lovequote", description="Get a beautiful love quote")
    async def lovequote_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("💌 Searching for a beautiful love quote...")
        quote = await self.fetch_love_quote()
        await asyncio.sleep(2)
        embed = discord.Embed(
            title="💖 Love Quote",
            description=quote,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(LoveQuotes(bot))
