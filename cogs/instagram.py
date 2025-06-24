import discord
from discord.ext import commands
from discord import app_commands
import requests

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="instagram")
    async def instagram_text(self, ctx, username: str):
        await self.send_profile(ctx, username)

    @app_commands.command(name="instagram", description="Stalk a public Instagram profile")
    @app_commands.describe(username="Instagram username (without @)")
    async def instagram_slash(self, interaction: discord.Interaction, username: str):
        await self.send_profile(interaction, username)

    async def send_profile(self, ctx_or_interaction, username: str):
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer()

        url = f"https://instagram120.p.rapidapi.com/api/instagram/hls?user={username}"
        headers = {
            "x-rapidapi-host": "instagram120.p.rapidapi.com",
            "x-rapidapi-key": "67c341f875msh6ddbc8d8e2d3dc6p183b1fjsncb663d7a8ce8"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            data = response.json()
            user = data.get("data", {})

            if not user:
                raise Exception("No profile data returned.")

            embed = discord.Embed(
                title=f"📸 @{username}",
                url=f"https://instagram.com/{username}",
                description=user.get("biography", "*No bio available.*"),
                color=discord.Color.default()  # Closest to black (Discord has no true black)
            )
            embed.set_thumbnail(url=user.get("profile_pic_url"))
            embed.add_field(name="👤 Name", value=user.get("full_name", "—"), inline=True)
            embed.add_field(name="📌 Posts", value=f"{int(user.get('edge_owner_to_timeline_media', {}).get('count', 0)):,}", inline=True)
            embed.add_field(name="👥 Followers", value=f"{int(user.get('edge_followed_by', {}).get('count', 0)):,}", inline=True)
            embed.add_field(name="🔁 Following", value=f"{int(user.get('edge_follow', {}).get('count', 0)):,}", inline=True)
            embed.set_footer(text=f"Requested by {(ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author)}")

            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(embed=embed)
            else:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(embed=embed)
                else:
                    await ctx_or_interaction.response.send_message(embed=embed)

        except Exception as e:
            msg = f"❌ Failed to fetch @{username}: {e}"
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(msg)
            else:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(msg)
                else:
                    await ctx_or_interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Instagram(bot))
