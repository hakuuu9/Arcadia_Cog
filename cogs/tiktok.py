import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import io
import re

class TikTok(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tiktok", description="Download a TikTok video and send it as a file!")
    @app_commands.describe(url="The URL of the TikTok video.")
    async def tiktok(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        # Validate URL
        if not re.match(r"https?://(www\.)?(tiktok\.com|vm\.tiktok\.com|m\.tiktok\.com|vt\.tiktok\.com)/", url):
            await interaction.followup.send("❌ That doesn't look like a valid TikTok URL.", ephemeral=True)
            return

        try:
            async with aiohttp.ClientSession() as session:
                api_url = f"https://tikwm.com/api/?url={url}"
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"❌ TikTok API error: HTTP {resp.status}", ephemeral=True)
                        return
                    data = await resp.json()

            if data.get("code") != 0:
                await interaction.followup.send(f"❌ API error: {data.get('msg', 'Unknown error')}", ephemeral=True)
                return

            video_data = data.get("data")
            if not video_data:
                await interaction.followup.send("❌ No video data found.", ephemeral=True)
                return

            video_url = video_data.get("nwm_play") or video_data.get("play")
            title = video_data.get("title", "TikTok Video")

            if not video_url:
                await interaction.followup.send("❌ Could not find a video URL.", ephemeral=True)
                return

            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as video_resp:
                    if video_resp.status != 200:
                        await interaction.followup.send(f"❌ Failed to download video (HTTP {video_resp.status}).", ephemeral=True)
                        return
                    video_bytes = await video_resp.read()

            # Check size (Discord max default 8MB)
            max_size = 8 * 1024 * 1024
            if len(video_bytes) > max_size:
                await interaction.followup.send("❌ Video is too large to send (over 8MB).", ephemeral=True)
                return

            file = discord.File(io.BytesIO(video_bytes), filename="tiktok_video.mp4")

            await interaction.followup.send(content=f"**{title}**", file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
            print(f"Error in TikTok command: {e}")

async def setup(bot):
    await bot.add_cog(TikTok(bot))
