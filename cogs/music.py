import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # guild_id: list of songs {title, url}
        self.current_players = {}  # guild_id: voice_client

    async def play_next(self, guild_id):
        queue = self.queues.get(guild_id)
        vc = self.current_players.get(guild_id)

        if not queue or len(queue) == 0:
            # No more songs, disconnect voice client if connected
            if vc and vc.is_connected():
                await vc.disconnect()
            self.current_players.pop(guild_id, None)
            return

        song = queue.pop(0)
        url = song["url"]
        title = song["title"]

        def after_playing(error):
            # This runs in a different thread — use run_coroutine_threadsafe
            fut = asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        if vc is None or not vc.is_connected():
            # If no voice client, clear queue
            self.queues.pop(guild_id, None)
            return

        try:
            vc.stop()
            ffmpeg_opts = {'options': '-vn'}
            source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
            vc.play(source, after=after_playing)

            # Send "Now playing" message to the voice channel text channel if possible
            # You can cache a text channel ID or just send to the voice channel's guild's system channel
            channel = vc.channel
            coro = channel.send(f"🎶 Now playing: **{title}**")
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        except Exception as e:
            print(f"Error playing audio: {e}")
            # Try playing next song if error occurs
            await self.play_next(guild_id)

    @app_commands.command(name="join", description="Join your voice channel")
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

    @app_commands.command(name="play", description="Play a song or playlist from YouTube")
    @app_commands.describe(query="YouTube URL or search keywords")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        guild_id = interaction.guild.id
        vc = interaction.guild.voice_client
        if vc is None:
            if interaction.user.voice is None:
                return await interaction.followup.send("You're not in a voice channel.", ephemeral=True)
            channel = interaction.user.voice.channel
            vc = await channel.connect()
        self.current_players[guild_id] = vc

        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'ytsearch',
            'extract_flat': False,
            'ignoreerrors': True,
            'no_warnings': True,
            'source_address': '0.0.0.0',
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            try:
                info = ytdl.extract_info(query, download=False)
            except Exception as e:
                return await interaction.followup.send(f"Error fetching info: {e}")

        if info is None:
            return await interaction.followup.send("Could not find any results.")

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        queue = self.queues[guild_id]

        if 'entries' in info:
            count_added = 0
            for entry in info['entries']:
                if entry is None:
                    continue
                # Get the best URL
                url = entry.get('url')
                if not url and 'formats' in entry and len(entry['formats']) > 0:
                    url = entry['formats'][0]['url']
                title = entry.get('title', 'Unknown Title')
                if url:
                    queue.append({"title": title, "url": url})
                    count_added += 1
            msg = f"Added {count_added} songs to the queue from playlist **{info.get('title', 'Playlist')}**."
        else:
            url = info.get('url')
            if not url and 'formats' in info and len(info['formats']) > 0:
                url = info['formats'][0]['url']
            title = info.get('title', 'Unknown Title')
            if url:
                queue.append({"title": title, "url": url})
                msg = f"Added **{title}** to the queue."
            else:
                return await interaction.followup.send("Could not retrieve audio URL.")

        # If nothing is playing, start playing the first song in queue
        if not vc.is_playing():
            await self.play_next(guild_id)

        await interaction.followup.send(msg)

    @app_commands.command(name="queue", description="Show the current song queue")
    async def queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = self.queues.get(guild_id, [])
        if not queue:
            return await interaction.response.send_message("The queue is currently empty.")

        embed = discord.Embed(title="Song Queue", color=discord.Color.blurple())
        description = ""
        for i, song in enumerate(queue[:10], 1):
            description += f"{i}. {song['title']}\n"
        if len(queue) > 10:
            description += f"...and {len(queue) - 10} more."

        embed.description = description
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Stop the music and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
            self.queues.pop(guild_id, None)
            self.current_players.pop(guild_id, None)
            await interaction.response.send_message("Stopped playing and cleared the queue.")
        else:
            await interaction.response.send_message("I'm not connected to any voice channel.")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        vc = interaction.guild.voice_client

        if vc is None or not vc.is_connected():
            return await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)

        if not vc.is_playing():
            return await interaction.response.send_message("No song is currently playing.", ephemeral=True)

        vc.stop()  # This triggers after_playing and plays the next song automatically
        await interaction.response.send_message("⏭️ Skipped the current song.")

async def setup(bot):
    await bot.add_cog(Music(bot))
