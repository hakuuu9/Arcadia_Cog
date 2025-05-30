import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL # Assuming config.py is in the same directory

# No default thumbnail URL needed if we're not using it

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

    # Helper function to create AFK status embed
    def create_afk_status_embed(self, user: discord.User, reason: str = None, time: datetime = None, is_set: bool = True):
        embed = discord.Embed(
            title=f"{'😴 AFK Status Set' if is_set else '👋 Welcome Back!'}",
            color=discord.Color.green() if is_set else discord.Color.blue()
        )
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        # Removed: embed.set_thumbnail(url=DEFAULT_THUMBNAIL_URL)

        if is_set:
            description = f"You are now AFK"
            if reason:
                description += f" with reason: **{reason}**"
            description += f". I'll let people know when they mention you."
            embed.description = description
            
            # Display time since AFK for the setter
            if time:
                embed.add_field(name="AFK Since", value=f"<t:{int(time.timestamp())}:R>", inline=False)
        else:
            description = f"Welcome back, {user.mention}! Your AFK status has been cleared."
            embed.description = description
            if time:
                duration = datetime.utcnow() - time
                embed.add_field(name="You were AFK for", value=self.format_duration(duration), inline=False)
        
        embed.set_footer(text="AFK System")
        return embed

    # Helper function to create AFK mention embed
    def create_afk_mention_embed(self, afk_member: discord.Member, reason: str, afk_time: datetime):
        duration = datetime.utcnow() - afk_time
        
        embed = discord.Embed(
            title="🚫 User is AFK!",
            description=f"{afk_member.mention} is currently AFK.",
            color=discord.Color.red()
        )
        embed.set_author(name=afk_member.display_name, icon_url=afk_member.avatar.url if afk_member.avatar else afk_member.default_avatar.url)
        # Removed: embed.set_thumbnail(url=DEFAULT_THUMBNAIL_URL)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        embed.add_field(name="AFK For", value=self.format_duration(duration), inline=False)
        embed.set_footer(text="AFK System")
        return embed

    # --- Command Logic (Shared for Prefix and Slash) ---
    async def process_afk_set(self, user: discord.Member, reason: str, send_response_func):
        user_id = str(user.id)
        current_time = datetime.utcnow()

        self.db.update_one(
            {"_id": user_id},
            {"$set": {"afk": {"reason": reason, "time": current_time}}},
            upsert=True
        )

        embed = self.create_afk_status_embed(user, reason, current_time, is_set=True)
        await send_response_func(embed=embed)
        
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
        await interaction.response.defer(ephemeral=False) # Defer the response first
        await self.process_afk_set(
            interaction.user,
            reason,
            interaction.followup.send # Use followup.send for deferred responses
        )

    # --- Prefix Command: $afk ---
    @commands.command(name="afk", help="Set yourself as AFK with an optional reason. Usage: $afk [reason]")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = None):
        await self.process_afk_set(
            ctx.author,
            reason,
            ctx.send # Use ctx.send for prefix commands
        )

    # --- Listener: on_message ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages and messages from DMs
        if message.author.bot or not message.guild:
            return

        # --- Check if the author of the message is AFK (to clear their status) ---
        user_id = str(message.author.id)
        user_data = self.db.find_one({"_id": user_id})

        if user_data and "afk" in user_data:
            # Clear AFK status
            self.db.update_one({"_id": user_id}, {"$unset": {"afk": ""}})
            
            # Remove [AFK] from nickname if present
            try:
                # Check if bot has permissions to change nickname and role hierarchy allows
                if message.guild.me.guild_permissions.manage_nicknames and message.author.top_role.position < message.guild.me.top_role.position:
                    if message.author.nick and message.author.nick.startswith("[AFK]"):
                        # Restore original nickname (remove "[AFK] ")
                        original_nick = message.author.nick[len("[AFK] "):].strip()
                        await message.author.edit(nick=original_nick if original_nick else None) # Set to None to clear custom nick
                elif not message.guild.me.guild_permissions.manage_nicknames:
                    print(f"Bot lacks 'manage_nicknames' permission to clear AFK nickname in guild {message.guild.name}")
                elif message.author.top_role.position >= message.guild.me.top_role.position:
                    print(f"Bot cannot change nickname for {message.author.display_name} due to role hierarchy.")

            except discord.Forbidden:
                print(f"Bot lacks permissions to change nickname for {message.author.name} in {message.guild.name}.")
            except Exception as e:
                print(f"An error occurred while clearing AFK nickname: {e}")

            # Send welcome back embed
            afk_time = user_data["afk"]["time"]
            embed = self.create_afk_status_embed(message.author, time=afk_time, is_set=False)
            await message.channel.send(embed=embed)
            
            return # Don't process mentions if the author just came back from AFK

        # --- Check for mentions of AFK users ---
        # Don't process commands here. That's handled by bot.process_commands() in main.py
        # We only care about mentions within non-command messages.
        if message.content.startswith(self.bot.command_prefix):
             return # Ignore if it's a command, let bot.process_commands handle it.

        for member in message.mentions:
            if member.bot: # Don't check if another bot is AFK
                continue

            member_id = str(member.id)
            afk_data = self.db.find_one({"_id": member_id})

            if afk_data and "afk" in afk_data:
                reason = afk_data["afk"]["reason"]
                afk_time = afk_data["afk"]["time"]
                
                embed = self.create_afk_mention_embed(member, reason, afk_time)
                await message.channel.send(embed=embed)
                # Only send one AFK response per message for mentioned users.
                # If you want to notify for ALL mentioned AFK users, remove this return.
                return 

    def cog_unload(self):
        self.client.close()
        print("AFK MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(AFK(bot))
