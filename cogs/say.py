import discord
from discord.ext import commands
from discord import app_commands

say_mod_id = 1347181345922748456  # Authorized user ID

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == say_mod_id

    @app_commands.command(
        name="say",
        description="Make the bot say a message (supports mentions and emojis)."
    )
    @app_commands.describe(
        channel="Channel to send the message",
        message="The message content (can include mentions and server emojis)"
    )
    async def say_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
    ):
        if not self.is_authorized(interaction):
            return await interaction.response.send_message(
                "❌ You are not allowed to use this command.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
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
