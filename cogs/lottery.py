import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import datetime

# Role ID for lottery staff
LOTTERY_STAFF_ID = 1347181345922748456  

def is_lottery_staff(interaction: discord.Interaction) -> bool:
    return any(role.id == LOTTERY_STAFF_ID for role in interaction.user.roles)

class Lottery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lotteries = {}  # store active lotteries {message_id: {...}}

    # ========== START LOTTERY ==========
    @app_commands.check(is_lottery_staff)
    @app_commands.command(name="lottery", description="Start a lottery event.")
    async def lottery(
        self, interaction: discord.Interaction,
        duration: str,
        winners: int,
        prize: str,
        channel: discord.TextChannel,
        embed_color: str = "#ff0000",
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None
    ):
        """Start a lottery in a specific channel"""
        await interaction.response.defer(ephemeral=True)

        # Convert duration (e.g., "10m", "2h", "1d") into seconds
        time_multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = duration[-1]
        if unit not in time_multipliers:
            return await interaction.followup.send("❌ Invalid duration format! Use s/m/h/d.", ephemeral=True)
        try:
            duration_seconds = int(duration[:-1]) * time_multipliers[unit]
        except ValueError:
            return await interaction.followup.send("❌ Invalid number for duration!", ephemeral=True)

        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)

        # Embed color
        try:
            color = discord.Color.from_str(embed_color)
        except Exception:
            color = discord.Color.red()

        # Create embed
        embed = discord.Embed(
            title="🎟️ Arcadia Lottery",
            description=f"Prize: **{prize}**\nWinners: **{winners}**\nEnds: <t:{int(end_time.timestamp())}:R>",
            color=color
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)

        embed.set_footer(text="Click 🎟️ to enter!")

        # Send lottery message
        lottery_msg = await channel.send(embed=embed)
        await lottery_msg.add_reaction("🎟️")

        # Store lottery info
        self.lotteries[lottery_msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "channel": channel.id,
            "host": interaction.user.id
        }

        await interaction.followup.send(f"✅ Lottery started in {channel.mention} (ID: `{lottery_msg.id}`).", ephemeral=True)

        # Automatically end after time runs out
        self.bot.loop.create_task(self.end_lottery_after(lottery_msg.id, duration_seconds))

    # ========== END LOTTERY ==========
    @app_commands.check(is_lottery_staff)
    @app_commands.command(name="lottery_end", description="End a running lottery early.")
    async def lottery_end(self, interaction: discord.Interaction, lottery_id: str):
        """End a lottery early using message ID"""
        if not lottery_id.isdigit():
            return await interaction.response.send_message("❌ Invalid lottery ID!", ephemeral=True)

        lottery_id = int(lottery_id)
        if lottery_id not in self.lotteries:
            return await interaction.response.send_message("❌ No active lottery with that ID!", ephemeral=True)

        await self.finish_lottery(lottery_id)
        await interaction.response.send_message(f"✅ Lottery `{lottery_id}` has been ended.", ephemeral=True)

    # ========== TASK: END LOTTERY ==========
    async def end_lottery_after(self, lottery_id: int, delay: int):
        await asyncio.sleep(delay)
        if lottery_id in self.lotteries:
            await self.finish_lottery(lottery_id)

    async def finish_lottery(self, lottery_id: int):
        lottery = self.lotteries.pop(lottery_id, None)
        if not lottery:
            return

        channel = self.bot.get_channel(lottery["channel"])
        if not channel:
            return

        try:
            message = await channel.fetch_message(lottery_id)
        except discord.NotFound:
            return

        # Get participants
        reaction = discord.utils.get(message.reactions, emoji="🎟️")
        if not reaction:
            return await channel.send("❌ No participants for this lottery.")

        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            return await channel.send("❌ No valid participants for this lottery.")

        # Pick winners
        winners_count = min(lottery["winners"], len(users))
        winners = random.sample(users, winners_count)

        winner_mentions = ", ".join(w.mention for w in winners)
        await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{lottery['prize']}** 🎁")

        # Edit original embed to mark ended
        embed = message.embeds[0]
        embed.color = discord.Color.dark_gray()
        embed.description += f"\n\n**Ended!** Winners: {winner_mentions}"
        await message.edit(embed=embed)

    # Error handler for missing role
    @lottery.error
    @lottery_end.error
    async def on_lottery_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ Only Lottery Staff can use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lottery(bot))
