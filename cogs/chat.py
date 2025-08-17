import discord
from discord.ext import commands
from discord import app_commands

# The ID of the role that has permission to use the chat command.
CHAT_ROLE_ID = 1347181345922748456

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # This decorator checks for the specific role ID.
    @commands.has_role(CHAT_ROLE_ID)
    # This decorator checks for the manage_messages permission.
    @commands.has_permissions(manage_messages=True)
    @commands.command(name="chat", help="Send a message to a specified channel.")
    async def chat(self, ctx, channel: discord.TextChannel, *, message: str):
        try:
            await channel.send(message)
            await ctx.send(f"✅ Message sent to {channel.mention}!", delete_after=5)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to send messages in that channel.", delete_after=5)
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}", delete_after=5)

    # We'll use a single error handler for both the slash and prefix commands
    # for a more unified and cleaner codebase.
    @commands.hybrid_command(name="chat", description="Send a message to a specified channel.")
    @app_commands.describe(channel="The channel to send the message to", message="The message content")
    @app_commands.checks.has_role(CHAT_ROLE_ID)
    @app_commands.default_permissions(manage_messages=True)
    async def chat_slash(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        try:
            await channel.send(message)
            await interaction.response.send_message(f"✅ Message sent to {channel.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    @chat.error
    @chat_slash.error
    async def chat_error(self, interaction_or_ctx, error):
        if isinstance(error, commands.MissingPermissions) or isinstance(error, app_commands.MissingPermissions):
            # The check `commands.has_permissions` is still a good safety measure.
            message = "❌ You must have the **Manage Messages** permission to use this command."
        elif isinstance(error, commands.MissingRole) or isinstance(error, app_commands.MissingRole):
            # This handles the role ID check, which is what the user asked for.
            message = "❌ You do not have the required role to use this command."
        else:
            message = "❌ An unexpected error occurred."

        # Send the response ephemerally for slash commands.
        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.send_message(message, ephemeral=True)
        # Send a regular message for prefix commands.
        else:
            await interaction_or_ctx.send(message, delete_after=5)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
