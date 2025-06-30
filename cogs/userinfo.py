import discord
from discord.ext import commands
from discord import app_commands

STATUS_EMOJIS = {
    discord.Status.online: "🟢 Online",
    discord.Status.idle: "🌙 Idle",
    discord.Status.dnd: "⛔ Do Not Disturb",
    discord.Status.offline: "⚫ Offline/Invisible"
}

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
}

class ProfileCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profilecard")
    async def profilecard_text(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = await self.create_profile_embed(member)
        await ctx.send(embed=embed)

    @app_commands.command(name="profilecard", description="Show a user profile card")
    @app_commands.describe(member="The member to show the profile card for (optional)")
    async def profilecard_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = await self.create_profile_embed(member)
        await interaction.response.send_message(embed=embed)

    async def create_profile_embed(self, member: discord.Member):
        embed = discord.Embed(
            title=f"{member.display_name}'s Profile Card",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        # Basic Info
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown", inline=True)

        # Roles except @everyone
        roles = ", ".join(role.mention for role in member.roles if role.name != "@everyone") or "None"
        embed.add_field(name="Roles", value=roles, inline=False)

        # Status
        status_text = STATUS_EMOJIS.get(member.status, "Unknown")
        embed.add_field(name="Status", value=status_text, inline=True)

        # Activity (if any)
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

        # Optional: add footer or description
        embed.set_footer(text=f"Profile card requested by {member.display_name}", icon_url=member.avatar.url if member.avatar else None)

        return embed

async def setup(bot):
    await bot.add_cog(ProfileCard(bot))
