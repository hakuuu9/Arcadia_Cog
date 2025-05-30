import discord
from discord.ext import commands
from discord import app_commands

class Post(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(interaction: discord.Interaction):
        # Check if the user has manage_messages permission
        return interaction.user.guild_permissions.manage_messages

    @app_commands.command(name="post", description="Post a message to a channel with optional embed, image, and color.")
    @app_commands.describe(
        channel="Channel to send the message",
        message="The message content (supports server GIFs/emojis)",
        embed="Send as an embed?",
        image_url="Image URL to include in the embed or message",
        embed_color="Embed color (hex code, e.g., #ff0000)"
    )
    async def post_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        embed: bool = False,
        image_url: str = None,
        embed_color: str = "#2f3136",
    ):
        # Staff check
        if not self.is_staff(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            if embed:
                # Convert hex color string to discord.Color
                try:
                    color = discord.Color.from_str(embed_color)
                except ValueError:
                    color = discord.Color.dark_gray()

                em = discord.Embed(description=message, color=color)
                if image_url:
                    em.set_image(url=image_url)
                await channel.send(embed=em)
            else:
                content = message
                if image_url:
                    content += f"\n{image_url}"  # Include image URL inline
                await channel.send(content=content)

            await interaction.followup.send(f"✅ Message sent to {channel.mention}.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Failed to send message: `{e}`", ephemeral=True)

    def is_staff(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_messages

async def setup(bot):
    await bot.add_cog(Post(bot))
