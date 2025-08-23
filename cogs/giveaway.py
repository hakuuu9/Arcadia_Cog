import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL
import asyncio, random, datetime, re

GIVEAWAY_STAFF_ROLE_ID = 1347181345922748456
DEFAULT_FOOTER = "They Say That The Best Blaze Burns The Brightest When Circumstances Are At Their Worst."

def parse_duration(duration_str: str) -> int:
    """Parse duration like 5s, 10m, 2h, 1d into seconds."""
    pattern = r"(\d+)([smhd])"
    match = re.match(pattern, duration_str)
    if not match:
        raise ValueError("Invalid duration format. Use 5s/m/h/d.")
    amount, unit = match.groups()
    amount = int(amount)
    if unit == "s":
        return amount
    elif unit == "m":
        return amount * 60
    elif unit == "h":
        return amount * 3600
    elif unit == "d":
        return amount * 86400

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.giveaways

    def cog_unload(self):
        self.client.close()

    # ----------------------
    # Start Giveaway Command
    # ----------------------
    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    @app_commands.describe(
        duration="Duration e.g. 5s, 10m, 2h, 1d",
        winners="Number of winners",
        prize="Prize description",
        channel="Text channel for giveaway",
        required_role="Role required to enter (optional)",
        extra_entry_roles="Roles that give extra entries (comma separated, optional)",
        color="Embed color (hex, optional)",
        thumbnail="Thumbnail image (optional)",
        image="Image (optional)"
    )
    async def giveaway(
        self, interaction: discord.Interaction,
        duration: str,
        winners: int,
        prize: str,
        channel: discord.TextChannel,
        required_role: discord.Role = None,
        extra_entry_roles: str = None,
        color: str = "#E1D3C4",
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None
    ):
        await interaction.response.defer()

        seconds = parse_duration(duration)

        # Parse extra roles
        extra_roles = []
        if extra_entry_roles:
            for role_mention in extra_entry_roles.split(","):
                role_mention = role_mention.strip()
                role_id = int(role_mention.replace("<@&", "").replace(">", ""))
                extra_roles.append(role_id)

        embed_color = int(color.replace("#", ""), 16)
        embed = discord.Embed(title="**ARCADIA GIVEAWAY**",
                              description=f"React with 🎉 to enter!\nTotal Entries: 0",
                              color=embed_color)
        embed.add_field(name="Winners", value=f"{winners}", inline=True)
        embed.add_field(name="Ends", value=duration, inline=True)
        embed.add_field(name="Requirements", value=f"{required_role.mention if required_role else 'None'}", inline=True)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)
        embed.set_footer(text=DEFAULT_FOOTER)

        msg = await channel.send(embed=embed)
        await msg.add_reaction("🎉")

        # Save giveaway in DB
        giveaway_data = {
            "_id": str(msg.id),
            "prize": prize,
            "channel_id": channel.id,
            "message_id": msg.id,
            "start_time": datetime.datetime.utcnow(),
            "end_time": datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds),
            "winners": winners,
            "required_role": required_role.id if required_role else None,
            "extra_roles": extra_roles,
            "entries": []
        }
        self.db.insert_one(giveaway_data)

        # Start background task to update total entries
        self.bot.loop.create_task(self.track_entries(msg.id, seconds))

    # ----------------------
    # Track entries live
    # ----------------------
    async def track_entries(self, message_id, duration_seconds):
        giveaway = self.db.find_one({"_id": str(message_id)})
        if not giveaway:
            return

        channel = self.bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])
        start = datetime.datetime.utcnow()
        end_time = start + datetime.timedelta(seconds=duration_seconds)

        while datetime.datetime.utcnow() < end_time:
            await asyncio.sleep(5)  # update every 5s
            message = await channel.fetch_message(giveaway["message_id"])
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            users = await reaction.users().flatten() if reaction else []
            # Filter required role
            valid_users = []
            for user in users:
                if user.bot:
                    continue
                if giveaway["required_role"]:
                    if not any(r.id == giveaway["required_role"] for r in user.roles):
                        continue
                # Extra entries
                count = 1
                for role_id in giveaway.get("extra_roles", []):
                    if any(r.id == role_id for r in user.roles):
                        count += 1
                valid_users.extend([user] * count)

            # Update embed
            embed = message.embeds[0]
            embed.description = f"React with 🎉 to enter!\nTotal Entries: {len(valid_users)}"
            await message.edit(embed=embed)

        # End giveaway after duration
        await self.end_giveaway(message_id)

    # ----------------------
    # End Giveaway Helper
    # ----------------------
    async def end_giveaway(self, message_id: int, reroll=False):
        giveaway = self.db.find_one({"_id": str(message_id)})
        if not giveaway:
            return

        channel = self.bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])
        reaction = discord.utils.get(message.reactions, emoji="🎉")
        users = await reaction.users().flatten() if reaction else []

        valid_users = []
        for user in users:
            if user.bot:
                continue
            if giveaway["required_role"]:
                if not any(r.id == giveaway["required_role"] for r in user.roles):
                    continue
            count = 1
            for role_id in giveaway.get("extra_roles", []):
                if any(r.id == role_id for r in user.roles):
                    count += 1
            valid_users.extend([user] * count)

        winners_count = giveaway["winners"]
        if len(valid_users) == 0:
            winner_text = "No valid entries."
        else:
            winners_list = random.sample(valid_users, k=min(winners_count, len(valid_users)))
            winner_text = "\n".join([f"{i+1}. {u.mention}" for i, u in enumerate(winners_list)])

        # Update embed
        embed = message.embeds[0]
        embed.title = "**ARCADIA GIVEAWAY ENDED**"
        embed.description = f"Prize: {giveaway['prize']}\nWinners:\n{winner_text}"
        embed.set_footer(text=f"Reroll Command: /giveaway_reroll message_id:{message_id}")
        await message.edit(embed=embed)

        if not reroll:
            self.db.delete_one({"_id": str(message_id)})

    # ----------------------
    # End Command
    # ----------------------
    @app_commands.command(name="giveaway_end", description="End a giveaway manually")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    @app_commands.describe(message_id="Giveaway message ID")
    async def giveaway_end(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer()
        await self.end_giveaway(message_id)
        await interaction.followup.send(f"✅ Giveaway {message_id} ended.", ephemeral=True)

    # ----------------------
    # Reroll Command
    # ----------------------
    @app_commands.command(name="giveaway_reroll", description="Reroll a giveaway winner")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    @app_commands.describe(message_id="Giveaway message ID")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer()
        await self.end_giveaway(message_id, reroll=True)
        await interaction.followup.send(f"🔁 Giveaway {message_id} rerolled.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
