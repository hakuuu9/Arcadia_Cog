import discord
from discord.ext import commands
from discord import app_commands

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="avatar")
    async def avatar_text(self, ctx, user: discord.User = None):
        user = user or ctx.author
        await self.send_avatar(ctx, user)

    @app_commands.command(name="avatar", description="Show the avatar of you or someone else")
    @app_commands.describe(user="The user to get the avatar of")
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        await self.send_avatar(interaction, user)

    async def send_avatar(self, ctx_or_interaction, user: discord.User):
        avatar_url = user.display_avatar.replace(size=1024).url
        accent = user.accent_color or discord.Color.blurple()

        embed = discord.Embed(
            title=f"🖼️ Avatar of {user}",
            color=accent
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by {ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author}")
        embed.set_thumbnail(url=avatar_url)

        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
