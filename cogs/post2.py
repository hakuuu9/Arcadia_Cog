import discord
from discord.ext import commands
from discord import app_commands

class Post2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Only allow members with Manage Messages
    def is_staff(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_messages

    @commands.hybrid_command(
        name="post2",
        description="Send a message with optional embed, image, footer, and embed color."
    )
    @app_commands.describe(
        channel="Channel to send the message",
        embed="Send as an embed?",
        message="Main message content (supports mentions/emojis)",
        image_url="Optional image URL (will appear in embed)",
        footer_text="Optional footer text below image",
        embed_color="Optional hex color (e.g., #ff5733)"
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
        # Slash or prefix?
        interaction = getattr(ctx, "interaction", None)
        if interaction and not self.is_staff(interaction):
            return await ctx.send("❌ You do not have permission to use this command.", ephemeral=True)

        if not interaction and not ctx.author.guild_permissions.manage_messages:
            return await ctx.send("❌ You do not have permission to use this command.")

        await ctx.defer(ephemeral=True) if interaction else None

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
                content = message
                if image_url:
                    content += f"\n{image_url}"
                await channel.send(content=content)

            confirmation = f"✅ Message sent to {channel.mention}."
            await (ctx.send(confirmation, ephemeral=True) if interaction else ctx.send(confirmation))

        except Exception as e:
            error_msg = f"❌ Failed to send message: `{e}`"
            await (ctx.send(error_msg, ephemeral=True) if interaction else ctx.send(error_msg))

async def setup(bot):
    await bot.add_cog(Post2(bot))
