import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Join the voice channel you're in")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            return await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)

        voice_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc:
            await vc.move_to(voice_channel)
        else:
            await voice_channel.connect()

        await interaction.response.send_message(f"Joined {voice_channel.name}!")

    @app_commands.command(name="play", description="Play a YouTube URL or search term")
    @app_commands.describe(query="YouTube URL or search keywords")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        vc = interaction.guild.voice_client
        if vc is None:
            if interaction.user.voice is None:
                return await interaction.followup.send("You're not in a voice channel.", ephemeral=True)
            channel = interaction.user.voice.channel
            vc = await channel.connect()

        ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'extract_flat': False,
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            try:
                info = ytdl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info.get('url') or info['formats'][0]['url']
                title = info.get('title', 'Unknown Title')
            except Exception as e:
                return await interaction.followup.send(f"Error playing audio: {e}")

        vc.stop()
        ffmpeg_opts = {'options': '-vn'}
        try:
            vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_opts))
            await interaction.followup.send(f"🎶 Now playing: **{title}**")
        except Exception as e:
            await interaction.followup.send(f"Error playing audio: {e}")

    @app_commands.command(name="stop", description="Stop the music and leave the voice channel")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("Stopped and left the voice channel.")
        else:
            await interaction.response.send_message("I'm not connected to any voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
