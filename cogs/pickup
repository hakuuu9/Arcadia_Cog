import discord
from discord.ext import commands
from discord import app_commands
import requests
import random
import asyncio

class Pickup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Local fallback lines for variety
    local_funny_lines = [
        "Are you French? Because Eiffel for you.",
        "Do you have a map? I keep getting lost in your eyes.",
        "Is your name Wi-Fi? Because I'm feeling a connection.",
        "Are you a magician? Because whenever I look at you, everyone else disappears.",
    ]

    local_sweet_lines = [
        "Do you believe in love at first sight—or should I walk by again?",
        "If you were a vegetable, you’d be a cute-cumber.",
        "Are you made of copper and tellurium? Because you’re Cu-Te.",
        "You must be tired because you’ve been running through my mind all day.",
    ]

    @commands.command(name="pickup")
    async def pickup_text(self, ctx):
        thinking = await ctx.send("🤔 Let me think of a good pickup line...")
        line = await self.get_pickup_line()
        await asyncio.sleep(2)  # suspense!
        await thinking.edit(content=None, embed=self.make_embed(line, ctx.author))

    @app_commands.command(name="pickup", description="Send a random pickup line with a twist")
    async def pickup_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🤔 Let me think of a good pickup line...")
        line = await self.get_pickup_line()
        await asyncio.sleep(2)  # suspense!
        embed = self.make_embed(line, interaction.user)
        await interaction.edit_original_response(embed=embed)

    async def get_pickup_line(self):
        url = "https://jokeandpickupapi.herokuapp.com/pickup/random"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            line = data.get("pickupline")
            if not line:
                # fallback if no line from API
                return random.choice(self.local_sweet_lines + self.local_funny_lines)
            # randomly choose to keep API line or local line
            if random.choice([True, False]):
                return line
            else:
                return random.choice(self.local_sweet_lines + self.local_funny_lines)
        except Exception:
            # fallback on error
            return random.choice(self.local_sweet_lines + self.local_funny_lines)

    def make_embed(self, line, user):
        embed = discord.Embed(
            title="💘 Here's a pickup line for you!",
            description=line,
            color=discord.Color.magenta()
        )
        embed.set_footer(text=f"Requested by {user}")
        return embed

async def setup(bot):
    await bot.add_cog(Pickup(bot))
