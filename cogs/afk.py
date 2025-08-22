import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL

AFK_EMOJI_ID = 1408383909636476998
EMBED_COLOR = 0xE1D3C4  # Beige color

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        print("AFK Cog initialized and connected to MongoDB.")

    def format_duration(self, duration: timedelta) -> str:
        """Formats a timedelta object into a human-readable string."""
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")

        return ", ".join(parts) if parts else "a few seconds"

    def _create_afk_embed(self, user: discord.Member, reason: str = None) -> discord.Embed:
        """Creates the AFK status embed."""
        afk_message = f"<:hii:{AFK_EMOJI_ID}> You are now in **AFK!**\n"
        if reason:
            afk_message += f"Reason: **{reason}**"

        return discord.Embed(
            description=afk_message,
            color=EMBED_COLOR
        )

    def _create_return_embed(self, user: discord.Member, afk_time: datetime) -> discord.Embed:
        """Creates the welcome back embed."""
        duration = datetime.utcnow() - afk_time
        formatted_duration = self.format_duration(duration)
        
        end_message = f"<:hii:{AFK_EMOJI_ID}> Welcome back, **{user.display_name}**! You were last seen **{formatted_duration}** ago."
        
        return discord.Embed(
            description=end_message,
            color=EMBED_COLOR
        )

    @app_commands.command(name="afk", description="Set yourself as AFK with an optional reason.")
    @app_commands.describe(reason="The reason for being AFK (optional).")
    async def afk_slash(self, interaction: discord.Interaction, reason: str = None):
        """Handles the slash command version of the AFK command."""
        await interaction.response.defer()
        
        self.db.update_one(
            {"_id": str(interaction.user.id)},
            {"$set": {"afk": {"reason": reason, "time": datetime.utcnow()}}},
            upsert=True
        )

        embed = self._create_afk_embed(interaction.user, reason)
        await interaction.followup.send(embed=embed)

        try:
            if interaction.user.guild.me.guild_permissions.manage_nicknames and interaction.user.top_role.position < interaction.user.guild.me.top_role.position:
                if not interaction.user.nick or not interaction.user.nick.startswith("[AFK]"):
                    original_nick = interaction.user.nick if interaction.user.nick else interaction.user.name
                    await interaction.user.edit(nick=f"[AFK] {original_nick}")
        except Exception as e:
            print(f"Nickname error for {interaction.user.display_name}: {e}")


    @commands.command(name="afk", help="Set yourself as AFK with an optional reason. Usage: $afk [reason]")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = None):
        """Handles the prefix command version of the AFK command."""
        self.db.update_one(
            {"_id": str(ctx.author.id)},
            {"$set": {"afk": {"reason": reason, "time": datetime.utcnow()}}},
            upsert=True
        )
        
        embed = self._create_afk_embed(ctx.author, reason)
        await ctx.send(embed=embed)

        try:
            if ctx.author.guild.me.guild_permissions.manage_nicknames and ctx.author.top_role.position < ctx.author.guild.me.top_role.position:
                if not ctx.author.nick or not ctx.author.nick.startswith("[AFK]"):
                    original_nick = ctx.author.nick if ctx.author.nick else ctx.author.name
                    await ctx.author.edit(nick=f"[AFK] {original_nick}")
        except Exception as e:
            print(f"Nickname error for {ctx.author.display_name}: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = str(message.author.id)
        user_data = self.db.find_one({"_id": user_id})

        # Check if the user is coming back from AFK
        if user_data and "afk" in user_data and not message.content.lower().startswith((f"{self.bot.command_prefix}afk", "/afk")):
            self.db.update_one({"_id": user_id}, {"$unset": {"afk": ""}})

            try:
                if message.guild.me.guild_permissions.manage_nicknames and message.author.top_role.position < message.guild.me.top_role.position:
                    if message.author.nick and message.author.nick.startswith("[AFK]"):
                        original_nick = message.author.nick.removeprefix("[AFK]").strip()
                        await message.author.edit(nick=original_nick or None)
            except Exception as e:
                print(f"Failed to reset nickname: {e}")

            embed = self._create_return_embed(message.author, user_data["afk"]["time"])
            await message.channel.send(embed=embed)

        # Check for mentions of AFK users
        afk_mentioned = set()
        for member in message.mentions:
            if member.bot or member.id in afk_mentioned:
                continue

            afk_data = self.db.find_one({"_id": str(member.id)})
            if afk_data and "afk" in afk_data:
                reason = afk_data["afk"]["reason"]
                afk_time = afk_data["afk"]["time"]

                response = f"{member.mention} is currently **AFK!**\n"
                if reason:
                    response += f"With reason: **{reason}**\n"
                response += f"Since: <t:{int(afk_time.timestamp())}:R>"
                
                embed = discord.Embed(
                    description=response,
                    color=EMBED_COLOR
                )
                
                await message.channel.send(embed=embed)
                afk_mentioned.add(member.id)
                break  # Respond only once

    def cog_unload(self):
        """Closes the MongoDB connection when the cog is unloaded."""
        self.client.close()
        print("AFK MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(AFK(bot))
