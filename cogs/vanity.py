import discord
from discord.ext import commands
from config import VANITY_LINK, ROLE_ID, VANITY_LOG_CHANNEL_ID, VANITY_IMAGE_URL

class VanityRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        member = after
        try:
            status = None
            for activity in after.activities:
                if activity.type == discord.ActivityType.custom:
                    status = activity.state
                    break

            has_role = any(role.id == ROLE_ID for role in member.roles)
            role = member.guild.get_role(ROLE_ID)
            if not role:
                print(f"[VanityRole] Role ID {ROLE_ID} not found in guild {member.guild.name}")
                return

            # Role granting
            if status and VANITY_LINK in status and not has_role:
                await member.add_roles(role)

                embed = discord.Embed(
                    title="Vanity Role Granted",
                    description=(
                        f"The role **<@&{ROLE_ID}>** has been assigned to **{member.mention}** "
                        f"for including the official vanity link in their custom status.\n\n"
                        "**Privileges:**\n"
                        "• Nickname perms\n"
                        "• Image and embed link perms\n"
                        "• 1.0 XP boost\n"
                    ),
                    color=discord.Color.green()
                )
                embed.set_image(url=VANITY_IMAGE_URL)
                embed.set_footer(text=f"Status verified for {member.name}.")

                channel = self.bot.get_channel(VANITY_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(embed=embed)

            # Role removal
            elif (not status or VANITY_LINK not in status) and has_role:
                await member.remove_roles(role)

                embed = discord.Embed(
                    title="Vanity Role Removed",
                    description=(
                        f"The role **<@&{ROLE_ID}>** has been removed from **{member.mention}** "
                        f"as the vanity link is no longer present in their status."
                    ),
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Status updated for {member.name}.")

                channel = self.bot.get_channel(VANITY_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(embed=embed)

        except Exception as e:
            print(f"[Error - Vanity Role Handler]: {e}")

def setup(bot):
    bot.add_cog(VanityRole(bot))
