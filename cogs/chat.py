import discord
from discord.ext import commands
from discord import app_commands

# The ID of the role that has permission to use the chat command.
CHAT_ROLE_ID = 1347181345922748456

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="chat", description="Send a message to a specified channel.")
    @app_commands.describe(channel="The channel to send the message to", message="The message content")
    @commands.has_role(CHAT_ROLE_ID)
    @commands.has_permissions(manage_messages=True)
    async def chat(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        # The 'ctx' object in a hybrid command can be either a Context or an Interaction.
        # We check the type to handle the response appropriately.
        if isinstance(ctx, commands.Context):
            # This is a prefix command
            try:
                await channel.send(message)
                await ctx.send(f"✅ Message sent to {channel.mention}!", delete_after=5)
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to send messages in that channel.", delete_after=5)
        else:
            # This is a slash command (an Interaction object)
            try:
                await channel.send(message)
                await ctx.response.send_message(f"✅ Message sent to {channel.mention}!", ephemeral=True)
            except discord.Forbidden:
                await ctx.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
            except Exception as e:
                await ctx.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    @chat.error
    async def chat_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            message = "❌ You must have the **Manage Messages** permission to use this command."
        elif isinstance(error, commands.MissingRole):
            message = "❌ You do not have the required role to use this command."
        else:
            message = "❌ An unexpected error occurred."
            
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(message, ephemeral=True)
        else:
            await ctx.send(message, delete_after=5)

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
