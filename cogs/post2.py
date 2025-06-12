import discord
from discord.ext import commands
from discord import app_commands

class Post2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_messages

    @commands.hybrid_command(
        name="post2",
        description="Send a styled message or embed with optional image, footer, and color."
    )
    @app_commands.describe(
        channel="Where to post the message",
        embed="Send as embed?",
        message="Message content (supports Discord formatting and emojis)",
        image_url="Image URL (optional, for embed)",
        footer_text="Footer text (optional)",
        embed_color="Embed color in hex (optional, e.g. #ff0000)"
    )
    async def post2(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        embed: bool,
        message: str,
        image_url: str = None,
        footer_text: str = None,
        embed_color: str = "#2f3136"
    ):
        interaction = getattr(ctx, "interaction", None)

        # Permission check
        if interaction:
            if not self.is_staff(interaction):
                return await interaction.response.send_message("❌ You lack permission to use this command.", ephemeral=True)
            await interaction.response.defer(ephemeral=True)
        else:
            if not ctx.author.guild_permissions.manage_messages:
                return await ctx.send("❌ You lack permission to use this command.")
            await ctx.typing()

        try:
            if embed:
                try:
                    color = discord.Color.from_str(embed_color)
                except ValueError:
                    color = discord.Color.dark_gray()

                em = discord.Embed(description=message, color=color)

                if image_url:
                    em.set_image(url=image_url)

                if footer_text:
                    em.set_footer(text=footer_text)

                await channel.send(embed=em)
            else:
                final_msg = message
                if image_url:
                    final_msg += f"\n{image_url}"
                await channel.send(content=final_msg)

            success = f"✅ Message sent to {channel.mention}."
            if interaction:
                await interaction.followup.send(success, ephemeral=True)
            else:
                await ctx.send(success)

        except Exception as e:
            error = f"❌ Failed to send message: `{e}`"
            if interaction:
                await interaction.followup.send(error, ephemeral=True)
            else:
                await ctx.send(error)

async def setup(bot):
    await bot.add_cog(Post2(bot))
