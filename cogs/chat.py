import discord
from discord.ext import commands
from discord import app_commands

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Prefix command version
    @commands.command(name="chat", help="Send a message to a specified channel (Moderator + Manage Messages required)")
    @commands.has_permissions(manage_messages=True)
    async def chat(self, ctx, channel: discord.TextChannel, *, message: str):
        # Check Moderator role
        if not any(role.name == "Moderator" for role in ctx.author.roles):
            await ctx.send("You need the **Moderator** role to use this command.", delete_after=5)
            return

        try:
            await channel.send(message)
            await ctx.send(f"Message sent to {channel.mention}!", delete_after=5)
        except discord.Forbidden:
            await ctx.send("I don't have permission to send messages in that channel.", delete_after=5)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", delete_after=5)

    @chat.error
    async def chat_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Only staff members with **Manage Messages** permission can use this command.", delete_after=5)

    # Slash command version
    @app_commands.command(name="chat", description="Send a message to a specified channel (Moderator + Manage Messages required)")
    @app_commands.describe(channel="The channel to send the message to", message="The message content")
    async def chat_slash(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        # Check Manage Messages permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need the **Manage Messages** permission to use this command.", ephemeral=True)
            return

        # Check Moderator role
        if not any(role.name == "Moderator" for role in interaction.user.roles):
            await interaction.response.send_message("You need the **Moderator** role to use this command.", ephemeral=True)
            return

        try:
            await channel.send(message)
            await interaction.response.send_message(f"Message sent to {channel.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to send messages in that channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
