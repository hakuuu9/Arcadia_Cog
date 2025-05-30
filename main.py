import discord
from discord.ext import commands
from keep_alive import keep_alive
from config import BOT_TOKEN, VANITY_LINK, ROLE_ID, VANITY_LOG_CHANNEL_ID, VANITY_IMAGE_URL # <--- ADD THESE
import os
import asyncio

# --- Intents ---
# CRITICAL: These intents are required for on_presence_update to work.
intents = discord.Intents.default()
intents.message_content = True  # Needed for chat commands
intents.presences = True      # Enable presence updates
intents.members = True        # Enable member updates (needed for roles and presence)

bot = commands.Bot(command_prefix="$ ", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Error syncing slash commands: {e}')

# --- Vanity Role Logic ---
@bot.event
async def on_presence_update(before, after):
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
        channel = bot.get_channel(VANITY_LOG_CHANNEL_ID)
        if channel is None:
            print(f"[VanityRole] Log channel with ID {VANITY_LOG_CHANNEL_ID} not found.")
            # We'll continue without logging if the channel isn't found,
            # but won't attempt to send a message to a None object.
            pass

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
        print(f"[Error - Vanity Role Handler]: {e}")

# --- Main Bot Runner ---
async def main():
    # Load all cogs from /cogs (still load other cogs if you have them)
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # IMPORTANT: If you had a 'vanity.py' cog, you should remove it
            # or skip loading it here to avoid duplicate event listeners.
            if filename != "vanity.py": # Example: Skip loading if vanity.py exists
                await bot.load_extension(f"cogs.{filename[:-3]}")
    
    # Start keep-alive server (if needed)
    keep_alive()
    
    # Run the bot
    await bot.start(BOT_TOKEN)

# Run the async main() function
asyncio.run(main())