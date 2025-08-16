import discord
from discord import app_commands
from discord.ext import commands

# The role ID for the purge command permissions
PURGE_ROLE_ID = 1347181345922748456

class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash command: /purge
    @app_commands.command(name="purge", description="Delete messages from this channel.")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_role(PURGE_ROLE_ID)
    async def purge_slash(self, interaction: discord.Interaction, amount: int):
        if not 1 <= amount <= 100:
            await interaction.response.send_message("Please choose a number between 1 and 100.", ephemeral=True)
            return

        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)

    # Prefix command: $purge
    @commands.command(name="purge", help="Delete messages from this channel.")
    @commands.has_role(PURGE_ROLE_ID)
    async def purge(self, ctx, amount: int):
        if not 1 <= amount <= 100:
            await ctx.send("Please enter a number between 1 and 100.", delete_after=5)
            return

        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🧹 Deleted {len(deleted)} messages.", delete_after=5)

    @purge_slash.error
    @purge.error
    async def purge_error(self, interaction_or_ctx, error):
        if isinstance(error, app_commands.MissingRole) or isinstance(error, commands.MissingRole):
            await interaction_or_ctx.response.send_message("You do not have the required role to use this command.", ephemeral=True)
        else:
            await interaction_or_ctx.response.send_message("An error occurred while trying to purge messages.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PurgeCog(bot))
