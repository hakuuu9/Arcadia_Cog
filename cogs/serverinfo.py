import discord
from discord.ext import commands
from discord import app_commands
import datetime

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_time(self, dt):
        return dt.strftime("%B %d, %Y")

    # PREFIX COMMAND
    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(
            title=f"🌐 Server Info: {guild.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)

        embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)

        boost_level = f"Level {guild.premium_tier}" if guild.premium_tier else "None"
        embed.add_field(name="🚀 Boost Level", value=boost_level, inline=True)

        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="📚 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)

        embed.add_field(name="🌟 Emojis", value=len(guild.emojis), inline=True)

        created = self.format_time(guild.created_at)
        embed.add_field(name="📅 Created On", value=created, inline=False)

        embed.set_footer(text=f"Guild ID: {guild.id} | Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # SLASH COMMAND
    @app_commands.command(name="serverinfo", description="Show info about this server")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=f"🌐 Server Info: {guild.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)

        embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)

        boost_level = f"Level {guild.premium_tier}" if guild.premium_tier else "None"
        embed.add_field(name="🚀 Boost Level", value=boost_level, inline=True)

        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="📚 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)

        embed.add_field(name="🌟 Emojis", value=len(guild.emojis), inline=True)

        created = self.format_time(guild.created_at)
        embed.add_field(name="📅 Created On", value=created, inline=False)

        embed.set_footer(text=f"Guild ID: {guild.id} | Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
