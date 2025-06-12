import discord
from discord.ext import commands
from discord import app_commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    @app_commands.command(
        name="say",
        description="Make the bot say a message (supports emojis and mentions). Admins only."
    )
    @app_commands.describe(
        channel="Channel to send the message",
        message="The message content (you can mention users/roles and use emojis)"
    )
    async def say_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
    ):
        if not self.is_admin(interaction):
            return await interaction.response.send_message(
                "❌ This command is only for admins.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            # Allow mentions in the message
            allowed_mentions = discord.AllowedMentions(
                users=True,
                roles=True,
                everyone=True
            )

            await channel.send(content=message, allowed_mentions=allowed_mentions)

            await interaction.followup.send(
                f"✅ Message sent to {channel.mention}.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to send message: `{e}`", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Say(bot))
