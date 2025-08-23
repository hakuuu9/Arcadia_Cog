import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL
import asyncio, random, datetime, re

# --- Constants ---
GIVEAWAY_STAFF_ROLE_ID = 1347181345922748456
DEFAULT_FOOTER = "They Say That The Best Blaze Burns The Brightest When Circumstances Are At Their Worst."
# You can customize the embed color here
DEFAULT_EMBED_COLOR = 0xE1D3C4 # Using integer format for discord.Color

# --- Helper Function ---
def parse_duration(duration_str: str) -> int:
    """Parse duration like 5s, 10m, 2h, 1d into seconds."""
    pattern = r"(\d+)([smhd])"
    match = re.match(pattern, duration_str.lower())
    if not match:
        raise ValueError("Invalid duration format. Use formats like `10m`, `2h`, or `7d`.")
    
    amount, unit = match.groups()
    amount = int(amount)
    
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    return amount * multipliers[unit]

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.giveaways
        self.check_giveaways.start()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.check_giveaways.cancel()
        self.client.close()

    async def _get_valid_entrants(self, giveaway_data: dict) -> list[discord.Member]:
        """Helper to fetch and filter giveaway entrants based on reaction and roles."""
        channel = self.bot.get_channel(giveaway_data["channel_id"])
        if not channel:
            return []
        try:
            message = await channel.fetch_message(giveaway_data["message_id"])
        except discord.NotFound:
            return []

        reaction = discord.utils.get(message.reactions, emoji="🎉")
        if not reaction:
            return []

        # Get a list of discord.User objects who reacted
        users = [user async for user in reaction.users()]
        
        entrants_with_weights = []
        for user in users:
            if user.bot:
                continue

            # We need the Member object to check roles, user from reaction might not be
            member = channel.guild.get_member(user.id)
            if not member:
                continue  # User might have left the server

            # Check for required role
            if giveaway_data.get("required_role"):
                required_role_id = giveaway_data["required_role"]
                if not any(r.id == required_role_id for r in member.roles):
                    continue
            
            # Calculate total entries for this member
            entry_count = 1
            for role_id in giveaway_data.get("extra_roles", []):
                if any(r.id == role_id for r in member.roles):
                    entry_count += 1
            
            entrants_with_weights.extend([member] * entry_count)
            
        return entrants_with_weights

    async def _end_giveaway_logic(self, message_id: int, reroll: bool = False):
        """The core logic for ending or rerolling a giveaway."""
        giveaway = self.db.find_one({"_id": str(message_id)})
        if not giveaway:
            # Cannot end/reroll a giveaway that is not in the database
            return "Giveaway not found in the database. It might have been deleted."

        channel = self.bot.get_channel(giveaway["channel_id"])
        if not channel:
            return "Giveaway channel not found."
        try:
            message = await channel.fetch_message(giveaway["message_id"])
        except discord.NotFound:
            return "Giveaway message not found."

        all_entrants = await self._get_valid_entrants(giveaway)
        
        if not all_entrants:
            winner_text = "No one with valid entries entered! 😢"
            winners_list = []
        else:
            winners_count = giveaway["winners"]
            
            # Shuffle the weighted list of entrants
            random.shuffle(all_entrants)
            
            # Pick unique winners from the shuffled list
            winners_list = []
            winner_ids = set()
            for entrant in all_entrants:
                if entrant.id not in winner_ids:
                    winners_list.append(entrant)
                    winner_ids.add(entrant.id)
                if len(winners_list) == winners_count:
                    break
        
        # Prepare the winner announcement text
        if winners_list:
            winner_text = "\n".join([f"› {winner.mention}" for winner in winners_list])
            if not reroll: # Only ping on the initial giveaway end
                await channel.send(f"Congratulations {', '.join([w.mention for w in winners_list])}! You won the **{giveaway['prize']}**!")
        else:
            winner_text = "Could not determine a winner."
            
        # Update the original giveaway embed
        embed = message.embeds[0]
        embed.title = "🎉 **ARCADIA GIVEAWAY ENDED** 🎉" # <--- EDITED TITLE
        embed.description = (
            f"**`{giveaway['prize']}`**\n\n"
            f"**Winner(s):**\n{winner_text}"
        )
        embed.clear_fields() # Remove 'Requirements' and 'Extra Entries' fields
        embed.set_footer(text=f"Ended | Reroll with /giveaway_reroll message_id:{message_id}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await message.edit(embed=embed)

        # Update the database record to mark as ended and store winners
        self.db.update_one(
            {"_id": str(message_id)},
            {"$set": {"ended": True, "winner_ids": [w.id for w in winners_list]}}
        )
        return f"Giveaway {message_id} has been successfully {'rerolled' if reroll else 'ended'}."

    # ----------------------
    # Background Task to check for giveaways to end
    # ----------------------
    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        """Periodically checks the database for giveaways that are due to end."""
        now = datetime.datetime.now(datetime.timezone.utc)
        # Find giveaways past their end_time that haven't been marked as ended
        ended_giveaways = self.db.find({"end_time": {"$lte": now}, "ended": {"$ne": True}})
        
        for giveaway in ended_giveaways:
            print(f"Ending giveaway {giveaway['_id']}...")
            await self._end_giveaway_logic(giveaway["message_id"])

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

    # ----------------------
    # Start Giveaway Command
    # ----------------------
    @app_commands.command(name="giveaway", description="Start a new giveaway")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    async def giveaway(
        self, interaction: discord.Interaction,
        duration: str,
        winners: int,
        prize: str,
        channel: discord.TextChannel,
        required_role: discord.Role = None,
        extra_entry_roles: str = None,
        color: str = None,
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            await interaction.followup.send(f"❌ Error: {e}")
            return

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        end_timestamp = int(end_time.timestamp())

        # Parse extra roles from string to list of IDs
        extra_roles_ids = []
        if extra_entry_roles:
            role_ids_str = re.findall(r'\d+', extra_entry_roles)
            extra_roles_ids = [int(rid) for rid in role_ids_str]

        embed_color = int(color.replace("#", ""), 16) if color else DEFAULT_EMBED_COLOR
        
        embed = discord.Embed(
            title=" **ARCADIA GIVEAWAY** ", # <--- EDITED TITLE
            description=(
                f"**`{prize}`**\n\n"
                f"React with 🎉 to enter!\n"
                f"Ends: <t:{end_timestamp}:R> (<t:{end_timestamp}:F>)\n"
                f"Winners: **{winners}**"
            ),
            color=embed_color
        )
        if required_role:
            embed.add_field(name="Requirements", value=required_role.mention, inline=False)
        if extra_roles_ids:
            mentions = [f"<@&{role_id}>" for role_id in extra_roles_ids]
            embed.add_field(name="Extra Entries", value=", ".join(mentions), inline=False)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)
        embed.set_footer(text=DEFAULT_FOOTER)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("🎉")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to send messages or add reactions in that channel.")
            return

        giveaway_data = {
            "_id": str(msg.id),
            "prize": prize,
            "channel_id": channel.id,
            "message_id": msg.id,
            "end_time": end_time,
            "winners": winners,
            "required_role": required_role.id if required_role else None,
            "extra_roles": extra_roles_ids,
            "ended": False
        }
        self.db.insert_one(giveaway_data)
        await interaction.followup.send(f"✅ Giveaway started in {channel.mention}! View it here: {msg.jump_url}")

    # ----------------------
    # End Giveaway Command
    # ----------------------
    @app_commands.command(name="giveaway_end", description="End a giveaway manually before its scheduled time")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        response = await self._end_giveaway_logic(int(message_id))
        await interaction.followup.send(f"✅ {response}")

    # ----------------------
    # Reroll Giveaway Command
    # ----------------------
    @app_commands.command(name="giveaway_reroll", description="Reroll a winner for an ended giveaway")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        response = await self._end_giveaway_logic(int(message_id), reroll=True)
        await interaction.followup.send(f"🔁 {response}")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
