import discord
from discord.ext import commands
from discord import app_commands
import requests

API_HOST = "instagram-data1.p.rapidapi.com"  # or the specific host name from InstaAPI
API_KEY = "67c341f875msh6ddbc8d8e2d3dc6p183b1fjsncb663d7a8ce8"

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="instagram")
    async def instagram_text(self, ctx, username: str):
        await self.send_profile(ctx, username)

    @app_commands.command(name="instagram", description="View public Instagram profile info")
    @app_commands.describe(username="Instagram username (without @)")
    async def instagram_slash(self, interaction: discord.Interaction, username: str):
        await self.send_profile(interaction, username)

    async def send_profile(self, ctx_or_interaction, username: str):
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer()

        url = f"https://{API_HOST}/user/profile/{username}"
        headers = {
            "X-RapidAPI-Host": API_HOST,
            "X-RapidAPI-Key": API_KEY
        }

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            msg = f"❌ Could not fetch @{username}: HTTP {resp.status_code}"
            await self._send_message(ctx_or_interaction, msg)
            return

        data = resp.json()
        if not data.get("success"):
            msg = f"❌ Failed to fetch @{username}: {data.get('message','Unknown error')}"
            await self._send_message(ctx_or_interaction, msg)
            return

        user = data["data"]
        embed = discord.Embed(
            title=f"@{username} on Instagram",
            url=f"https://instagram.com/{username}",
            description=user.get("biography", ""),
            color=discord.Color.dark_purple()
        )
        embed.set_thumbnail(url=user.get("profile_pic_url"))
        embed.add_field(name="Name", value=user.get("full_name","—"), inline=True)
        embed.add_field(name="Followers", value=f"{user.get('follower_count',0):,}", inline=True)
        embed.add_field(name="Following", value=f"{user.get('following_count',0):,}", inline=True)
        embed.add_field(name="Posts", value=f"{user.get('posts',0):,}", inline=True)
        embed.set_footer(text=f"Requested by {(ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author)}")

        await self._send_embed(ctx_or_interaction, embed)

    async def _send_message(self, ctx_or_interaction, message: str):
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(message)
        else:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(message)
            else:
                await ctx_or_interaction.response.send_message(message)

    async def _send_embed(self, ctx_or_interaction, embed: discord.Embed):
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Instagram(bot))
