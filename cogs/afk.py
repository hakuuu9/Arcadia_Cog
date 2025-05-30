import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL # Assuming config.py is in the same directory

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users # Using the 'users' collection for AFK data
        print("AFK Cog initialized and connected to MongoDB.")

    # Helper function to format duration string
    def format_duration(self, duration: timedelta) -> str:
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        
        if not parts: # If less than a minute
            return "a few seconds"
        
        return ", ".join(parts) # Join with comma and space

    # --- Command Logic (Shared for Prefix and Slash) ---
    async def process_afk_set(self, user: discord.Member, reason: str, send_response_func):
        user_id = str(user.id)
        current_time = datetime.utcnow()

        self.db.update_one(
            {"_id": user_id},
            {"$set": {"afk": {"reason": reason, "time": current_time}}},
            upsert=True
        )

        # CORRECTED: AFK message format to include "Since:" time
        afk_message = f"You are now **AFK!**\n"
        if reason:
            afk_message += f"Reason: **{reason}**\n"
        afk_message += f"I'll let people know when they mention you.\n"
        afk_message += f"Since: <t:{int(current_time.timestamp())}:R>" # Add this line

        await send_response_func(afk_message)
        
        # Optionally, change nickname to indicate AFK
        try:
            if user.guild.me.guild_permissions.manage_nicknames and user.top_role.position < user.guild.me.top_role.position:
                if not user.nick or not user.nick.startswith("[AFK]"):
                    original_nick = user.nick if user.nick else user.name
                    await user.edit(nick=f"[AFK] {original_nick}")
            elif not user.guild.me.guild_permissions.manage_nicknames:
                print(f"Bot lacks 'manage_nicknames' permission in guild {user.guild.name} to set AFK nick.")
            elif user.top_role.position >= user.guild.me.top_role.position:
                print(f"Bot cannot change nickname for {user.display_name} due to role hierarchy.")
        except discord.Forbidden:
            print(f"Bot lacks permissions to change nickname for {user.display_name} in {user.guild.name}.")
        except Exception as e:
            print(f"An error occurred while changing nickname for {user.display_name}: {e}")

    # --- Slash Command: /afk ---
    @app_commands.command(name="afk", description="Set yourself as AFK with an optional reason.")
    @app_commands.describe(reason="The reason for being AFK (optional).")
    async def afk_slash(self, interaction: discord.Interaction, reason: str = None):
        await interaction.response.defer(ephemeral=False) 
        await self.process_afk_set(
            interaction.user,
            reason,
            interaction.followup.send
        )

    # --- Prefix Command: $afk ---
    @commands.command(name="afk", help="Set yourself as AFK with an optional reason. Usage: $afk [reason]")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = None):
        await self.process_afk_set(
            ctx.author,
            reason,
            ctx.send
        )

    # --- Listener: on_message ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = str(message.author.id)
        user_data = self.db.find_one({"_id": user_id})

        # Check if the author is AFK BUT *not* sending an AFK command
        if user_data and "afk" in user_data and not message.content.startswith(self.bot.command_prefix + "afk"):
            # Clear AFK status
            self.db.update_one({"_id": user_id}, {"$unset": {"afk": ""}})
            
            # Remove [AFK] from nickname if present
            try:
                if message.guild.me.guild_permissions.manage_nicknames and message.author.top_role.position < message.guild.me.top_role.position:
                    if message.author.nick and message.author.nick.startswith("[AFK]"):
                        original_nick = message.author.nick[len("[AFK] "):].strip()
                        await message.author.edit(nick=original_nick if original_nick else None)
                elif not message.guild.me.guild_permissions.manage_nicknames:
                    print(f"Bot lacks 'manage_nicknames' permission to clear AFK nickname in guild {message.guild.name}")
                elif message.author.top_role.position >= message.guild.me.top_role.position:
                    print(f"Bot cannot change nickname for {message.author.display_name} due to role hierarchy.")

            except discord.Forbidden:
                print(f"Bot lacks permissions to change nickname for {message.author.name} in {message.guild.name}.")
            except Exception as e:
                print(f"An error occurred while clearing AFK nickname: {e}")

            afk_time = user_data["afk"]["time"]
            duration_str = self.format_duration(datetime.utcnow() - afk_time)
            # Corrected: Added "Since:" time for welcome back message
            await message.channel.send(f"👋 Welcome back, {message.author.mention}! You were AFK for **{duration_str}**. Since: <t:{int(afk_time.timestamp())}:R>")
            
            return

        if message.content.startswith(self.bot.command_prefix):
             return

        for member in message.mentions:
            if member.bot:
                continue

            member_id = str(member.id)
            afk_data = self.db.find_one({"_id": member_id})

            if afk_data and "afk" in afk_data:
                reason = afk_data["afk"]["reason"]
                afk_time = afk_data["afk"]["time"]
                
                duration_str = self.format_duration(datetime.utcnow() - afk_time)
                
                # Corrected: Added "Since:" time for AFK mention message
                response = f"{member.mention} is currently **AFK!**\n"
                if reason:
                    response += f"With reason: **{reason}**\n"
                response += f"for **{duration_str}**\n"
                response += f"Since: <t:{int(afk_time.timestamp())}:R>" # Add this line
                
                await message.channel.send(response)
                return 

    def cog_unload(self):
        self.client.close()
        print("AFK MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(AFK(bot))
