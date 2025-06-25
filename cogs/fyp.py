import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import config  # this imports your ZYLA_API_KEY

class FYP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fyp", description="Get a random TikTok video you can watch inside Discord!")
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

        await interaction.followup.send(tiktok_url)

async def setup(bot):
    await bot.add_cog(FYP(bot))
