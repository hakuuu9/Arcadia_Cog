import discord
from discord.ext import commands
from discord import app_commands

POST2_ID = 1347181345922748456  # moderator role ID allowed to use post2

class Post2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        role = discord.utils.get(interaction.user.roles, id=POST2_ID)
        return role is not None

    @app_commands.command(
        name="post2",
        description="Post a message to a channel with embed option, image, footer, and color."
    )
    @app_commands.describe(
        channel="Channel to send the message",
        embed="Send as an embed?",
        message="Message content (use \\n for line breaks)",
        image_url="Image URL to show inside the embed (optional)",
        footer="Footer text (optional, use \\n for line breaks)",
        embed_color="Hex color for embed (optional, e.g., #ff0000)"
    )
    async def post2_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        embed: bool,
        message: str,
        image_url: str = None,
        footer: str = None,
        embed_color: str = "#2f3136",
    ):
        if not self.is_staff(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        message = message.replace("\\n", "\n")
        if footer:
            footer = footer.replace("\\n", "\n")

        try:
            if embed:
                try:
                    color = discord.Color.from_str(embed_color)
                except ValueError:
                    color = discord.Color.dark_gray()

                em = discord.Embed(description=message, color=color)
                if footer:
                    em.set_footer(text=footer)
                if image_url:
                    em.set_image(url=image_url)
                await channel.send(embed=em)
            else:
                content = message
                if image_url:
                    content += f"\n{image_url}"
                await channel.send(content=content)

            await interaction.followup.send(
                f"✅ Message sent to {channel.mention}.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to send message: `{e}`", ephemeral=True
            )

    @commands.command(name="post2")
    async def post2_prefix(
        self,
        ctx,
        channel: discord.TextChannel,
        embed: bool,
        *,
        args: str
    ):
        role = discord.utils.get(ctx.author.roles, id=POST2_ID)
        if role is None:
            return await ctx.send("❌ You do not have permission to use this command.", delete_after=10)

        parts = args.split("|")
        message = parts[0].strip().replace("\\n", "\n")
        image_url = parts[1].strip() if len(parts) > 1 else None
        footer = parts[2].strip().replace("\\n", "\n") if len(parts) > 2 else None
        embed_color = parts[3].strip() if len(parts) > 3 else "#2f3136"

        try:
            if embed:
                try:
                    color = discord.Color.from_str(embed_color)
                except ValueError:
                    color = discord.Color.dark_gray()

                em = discord.Embed(description=message, color=color)
                if footer:
                    em.set_footer(text=footer)
                if image_url:
                    em.set_image(url=image_url)
                await channel.send(embed=em)
            else:
                content = message
                if image_url:
                    content += f"\n{image_url}"
                await channel.send(content=content)

            await ctx.send(f"✅ Message sent to {channel.mention}.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Failed to send message: `{e}`", delete_after=10)

async def setup(bot):
    await bot.add_cog(Post2(bot))
