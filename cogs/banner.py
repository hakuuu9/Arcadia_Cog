import discord
from discord.ext import commands
from discord import app_commands

class Banner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="banner")
    async def banner_text(self, ctx, user: discord.User = None):
        user = user or ctx.author
        await self.send_banner(ctx, user)

    @app_commands.command(name="banner", description="Show the banner of a user (if available)")
    @app_commands.describe(user="The user to get the banner of")
    async def banner_slash(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        await self.send_banner(interaction, user)

    async def send_banner(self, ctx_or_interaction, user: discord.User):
        # Fetch user profile to access banner
        user_profile = await self.bot.fetch_user(user.id)
        banner_url = user_profile.banner.url if user_profile.banner else None
        accent = user_profile.accent_color or discord.Color.blurple()

        if not banner_url:
            message = f"❌ {user.name} has no banner set."
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(message)
            else:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(message)
                else:
                    await ctx_or_interaction.response.send_message(message)
            return

        embed = discord.Embed(
            title=f"🌇 Banner of {user.name}",
            color=accent
        )
        embed.set_image(url=banner_url)
        embed.set_footer(text=f"Requested by {ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author}")

        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
        else:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Banner(bot))
