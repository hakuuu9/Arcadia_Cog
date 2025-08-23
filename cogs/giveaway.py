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
        
    # ----------------------
    # EVENT LISTENER: To check for role requirements on reaction
    # ----------------------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore reactions from the bot itself
        if payload.user_id == self.bot.user.id:
            return

        # We only care about the giveaway emoji
        if str(payload.emoji) != "🎉":
            return

        # Check if the message is an active giveaway
        giveaway = self.db.find_one({"_id": str(payload.message_id), "ended": False})
        if not giveaway:
            return

        # Check if there's a required role. If not, we don't need to do anything.
        required_role_id = giveaway.get("required_role")
        if not required_role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        member = guild.get_member(payload.user_id)
        if not member: return

        required_role = guild.get_role(required_role_id)
        if not required_role: return

        # If the member does NOT have the required role
        if required_role not in member.roles:
            # 1. Remove their reaction
            try:
                channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
            except (discord.Forbidden, discord.NotFound):
                # Bot might not have perms to remove reactions, or message was deleted
                pass

            # 2. Send them a DM explaining why
            try:
                dm_message = (
                    f"Hi {member.display_name}, you tried to enter the giveaway for **{giveaway['prize']}** "
                    f"in **{guild.name}**, but you are missing the required role: `{required_role.name}`."
                )
                await member.send(dm_message)
            except discord.Forbidden:
                # User has DMs closed.
                pass

    async def _get_valid_entrants(self, giveaway_data: dict) -> list[discord.Member]:
        """Helper to fetch and filter giveaway entrants based on reaction and roles."""
        channel = self.bot.get_channel(giveaway_data["channel_id"])
        if not channel: return []
        try:
            message = await channel.fetch_message(giveaway_data["message_id"])
        except discord.NotFound: return []

        reaction = discord.utils.get(message.reactions, emoji="🎉")
        if not reaction: return []

        users = [user async for user in reaction.users()]
        
        entrants_with_weights = []
        for user in users:
            if user.bot: continue
            member = channel.guild.get_member(user.id)
            if not member: continue

            if giveaway_data.get("required_role"):
                if not any(r.id == giveaway_data["required_role"] for r in member.roles):
                    continue
            
            entry_count = 1
            for role_id in giveaway_data.get("extra_roles", []):
                if any(r.id == role_id for r in member.roles):
                    entry_count += 1
            
            entrants_with_weights.extend([member] * entry_count)
            
        return entrants_with_weights

    async def _end_giveaway_logic(self, message_id: int, reroll: bool = False):
        """The core logic for ending or rerolling a giveaway."""
        giveaway = self.db.find_one({"_id": str(message_id)})
        if not giveaway: return "Giveaway not found in the database."

        channel = self.bot.get_channel(giveaway["channel_id"])
        if not channel: return "Giveaway channel not found."
        try:
            message = await channel.fetch_message(giveaway["message_id"])
        except discord.NotFound: return "Giveaway message not found."

        all_entrants = await self._get_valid_entrants(giveaway)
        
        if not all_entrants:
            winners_list = []
        else:
            winners_count = giveaway["winners"]
            random.shuffle(all_entrants)
            winners_list = []
            winner_ids = set()
            for entrant in all_entrants:
                if entrant.id not in winner_ids:
                    winners_list.append(entrant)
                    winner_ids.add(entrant.id)
                if len(winners_list) == winners_count: break
        
        if winners_list:
            winner_text = "\n".join([f"› {winner.mention}" for winner in winners_list])
            if not reroll:
                await channel.send(f"Congratulations {', '.join([w.mention for w in winners_list])}! You won the **{giveaway['prize']}**!")
        else:
            winner_text = "No one with valid entries entered! 😢" if not reroll else "Could not determine a new winner."
            
        embed = message.embeds[0]
        embed.title = "🎉 **ARCADIA GIVEAWAY ENDED** 🎉"
        end_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        embed.description = (
            f"**`{giveaway['prize']}`**\n\n"
            f"**Winner(s):**\n{winner_text}\n\n"
            f"**Ended:** <t:{end_timestamp}:F>"
        )
        embed.clear_fields()
        embed.set_footer(text=f"Ended | Reroll with /giveaway_reroll message_id:{message_id}")
        await message.edit(embed=embed)

        self.db.update_one(
            {"_id": str(message_id)},
            {"$set": {"ended": True, "winner_ids": [w.id for w in winners_list]}}
        )
        return f"Giveaway {message_id} has been successfully {'rerolled' if reroll else 'ended'}."

    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        """Periodically checks the database for giveaways that are due to end."""
        now = datetime.datetime.now(datetime.timezone.utc)
        ended_giveaways = self.db.find({"end_time": {"$lte": now}, "ended": {"$ne": True}})
        
        for giveaway in ended_giveaways:
            print(f"Ending giveaway {giveaway['_id']}...")
            await self._end_giveaway_logic(giveaway["message_id"])

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

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

        start_time = datetime.datetime.now(datetime.timezone.utc)
        end_time = start_time + datetime.timedelta(seconds=seconds)
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        extra_roles_ids = []
        if extra_entry_roles:
            role_ids_str = re.findall(r'\d+', extra_entry_roles)
            extra_roles_ids = [int(rid) for rid in role_ids_str]

        embed_color = int(color.replace("#", ""), 16) if color else DEFAULT_EMBED_COLOR
        
        embed = discord.Embed(
            title="🎉 **ARCADIA GIVEAWAY** 🎉",
            description=(
                f"**`{prize}`**\n\n"
                f"React with 🎉 to enter!\n"
                f"Winners: **{winners}**\n\n"
                f"**Started:** <t:{start_timestamp}:F>\n"
                f"**Ends:** <t:{end_timestamp}:F> (<t:{end_timestamp}:R>)"
            ),
            color=embed_color
        )
        if required_role:
            embed.add_field(name="Requirements", value=required_role.mention, inline=False)
        if extra_roles_ids:
            mentions = [f"<@&{role_id}>" for role_id in extra_roles_ids]
            embed.add_field(name="Extra Entries", value=", ".join(mentions), inline=False)

        if thumbnail: embed.set_thumbnail(url=thumbnail.url)
        if image: embed.set_image(url=image.url)
        embed.set_footer(text=DEFAULT_FOOTER)

        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("🎉")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to send messages or add reactions in that channel.")
            return

        giveaway_data = {
            "_id": str(msg.id), "prize": prize, "channel_id": channel.id,
            "message_id": msg.id, "end_time": end_time, "winners": winners,
            "required_role": required_role.id if required_role else None,
            "extra_roles": extra_roles_ids, "ended": False
        }
        self.db.insert_one(giveaway_data)
        await interaction.followup.send(f"✅ Giveaway started in {channel.mention}! View it here: {msg.jump_url}")

    @app_commands.command(name="giveaway_end", description="End a giveaway manually before its scheduled time")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        response = await self._end_giveaway_logic(int(message_id))
        await interaction.followup.send(f"✅ {response}")

    @app_commands.command(name="giveaway_reroll", description="Reroll a winner for an ended giveaway")
    @app_commands.checks.has_role(GIVEAWAY_STAFF_ROLE_ID)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        response = await self._end_giveaway_logic(int(message_id), reroll=True)
        await interaction.followup.send(f"🔁 {response}")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
