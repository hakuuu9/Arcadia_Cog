import discord
from discord import app_commands
from discord.ext import commands

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Replace with the actual ID for the role that can use this command
    ROLE_ROLES_ID = 1347181345922748456
    LOG_CHANNEL_ID = 1364839238960549908

    @commands.hybrid_command(name="role", description="Grant or revoke a role from a member.")
    @app_commands.describe(member="The member to give/revoke the role to/from", role_input="The role (name, ID, or mention)")
    @commands.has_role(ROLE_ROLES_ID)
    async def role(self, ctx: commands.Context, member: discord.Member, *, role_input: str):
        # We can remove the manual role checks because the decorator handles it.
        if not member or not role_input:
            await ctx.send("Usage: `/role @member rolename/roleid` or `$role @member rolename/roleid`")
            return

        # Case-insensitive and format-flexible role resolution
        role = None
        if role_input.isdigit():
            role = ctx.guild.get_role(int(role_input))
        elif role_input.startswith("<@&") and role_input.endswith(">"):
            try:
                role_id = int(role_input[3:-1])
                role = ctx.guild.get_role(role_id)
            except (ValueError, IndexError):
                pass  # Handle cases where the mention format is invalid
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
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1370401173017722922/1370404097987182763/IMG_0702.gif")
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

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingRole) or isinstance(error, app_commands.MissingRole):
            await ctx.send("❌ You do not have the required role to use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid member or role provided.")
        else:
            await ctx.send("An error occurred while trying to manage roles.")

async def setup(bot):
    await bot.add_cog(RoleManager(bot))

---
