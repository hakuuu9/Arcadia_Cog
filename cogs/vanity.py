# cogs/vanity.py

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
            # Get the custom status text if it exists
            status = None
            for activity in after.activities:
                if activity.type == discord.ActivityType.custom:
                    status = activity.state
                    break

            # Get the role object from the guild
            role = member.guild.get_role(ROLE_ID)
            if role is None:
                print(f"[VanityRole] Role with ID {ROLE_ID} not found in guild {member.guild.name}.")
                return # Exit if role not found

            has_role = role in member.roles

            # Get the log channel
            channel = self.bot.get_channel(VANITY_LOG_CHANNEL_ID)
            if channel is None:
                print(f"[VanityRole] Log channel with ID {VANITY_LOG_CHANNEL_ID} not found.")
                # It's generally good to log this, but the function can still proceed
                # if the only issue is not being able to send a log message.
                # However, if logging is critical, you might consider returning here.
                # For this specific error (awaiting None), we need to ensure channel is not None
                # before attempting to send.
                pass # Continue if channel is None, but handle sending later.

            # Assign role if status contains vanity link and member does not have role
            if status and VANITY_LINK in status and not has_role:
                await member.add_roles(role)

                if channel: # Only try to send if channel is not None
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

                    await channel.send(embed=embed)

            # Remove role if status does not contain vanity link and member has role
            elif (not status or VANITY_LINK not in status) and has_role:
                await member.remove_roles(role)

                if channel: # Only try to send if channel is not None
                    embed = discord.Embed(
                        title="Vanity Role Removed",
                        description=(
                            f"The role **<@&{ROLE_ID}>** has been removed from **{member.mention}** "
                            f"as the vanity link is no longer present in their status."
                        ),
                        color=discord.Color.red()
                    )
                    embed.set_footer(text=f"Status updated for {member.name}.")

                    await channel.send(embed=embed)

        except Exception as e:
            # Fixed the incomplete print statement.
            print(f"[Error - Vanity Role Handler]: {e}")

def setup(bot):
    bot.add_cog(VanityRole(bot))