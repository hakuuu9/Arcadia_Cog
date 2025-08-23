import discord
from discord.ext import commands
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
        self.lotteries = {}  # {message_id: {...}}

    # ========== START LOTTERY ==========
    @app_commands.check(is_lottery_staff)
    @app_commands.command(name="lottery", description="Start a lottery event.")
    async def lottery(
        self, interaction: discord.Interaction,
        duration: str,
        winners: int,
        prize: str,
        channel: discord.TextChannel,
        required_role: discord.Role = None,
        embed_color: str = "#ff0000",
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None
    ):
        await interaction.response.defer(ephemeral=True)

        # Convert duration
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

        # Role requirement text
        role_text = required_role.mention if required_role else "None"

        # Create embed
        embed = discord.Embed(
            title="**ARCADIA GIVEAWAY**",
            description=(
                f"React with 🎟️ to enter!\n"
                f"Total Entries: `0`\n\n"
                f"Winners: `{winners}`\n"
                f"Ends: <t:{int(end_time.timestamp())}:R>\n"
                f"Requirements: {role_text}"
            ),
            color=color
        )

        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)

        # Default footer
        embed.set_footer(text="They Say That The Best Blaze Burns The Brightest When Circumstances Are At Their Worst.")

        # Send lottery message
        lottery_msg = await channel.send(embed=embed)
        await lottery_msg.add_reaction("🎟️")

        # Store lottery info
        self.lotteries[lottery_msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "channel": channel.id,
            "host": interaction.user.id,
            "required_role": required_role.id if required_role else None,
            "winner_ids": []
        }

        await interaction.followup.send(f"✅ Lottery started in {channel.mention} (ID: `{lottery_msg.id}`).", ephemeral=True)

        # Auto end
        self.bot.loop.create_task(self.end_lottery_after(lottery_msg.id, duration_seconds))

    # ========== END LOTTERY ==========
    @app_commands.check(is_lottery_staff)
    @app_commands.command(name="lottery_end", description="End a running lottery early.")
    async def lottery_end(self, interaction: discord.Interaction, lottery_id: str):
        if not lottery_id.isdigit():
            return await interaction.response.send_message("❌ Invalid lottery ID!", ephemeral=True)

        lottery_id = int(lottery_id)
        if lottery_id not in self.lotteries:
            return await interaction.response.send_message("❌ No active lottery with that ID!", ephemeral=True)

        await self.finish_lottery(lottery_id)
        await interaction.response.send_message(f"✅ Lottery `{lottery_id}` has been ended.", ephemeral=True)

    # ========== REROLL WINNERS ==========
    @app_commands.check(is_lottery_staff)
    @app_commands.command(name="lottery_reroll", description="Reroll winners for a lottery.")
    async def lottery_reroll(self, interaction: discord.Interaction, lottery_id: str):
        if not lottery_id.isdigit():
            return await interaction.response.send_message("❌ Invalid lottery ID!", ephemeral=True)
        lottery_id = int(lottery_id)
        if lottery_id not in self.lotteries:
            return await interaction.response.send_message("❌ No active lottery with that ID!", ephemeral=True)

        lottery = self.lotteries[lottery_id]
        channel = self.bot.get_channel(lottery["channel"])
        message = await channel.fetch_message(lottery_id)

        reaction = discord.utils.get(message.reactions, emoji="🎟️")
        users = [u async for u in reaction.users() if not u.bot]

        if lottery["required_role"]:
            role_id = lottery["required_role"]
            users = [u for u in users if any(r.id == role_id for r in u.roles)]

        if not users:
            return await interaction.response.send_message("❌ No valid participants to reroll.", ephemeral=True)

        winners_count = min(lottery["winners"], len(users))
        winners = random.sample(users, winners_count)

        winner_mentions = ", ".join(w.mention for w in winners)
        lottery["winner_ids"] = [w.id for w in winners]

        # Winner embed
        win_embed = discord.Embed(
            title="🎉 Lottery Winners (Reroll) 🎉",
            description=(
                f"**Prize:** {lottery['prize']}\n"
                f"**Winners:** {winner_mentions}\n"
                f"**Hosted By:** <@{lottery['host']}>"
            ),
            color=discord.Color.gold()
        )
        win_embed.set_footer(text=f"Reroll with: /lottery reroll {lottery_id}")
        await channel.send(embed=win_embed)
        await interaction.response.send_message(f"✅ Lottery `{lottery_id}` rerolled.", ephemeral=True)

    # ========== AUTO END ==========
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

        reaction = discord.utils.get(message.reactions, emoji="🎟️")
        if not reaction:
            return await channel.send("❌ No participants for this lottery.")

        users = [u async for u in reaction.users() if not u.bot]

        if lottery["required_role"]:
            role_id = lottery["required_role"]
            users = [u for u in users if any(r.id == role_id for r in u.roles)]

        if not users:
            return await channel.send("❌ No valid participants for this lottery.")

        winners_count = min(lottery["winners"], len(users))
        winners = random.sample(users, winners_count)
        lottery["winner_ids"] = [w.id for w in winners]

        winner_mentions = ", ".join(w.mention for w in winners)

        # Winner embed
        win_embed = discord.Embed(
            title="🎉 Lottery Winners 🎉",
            description=(
                f"**Prize:** {lottery['prize']}\n"
                f"**Winners:** {winner_mentions}\n"
                f"**Hosted By:** <@{lottery['host']}>"
            ),
            color=discord.Color.green()
        )
        win_embed.set_footer(text=f"Reroll with: /lottery reroll {lottery_id}")
        await channel.send(embed=win_embed)

        # Update original message embed
        embed = message.embeds[0]
        embed.color = discord.Color.dark_gray()
        embed.description += f"\n\n**Ended!** Winners: {winner_mentions}"
        await message.edit(embed=embed)

    # ========== UPDATE ENTRIES ==========
    async def update_entries(self, payload):
        if payload.message_id not in self.lotteries:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Count entries (ignore bots)
        reaction = discord.utils.get(message.reactions, emoji="🎟️")
        users = [u async for u in reaction.users() if not u.bot]

        # Update embed
        embed = message.embeds[0]
        lines = embed.description.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Total Entries:"):
                lines[i] = f"Total Entries: `{len(users)}`"
        embed.description = "\n".join(lines)

        await message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == "🎟️":
            await self.update_entries(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if str(payload.emoji) == "🎟️":
            await self.update_entries(payload)

    @lottery.error
    @lottery_end.error
    @lottery_reroll.error
    async def on_lottery_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ Only Lottery Staff can use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lottery(bot))
