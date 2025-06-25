import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import config  # this imports your ZYLA_API_KEY

class FYP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fyp", description="Get a random TikTok video you can watch inside Discord!")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)  # 1 use per 15 seconds per user
    async def fyp_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()

        url = "https://zylalabs.com/api/2585/tiktok+video+roulette+api/2585/get+tiktok+video"
        headers = {
            "Authorization": f"Bearer {config.ZYLA_API_KEY}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Failed to fetch a TikTok. Try again later.")
                data = await resp.json()

        video = data.get("video")
        if not video or "id" not in video:
            return await interaction.followup.send("❌ No video found. Try again.")

        video_id = video["id"]
        username = video.get("author", {}).get("username", "tiktok")
        tiktok_url = f"https://www.tiktok.com/@{username}/video/{video_id}"

        embed = discord.Embed(
            title="Here's your TikTok video!",
            url=tiktok_url,
            color=discord.Colour.black()
        )
        embed.set_author(name=f"@{username}")
        embed.description = f"[Watch the video here]({tiktok_url})"

        await interaction.followup.send(embed=embed)

    # Optional: handle cooldown error to give user feedback
    @fyp_slash.error
    async def fyp_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Please wait {error.retry_after:.1f} seconds before using this command again.",
                ephemeral=True
            )
        else:
            raise error

async def setup(bot):
    await bot.add_cog(FYP(bot))
