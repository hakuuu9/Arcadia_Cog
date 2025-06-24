import discord
from discord.ext import commands
from discord import app_commands
import requests
import re

class TikTokStalker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tiktokstalk")
    async def tiktokstalk_text(self, ctx, username: str):
        await self.send_profile(ctx, username)

    @app_commands.command(name="tiktokstalk", description="View basic TikTok profile info by username")
    @app_commands.describe(username="TikTok username (without @)")
    async def tiktokstalk_slash(self, interaction: discord.Interaction, username: str):
        await self.send_profile(interaction, username)

    async def send_profile(self, ctx_or_interaction, username: str):
        await (ctx_or_interaction.response.defer() if isinstance(ctx_or_interaction, discord.Interaction) else None)

        url = f"https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                raise Exception("Profile not found or blocked by TikTok.")

            html = response.text

            nickname = re.search(r'"nickname":"(.*?)"', html)
            followers = re.search(r'"followerCount":(\d+)', html)
            following = re.search(r'"followingCount":(\d+)', html)
            likes = re.search(r'"heartCount":(\d+)', html)
            avatar = re.search(r'"avatarLarger":"(.*?)"', html)

            if not nickname:
                raise Exception("Could not parse user data.")

            embed = discord.Embed(
                title=f"@{username} on TikTok",
                url=url,
                color=discord.Color.magenta()
            )
            embed.set_thumbnail(url=avatar.group(1).replace("\\u0026", "&") if avatar else "")
            embed.add_field(name="Nickname", value=nickname.group(1), inline=True)
            embed.add_field(name="Followers", value=f"{int(followers.group(1)):,}" if followers else "N/A", inline=True)
            embed.add_field(name="Following", value=f"{int(following.group(1)):,}" if following else "N/A", inline=True)
            embed.add_field(name="Likes", value=f"{int(likes.group(1)):,}" if likes else "N/A", inline=True)
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
    await bot.add_cog(TikTokStalker(bot))
