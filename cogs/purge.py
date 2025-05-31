from discord.ext import commands
from discord import app_commands
import discord

class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_moderator(self, member: discord.Member):
        return any(role.name.lower() == "moderator" for role in member.roles)

    # Slash command: /purge
    @app_commands.command(name="purge", description="Delete messages from this channel (Moderator only).")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge_slash(self, interaction: discord.Interaction, amount: int):
        if not self.is_moderator(interaction.user):
            await interaction.response.send_message("You must be a **Moderator** to use this command.", ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Please choose a number between 1 and 100.", ephemeral=True)
            return

        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)

    # Prefix command: $purge
    @commands.command(name="purge", help="Delete messages from this channel (Moderator only).")
    async def purge(self, ctx, amount: int):
        if not self.is_moderator(ctx.author):
            await ctx.send("You must be a **Moderator** to use this command.", delete_after=5)
            return
        
        if amount < 1 or amount > 100:
            await ctx.send("Please enter a number between 1 and 100.", delete_after=5)
            return

        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🧹 Deleted {len(deleted)} messages.", delete_after=5)

    @purge.error
    async def purge_error(self, ctx, error):
        await ctx.send("An error occurred while trying to purge messages.", delete_after=5)

async def setup(bot):
    await bot.add_cog(PurgeCog(bot))