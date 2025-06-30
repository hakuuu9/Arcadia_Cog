import discord
from discord.ext import commands
from discord import app_commands

# Map Discord status enums to readable strings with emojis
STATUS_EMOJIS = {
    discord.Status.online: "🟢 Online",
    discord.Status.idle: "🌙 Idle",
    discord.Status.dnd: "⛔ Do Not Disturb",
    discord.Status.offline: "⚫ Offline/Invisible"
}

# Map some common user badges (flags) to readable names and emojis
BADGE_EMOJIS = {
    "staff": "👮 Discord Staff",
    "partner": "🤝 Discord Partner",
    "hypesquad": "🎉 HypeSquad Events",
    "bug_hunter": "🐞 Bug Hunter",
    "bug_hunter_level_2": "🐞 Bug Hunter Level 2",
    "verified_bot_developer": "🤖 Verified Bot Developer",
    "early_supporter": "💖 Early Supporter",
    "verified_bot": "✅ Verified Bot",
    "discord_certified_moderator": "🛡️ Certified Moderator",
    "premium_subscriber": "🚀 Nitro Subscriber",
    # Add more if you want
}

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo_text(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = await self.create_user_embed(member)
        await ctx.send(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a user")
    @app_commands.describe(member="The member to get info for (optional)")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = await self.create_user_embed(member)
        await interaction.response.send_message(embed=embed)

    async def create_user_embed(self, member: discord.Member):
        embed = discord.Embed(
            title=f"User Info - {member}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC") if member.joined_at else "Unknown", inline=False)

        # Roles except @everyone
        roles = ", ".join(role.mention for role in member.roles if role.name != "@everyone") or "None"
        embed.add_field(name="Roles", value=roles, inline=False)

        # Status
        status_text = STATUS_EMOJIS.get(member.status, "Unknown")
        embed.add_field(name="Status", value=status_text, inline=True)

        # Custom activity (if any)
        activity = None
        for act in member.activities:
            if isinstance(act, discord.CustomActivity) and act.state:
                activity = f"Custom Status: {act.state}"
                break
            elif isinstance(act, discord.Game):
                activity = f"Playing {act.name}"
                break
            elif isinstance(act, discord.Streaming):
                activity = f"Streaming [{act.name}]({act.url})"
                break
            elif isinstance(act, discord.Listening):
                activity = f"Listening to {act.title} by {act.artist}"
                break
            elif isinstance(act, discord.Watching):
                activity = f"Watching {act.title}"
                break
        if activity:
            embed.add_field(name="Activity", value=activity, inline=False)

        # Badges
        flags = member.public_flags
        badges = []
        for badge_attr, badge_name in BADGE_EMOJIS.items():
            if getattr(flags, badge_attr, False):
                badges.append(badge_name)
        embed.add_field(name="Badges", value=", ".join(badges) if badges else "None", inline=False)

        embed.set_footer(text=f"Requested by {member.display_name}", icon_url=member.avatar.url if member.avatar else None)
        return embed

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
