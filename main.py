import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive # Assuming keep_alive.py is in the same directory
# Make sure these are defined in your config.py
from config import BOT_TOKEN, VANITY_LINK, ROLE_ID, VANITY_LOG_CHANNEL_ID, VANITY_IMAGE_URL

# --- 1. Define Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

# --- 2. Initialize the Bot ---
bot = commands.Bot(command_prefix="$", intents=intents) # Prefix is now just "$"

# --- 3. Bot Events ---

@bot.event
async def on_ready():
    """
    Called when the bot is ready and connected to Discord.
    Attempts to sync slash commands.
    """
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands globally')
    except Exception as e:
        print(f'Error syncing slash commands: {e}')

# --- THE CRUCIAL CHANGE: REMOVE THE ENTIRE on_message BLOCK FROM HERE ---
# @bot.event
# async def on_message(message):
#     """
#     Handles all incoming messages. This is required to process prefix commands
#     if you have ANY other @bot.event listeners that might interfere.
#     """
#     # Ignore messages from the bot itself to prevent infinite loops
#     if message.author == bot.user:
#         return
#
#     # This line tells the bot to process any commands found in the message
#     # using its registered prefixes.
#     await bot.process_commands(message)
# --- END OF REMOVED BLOCK ---

# --- Vanity Role Logic (Moved from Cog, kept in main.py) ---
@bot.event
async def on_presence_update(before, after):
    """
    Monitors user presence for custom status changes to assign/remove vanity roles.
    """
    member = after
    
    # Ignore bots to prevent self-triggering or issues with other bots
    if member.bot:
        return

    try:
        # Get the custom status text if it exists
        status = None
        for activity in after.activities:
            if activity.type == discord.ActivityType.custom:
                status = activity.state
                break

        # Get the role object from the guild
        # Use member.guild.get_role to get the role by ID
        role = member.guild.get_role(ROLE_ID)
        if role is None:
            print(f"[VanityRole] Role with ID {ROLE_ID} not found in guild {member.guild.name}.")
            return # Exit if the role isn't found, as we can't proceed without it.

        # Check if the member currently has the role
        has_role = role in member.roles

        # Get the log channel
        channel = bot.get_channel(VANITY_LOG_CHANNEL_ID)
        if channel is None:
            print(f"[VanityRole] Log channel with ID {VANITY_LOG_CHANNEL_ID} not found.")
            # It's okay to continue if the log channel isn't found, we just won't send logs.
            # We explicitly check 'if channel:' before sending messages.
            pass

        # --- Logic for Assigning Role ---
        # If status contains vanity link AND member does NOT have the role
        if status and VANITY_LINK in status and not has_role:
            await member.add_roles(role)
            print(f"[VanityRole] Granted role to {member.display_name} for status: '{status}'")

            if channel: # Only send embed if the log channel was found
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

        # --- Logic for Removing Role ---
        # If status does NOT contain vanity link AND member HAS the role
        elif (not status or VANITY_LINK not in status) and has_role:
            await member.remove_roles(role)
            print(f"[VanityRole] Removed role from {member.display_name} as vanity link is gone.")

            if channel: # Only send embed if the log channel was found
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
        # Catch any errors during the presence update handling
        print(f"[Error - Vanity Role Handler]: {e}")


# --- 5. Example Prefix Commands ---
# These are just examples. Your actual commands would go here or in other cogs.

@bot.command(name="ping", help="Responds with Pong! (Prefix Command)")
async def ping_command(ctx):
    """A simple prefix command that responds with 'Pong!'"""
    await ctx.send("Pong!")

@bot.command(name="hello", help="Greets the user (Prefix Command)")
async def hello_command(ctx):
    """A prefix command that greets the user."""
    await ctx.send(f"Hello, {ctx.author.display_name}!")

# --- 6. Example Slash Commands ---
# These are just examples. Your actual slash commands would go here or in other cogs.

@bot.tree.command(name="sayhi", description="Says hi using a slash command!")
async def sayhi_slash(interaction: discord.Interaction):
    """A simple slash command that says hi."""
    await interaction.response.send_message(f"Hi, {interaction.user.display_name}!")

@bot.tree.command(name="echo", description="Echoes your message (Slash Command)")
@discord.app_commands.describe(message="The message to echo back")
async def echo_slash(interaction: discord.Interaction, message: str):
    """A slash command that echoes the provided message."""
    await interaction.response.send_message(f"You said: {message}")

# --- 7. Main Bot Runner ---
async def main():
    """
    Main function to load cogs, start keep-alive, and run the bot.
    """
    # Load all other cogs from /cogs
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded cog: {filename[:-3]}")
    
    # Start keep-alive server (if needed for replit, etc.)
    keep_alive()
    
    # Run the bot with your token
    await bot.start(BOT_TOKEN)

# --- 8. Run the Bot ---
if __name__ == "__main__":
    asyncio.run(main())
