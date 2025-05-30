from discord import app_commands
from discord.ext import commands
import discord

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    STAFF_ROLE_NAME = "Moderator"
    STAFF_ROLE_ID = 1347181345922748456
    LOG_CHANNEL_ID = 1364839238960549908

    @commands.hybrid_command(name="role", description="Grant or revoke a role from a member.")
    @app_commands.describe(member="The member to give/revoke the role to/from", role_input="The role (name, ID, or mention)")
    async def role(self, ctx: commands.Context, member: discord.Member = None, *, role_input: str = None):
        staff_role = discord.utils.get(ctx.guild.roles, id=self.STAFF_ROLE_ID)

        if not staff_role or staff_role.id != self.STAFF_ROLE_ID:
            await ctx.send("❌ You don't have the required staff role.")
            return

        if staff_role not in ctx.author.roles:
            await ctx.send("❌ You don't have permission to use this command.")
            return

        if not member or not role_input:
            await ctx.send("Usage: `/role @member rolename/roleid` or `$role @member rolename/roleid`")
            return

        # Case-insensitive and format-flexible role resolution
        role = None
        if role_input.isdigit():
            role = ctx.guild.get_role(int(role_input))
        elif role_input.startswith("<@&") and role_input.endswith(">"):
            role_id = int(role_input[3:-1])
            role = ctx.guild.get_role(role_id)
        else:
            role = discord.utils.find(lambda r: r.name.lower() == role_input.lower(), ctx.guild.roles)

        if not role:
            await ctx.send("❌ Couldn't find that role.")
            return

        granted_emoji = "<a:GC_Fire:1348482027447386116>"
        revoked_emoji = "<a:calcifer:1348189333542404106>"

        embed = discord.Embed(
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url="https://i.imgur.com/JxsCfCe.gif")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        if role in member.roles:
            await member.remove_roles(role)
            embed.title = f"{revoked_emoji} Role Revoked"
            embed.description = (
                f"The role **{role.name}** has been revoked from {member.mention}.\n"
                f"All permissions associated with this role have been removed."
            )
        else:
            await member.add_roles(role)
            embed.title = f"{granted_emoji} Role Granted"
            embed.description = (
                f"{member.mention} has been granted the **{role.name}** role.\n"
                f"Relevant permissions are now active."
            )

        await ctx.send(embed=embed)

        log_channel = ctx.guild.get_channel(self.LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleManager(bot))
