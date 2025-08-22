import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Constants for the custom emoji and embed color
AVATAR_EMOJI_ID = 1408388366101385217
EMBED_COLOR = 0xE1D3C4  # Beige color

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_avatar(self, ctx_or_interaction, user: discord.User):
        """A single function to handle sending the avatar embed for both slash and prefix commands."""
        # Get the URL for the user's avatar, ensuring it's a large size
        avatar_url = user.display_avatar.replace(size=1024).url

        # Create the embed with the custom emoji, title, and color
        embed = discord.Embed(
            title=f"<a:avatar:{AVATAR_EMOJI_ID}> The requested Avatar of {user.display_name}",
            color=EMBED_COLOR
        )
        embed.set_image(url=avatar_url)

        # Add the current date and time to the embed footer
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        embed.set_footer(text=f"Requested on {current_time}")

        # Send the embed based on the type of command used (prefix or slash)
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            # For slash commands, check if the interaction has already been responded to
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)

    @commands.command(name="avatar", help="Show the avatar of you or someone else.")
    async def avatar_text(self, ctx, user: discord.User = None):
        """Prefix command for getting a user's avatar."""
        user = user or ctx.author
        await self.send_avatar(ctx, user)

    @app_commands.command(name="avatar", description="Show the avatar of you or someone else.")
    @app_commands.describe(user="The user to get the avatar of.")
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Slash command for getting a user's avatar."""
        user = user or interaction.user
        await self.send_avatar(interaction, user)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
