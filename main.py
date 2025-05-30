import discord
from discord.ext import commands
from keep_alive import keep_alive
import os
import asyncio

# --- Configuration Imports ---
# Make sure your config.py has these variables defined:
# BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# VANITY_LINK = "your_vanity_link_here" # e.g., "discord.gg/yourserver"
# ROLE_ID = 123456789012345678 # Replace with your Vanity Role ID
# VANITY_LOG_CHANNEL_ID = 987654321098765432 # Replace with your Log Channel ID
# VANITY_IMAGE_URL = "https://example.com/vanity_image.png" # Optional image URL
from config import (
    BOT_TOKEN,
    VANITY_LINK,
    ROLE_ID,
    VANITY_LOG_CHANNEL_ID,
    VANITY_IMAGE_URL
)

# --- Define Intents ---
# Intents are CRITICAL for your bot to receive specific events from Discord.
# - message_content: REQUIRED for prefix commands to read message content.
# - presences: REQUIRED for on_presence_update (vanity role).
# - members: REQUIRED for on_presence_update (accessing member roles/guild data).
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

# --- Initialize the Bot ---
# command_prefix defines what characters your bot will listen for as commands.
bot = commands.Bot(command_prefix="$ ", intents=intents)

# --- Bot Event: on_ready ---
# This event fires when the bot successfully connects to Discord.
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        # Sync slash commands with Discord. This is usually done on startup.
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands: {[s.name for s in synced]}')
    except Exception as e:
        print(f'Error syncing slash commands: {e}')

# --- Bot Event: on_presence_update (Vanity Role Logic) ---
# This event fires when a member's presence (status, activity) changes.
# It requires the 'presences' and 'members' intents.
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    member = after # We care about the 'after' state of the member

    # Only process if the user is not a bot to avoid issues
    if member.bot:
        return

    try:
        # Get the custom status text if it exists
        status = None
        for activity in after.activities:
            if isinstance(activity, discord.CustomActivity):
                status = activity.state
                break # Found custom status, no need to check other activities

        # Get the role object from the guild
        role = member.guild.get_role(ROLE_ID)
        if role is None:
            print(f"[VanityRole] Role with ID {ROLE_ID} not found in guild {member.guild.name}.")
            return # Cannot proceed if the role doesn't exist

        has_role = role in member.roles

        # Get the log channel
        channel = bot.get_channel(VANITY_LOG_CHANNEL_ID)
        if channel is None:
            print(f"[VanityRole] Log channel with ID {VANITY_LOG_CHANNEL_ID} not found.")
            # We'll continue without logging if the channel isn't found,
            # but won't attempt to send a message to a None object.
            pass # No 'return' here, as the core role logic can still run

        # Assign role if status contains vanity link and member does not have role
        if status and VANITY_LINK in status and not has_role:
            await member.add_roles(role)
            print(f"Assigned vanity role to {member.name} ({member.id})") # Debugging print

            if channel: # Only try to send log message if channel is valid
                embed = discord.Embed(
                    title="Vanity Role Granted",
                    description=(
                        f"The role **<@&{ROLE_ID}>** has been assigned to **{member.mention}** "
                        f"for including the official vanity link (`{VANITY_LINK}`) in their custom status.\n\n" # Added link for clarity
                        "**Privileges:**\n"
                        "• Nickname perms\n"
                        "• Image and embed link perms\n"
                        "• 1.0 XP boost\n"
                    ),
                    color=discord.Color.green()
                )
                if VANITY_IMAGE_URL: # Only set image if URL is provided
                    embed.set_image(url=VANITY_IMAGE_URL)
                embed.set_footer(text=f"Status verified for {member.name} ({member.id}).")

                await channel.send(embed=embed)

        # Remove role if status does not contain vanity link and member has role
        elif (not status or VANITY_LINK not in status) and has_role:
            await member.remove_roles(role)
            print(f"Removed vanity role from {member.name} ({member.id})") # Debugging print

            if channel: # Only try to send log message if channel is valid
                embed = discord.Embed(
                    title="Vanity Role Removed",
                    description=(
                        f"The role **<@&{ROLE_ID}>** has been removed from **{member.mention}** "
                        f"as the vanity link (`{VANITY_LINK}`) is no longer present in their status." # Added link for clarity
                    ),
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Status updated for {member.name} ({member.id}).")

                await channel.send(embed=embed)

    except discord.Forbidden:
        print(f"[VanityRole] Bot lacks permissions to manage roles for {member.name} ({member.id}).")
    except discord.HTTPException as e:
        print(f"[VanityRole] Failed to modify roles for {member.name} ({member.id}): {e}")
    except Exception as e:
        print(f"[Error - Vanity Role Handler]: {e}")

# --- Example Prefix Command (for testing) ---
@bot.command(name="ping") # Define a prefix command
async def ping_command(ctx: commands.Context):
    """Responds with Pong!"""
    await ctx.send("Pong!")
    print(f"Prefix command 'ping' executed by {ctx.author}")

# --- Example Slash Command (for testing) ---
@bot.tree.command(name="hello", description="Says hello to the user!")
async def hello_command(interaction: discord.Interaction):
    """Says hello to the user!"""
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!", ephemeral=False)
    print(f"Slash command '/hello' executed by {interaction.user}")

# --- Main Asynchronous Function to Load Cogs and Start Bot ---
async def main():
    # Load all cogs from ./cogs directory
    # IMPORTANT: If you had a 'vanity.py' cog, ensure it's removed or skipped
    # to prevent duplicate event listeners and potential errors.
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # Example: If you named your vanity cog 'vanity.py', skip it here
            if filename == "vanity.py":
                print(f"Skipping loading cogs/{filename} as its logic is in main.py.")
                continue
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load cog {filename[:-3]}: {e}")
    
    # Start the keep-alive server (if keep_alive.py is configured)
    keep_alive()
    
    # Start the bot connection to Discord
    await bot.start(BOT_TOKEN)

# --- Run the main asynchronous function ---
# This is the entry point of your bot.
if __name__ == "__main__":
    asyncio.run(main())
