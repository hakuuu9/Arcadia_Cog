import discord
from discord.ext import commands
from discord import app_commands
import random

class Kiss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kiss_gifs = [
            "https://tenor.com/bWFDV.gif",
            "https://tenor.com/eaJBn7UpGFt.gif",
            "https://tenor.com/eHuKozPgugX.gif",
            "https://tenor.com/jRVsCzxMYlx.gif",
            "https://tenor.com/hNbDPWQGtfW.gif",
            "https://tenor.com/jKGRdRScSTC.gif",
            "https://tenor.com/b1Ds9.gif",
        ]

    # PREFIX COMMAND
    @commands.command(name="kiss")
    async def kiss(self, ctx, member: discord.Member = None):
        if member is None:
            return await ctx.send("❌ Please mention someone to kiss.")
        gif = random.choice(self.kiss_gifs)

        await ctx.send(f"💋 {ctx.author.mention} kissed {member.mention} ❤️\n{gif}")

    # SLASH COMMAND
    @app_commands.command(name="kiss", description="Kiss someone with an anime gif.")
    @app_commands.describe(member="The member you want to kiss")
    async def kiss_slash(self, interaction: discord.Interaction, member: discord.Member):
        gif = random.choice(self.kiss_gifs)

        await interaction.response.send_message(f"💋 {interaction.user.mention} kissed {member.mention} ❤️\n{gif}")

async def setup(bot):
    await bot.add_cog(Kiss(bot))
