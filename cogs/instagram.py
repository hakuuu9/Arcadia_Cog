import discord
from discord.ext import commands
from discord import app_commands
import requests
import re

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="instagram")
    async def instagram_text(self, ctx, username: str):
        await self.send_profile(ctx, username)

    @app_commands.command(name="instagram", description="View basic Instagram profile info by username")
    @app_commands.describe(username="Instagram username (without @)")
    async def instagram_slash(self, interaction: discord.Interaction, username: str):
        await self.send_profile(interaction, username)

    async def send_profile(self, ctx_or_interaction, username: str):
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.defer()

        url = f"https://www.instagram.com/{username}/"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                raise Exception("Profile not found or private.")

            html = response.text

            name = re.search(r'"full_name":"(.*?)"', html)
            bio = re.search(r'"biography":"(.*?)"', html)
            followers = re.search(r'"edge_followed_by":{"count":(\d+)}', html)
            following = re.search(r'"edge_follow":{"count":(\d+)}', html)
            posts = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html)
            profile_pic = re.search(r'"profile_pic_url_hd":"(.*?)"', html)

            if not name:
                raise Exception("Could not parse profile info.")

            embed = discord.Embed(
                title=f"@{username} on Instagram",
                url=url,
                color=discord.Color.dark_purple(),
                description=bio.group(1).encode().decode('unicode_escape') if bio else ""
            )
            embed.set_thumbnail(url=profile_pic.group(1).replace("\\u0026", "&") if profile_pic else "")
            embed.add_field(name="Name", value=name.group(1), inline=True)
            embed.add_field(name="Followers", value=f"{int(followers.group(1)):,}" if followers else "N/A", inline=True)
            embed.add_field(name="Following", value=f"{int(following.group(1)):,}" if following else "N/A", inline=True)
            embed.add_field(name="Posts", value=f"{int(posts.group(1)):,}" if posts else "N/A", inline=True)
            embed.set_footer(text=f"Requested by {(ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author)}")

            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(embed=embed)
            else:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(embed=embed)
                else:
                    await ctx_or_interaction.response.send_message(embed=embed)

        except Exception as e:
            message = f"❌ Failed to fetch @{username}: {e}"
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(message)
            else:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(message)
                else:
                    await ctx_or_interaction.response.send_message(message)

async def setup(bot):
    await bot.add_cog(Instagram(bot))
