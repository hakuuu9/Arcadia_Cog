import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        print("AFK Cog initialized and connected to MongoDB.")

    def format_duration(self, duration: timedelta) -> str:
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

    async def process_afk_set(self, user: discord.Member, reason: str, send_response_func):
        user_id = str(user.id)
        current_time = datetime.utcnow()

        self.db.update_one(
            {"_id": user_id},
            {"$set": {"afk": {"reason": reason, "time": current_time}}},
            upsert=True
        )

        afk_message = f"You are now **AFK!**\n"
        if reason:
            afk_message += f"Reason: **{reason}**\n"
        afk_message += f"I'll let people know when they mention you.\n"
        afk_message += f"Since: <t:{int(current_time.timestamp())}:R>"

        await send_response_func(afk_message)

        # Try to change nickname
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
        await interaction.response.defer(ephemeral=False)
        await self.process_afk_set(
            interaction.user,
            reason,
            interaction.followup.send
        )

    @commands.command(name="afk", help="Set yourself as AFK with an optional reason. Usage: $afk [reason]")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = None):
        await self.process_afk_set(
            ctx.author,
            reason,
            ctx.send
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = str(message.author.id)
        user_data = self.db.find_one({"_id": user_id})

        if user_data and "afk" in user_data and not message.content.lower().startswith(f"{self.bot.command_prefix}afk"):
            # Remove AFK status
            self.db.update_one({"_id": user_id}, {"$unset": {"afk": ""}})

            try:
                if message.guild.me.guild_permissions.manage_nicknames and message.author.top_role.position < message.guild.me.top_role.position:
                    if message.author.nick and message.author.nick.startswith("[AFK]"):
                        original_nick = message.author.nick[len("[AFK] "):].strip()
                        await message.author.edit(nick=original_nick or None)
            except Exception as e:
                print(f"Failed to reset nickname: {e}")

            afk_time = user_data["afk"]["time"]
            duration = self.format_duration(datetime.utcnow() - afk_time)
            await message.channel.send(
                f"👋 Welcome back, {message.author.mention}! You were AFK for **{duration}**. Since: <t:{int(afk_time.timestamp())}:R>"
            )

        # If it's a command, skip AFK checks
        if message.content.startswith(self.bot.command_prefix):
            return

        # Only mention the first AFK user once
        afk_mentioned = set()
        for member in message.mentions:
            if member.bot or member.id in afk_mentioned:
                continue

            afk_data = self.db.find_one({"_id": str(member.id)})
            if afk_data and "afk" in afk_data:
                reason = afk_data["afk"]["reason"]
                afk_time = afk_data["afk"]["time"]
                duration = self.format_duration(datetime.utcnow() - afk_time)

                response = f"{member.mention} is currently **AFK!**\n"
                if reason:
                    response += f"With reason: **{reason}**\n"
                response += f"for **{duration}**\n"
                response += f"Since: <t:{int(afk_time.timestamp())}:R>"

                await message.channel.send(response)
                afk_mentioned.add(member.id)
                break  # Respond only once

    def cog_unload(self):
        self.client.close()
        print("AFK MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(AFK(bot))
