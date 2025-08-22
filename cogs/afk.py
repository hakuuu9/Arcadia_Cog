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

    async def _send_afk_embed(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Helper function to send the AFK embed."""
        current_time = datetime.utcnow()
        self.db.update_one(
            {"_id": str(user.id)},
            {"$set": {"afk": {"reason": reason, "time": current_time}}},
            upsert=True
        )

        embed = discord.Embed(
            description=f"<:hii:{AFK_EMOJI_ID}> You are now in **AFK!**",
            color=EMBED_COLOR
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"I'll let people know when they mention you. Since: ")
        embed.timestamp = current_time

        await interaction.response.send_message(embed=embed)
        
    async def _handle_afk_set(self, user: discord.Member, reason: str, send_response_func):
        """A core function to handle the AFK status setting logic for both command types."""
        user_id = str(user.id)
        current_time = datetime.utcnow()

        self.db.update_one(
            {"_id": user_id},
            {"$set": {"afk": {"reason": reason, "time": current_time}}},
            upsert=True
        )

        embed = discord.Embed(
            description=f"<:hii:{AFK_EMOJI_ID}> You are now in **AFK!**",
            color=EMBED_COLOR
        )
        if reason:
            embed.add_field(name="Reason", value=f"**{reason}**", inline=False)
        embed.set_footer(text=f"I'll let people know when they mention you.")
        embed.timestamp = current_time

        await send_response_func(embed=embed)

        try:
            if user.guild.me.guild_permissions.manage_nicknames and user.top_role.position < user.guild.me.top_role.position:
                if not user.nick or not user.nick.startswith("[AFK]"):
                    original_nick = user.nick if user.nick else user.name
                    await user.edit(nick=f"[AFK] {original_nick}")
        except Exception as e:
            print(f"Nickname error for {user.display_name}: {e}")

    @app_commands.command(name="afk", description="Set yourself as AFK with an optional reason.")
    @app_commands.describe(reason="The reason for being AFK (optional).")
    async def afk_slash(self, interaction: discord.Interaction, reason: str = None):
        """Handles the slash command version of the AFK command."""
        await interaction.response.defer()
        await self._handle_afk_set(
            user=interaction.user,
            reason=reason,
            send_response_func=interaction.followup.send
        )

    @commands.command(name="afk", help="Set yourself as AFK with an optional reason. Usage: $afk [reason]")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = None):
        """Handles the prefix command version of the AFK command."""
        await self._handle_afk_set(
            user=ctx.author,
            reason=reason,
            send_response_func=ctx.send
        )

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

            afk_time = user_data["afk"]["time"]
            duration = datetime.utcnow() - afk_time
            formatted_duration = self.format_duration(duration)

            embed = discord.Embed(
                description=f"<:hii:{AFK_EMOJI_ID}> Welcome back, **{message.author.display_name}**! You were last seen **{formatted_duration}** ago.",
                color=EMBED_COLOR
            )
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

                embed = discord.Embed(
                    description=f"{member.mention} is currently **AFK!**",
                    color=EMBED_COLOR
                )
                if reason:
                    embed.add_field(name="Reason", value=f"**{reason}**", inline=False)
                embed.set_footer(text="Since:")
                embed.timestamp = afk_time

                await message.channel.send(embed=embed)
                afk_mentioned.add(member.id)
                break  # Respond only once

    def cog_unload(self):
        """Closes the MongoDB connection when the cog is unloaded."""
        self.client.close()
        print("AFK MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(AFK(bot))
