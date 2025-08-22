import discord
from discord.ext import commands
from discord import app_commands

POST3_ID = 1347181345922748456  # staff role ID allowed to use post3

class Post3(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        role = discord.utils.get(interaction.user.roles, id=POST3_ID)
        return role is not None

    # ========== SLASH COMMAND ==========
    @app_commands.command(
        name="post3",
        description="Post a simple embed with text, image, and optional color."
    )
    @app_commands.describe(
        channel="Channel to send the embed",
        message="Embed text (use \\n for line breaks)",
        image_url="Image URL to show inside the embed",
        embed_color="Hex color for embed (optional, e.g., #ff0000)"
    )
    async def post3_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        image_url: str,
        embed_color: str = "#2f3136"
    ):
        if not self.is_staff(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        message = message.replace("\\n", "\n")
        try:
            try:
                color = discord.Color.from_str(embed_color)
            except ValueError:
                color = discord.Color.dark_gray()

            em = discord.Embed(description=message, color=color)
            em.set_image(url=image_url)
            await channel.send(embed=em)

            await interaction.followup.send(
                f"✅ Message sent to {channel.mention}.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to send message: `{e}`", ephemeral=True
            )

    # ========== PREFIX COMMAND ==========
    @commands.command(name="post3")
    async def post3_prefix(
        self,
        ctx,
        channel: discord.TextChannel,
        *,
        args: str
    ):
        role = discord.utils.get(ctx.author.roles, id=POST3_ID)
        if role is None:
            return await ctx.send("❌ You do not have permission to use this command.", delete_after=10)

        # args format: message | image_url | embed_color
        parts = args.split("|")
        message = parts[0].strip().replace("\\n", "\n")
        image_url = parts[1].strip() if len(parts) > 1 else None
        embed_color = parts[2].strip() if len(parts) > 2 else "#2f3136"

        try:
            try:
                color = discord.Color.from_str(embed_color)
            except ValueError:
                color = discord.Color.dark_gray()

            em = discord.Embed(description=message, color=color)
            if image_url:
                em.set_image(url=image_url)
            await channel.send(embed=em)

            await ctx.send(f"✅ Message sent to {channel.mention}.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Failed to send message: `{e}`", delete_after=10)


async def setup(bot):
    await bot.add_cog(Post3(bot))
