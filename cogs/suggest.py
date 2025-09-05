import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime 
from pymongo import MongoClient
from config import MONGO_URL # Assumes MONGO_URL is in a config.py file

# --- CONFIGURATION ---
# IMPORTANT: Both IDs should be the SAME for a single-channel system.
SUGGESTIONS_CHANNEL_ID = 1365065762104020992 

UPVOTE_EMOJI = '✅'
DOWNVOTE_EMOJI = '❌'

SUGGESTION_THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1365065762104020992/1413481070149763183/IMG_2007.gif?ex=68bc1654&is=68bac4d4&hm=3629180fcf5384bbc607d5a84df5a6268c9a81ee91afb9b26f698e078d6d1a30"

# This is the function that creates the setup message embed
def create_setup_embed():
    return discord.Embed(
        title="📝 Submit a Suggestion",
        description="Click the button below to submit a suggestion for the server!",
        color=discord.Color.purple()
    )

# The Modal (pop-up form) remains mostly the same
class SuggestionModal(ui.Modal, title="Submit a Recommendation"):
    def __init__(self, bot, cog):
        super().__init__()
        self.bot = bot
        self.cog = cog # We need the cog to access the database and other methods

    suggestion_text = ui.TextInput(
        label="What is your suggestion?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., We should add an UNO bot to the server for events.",
        required=True,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Defer response as we have a lot to do

        suggestion_channel = self.bot.get_channel(SUGGESTIONS_CHANNEL_ID)
        if not suggestion_channel:
            await interaction.followup.send("❗ Error: Suggestion channel not found.", ephemeral=True)
            return

        # 1. Post the new suggestion embed
        suggestion_embed = discord.Embed(
            title="New Suggestion",
            description=self.suggestion_text.value,
            color=0xF5F5DC
        )
        suggestion_embed.set_author(name=f"{interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        suggestion_embed.set_thumbnail(url=SUGGESTION_THUMBNAIL_URL)
        formatted_date = interaction.created_at.strftime('%m/%d/%Y')
        suggestion_embed.set_footer(text=f"Submitted on: {formatted_date}")
        
        suggestion_message = await suggestion_channel.send(embed=suggestion_embed)
        await suggestion_message.add_reaction(UPVOTE_EMOJI)
        await suggestion_message.add_reaction(DOWNVOTE_EMOJI)

        # 2. Delete the old button message
        await self.cog.delete_old_setup_message()

        # 3. Post the new button message at the bottom
        await self.cog.post_new_setup_message(suggestion_channel)

        await interaction.followup.send("✅ Thank you! Your recommendation has been submitted.", ephemeral=True)


# The View now passes the main cog instance to the Modal
class SuggestionView(ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog

    @ui.button(label="Submit Recommendation", style=discord.ButtonStyle.primary, custom_id="submit_recommendation_button_v2")
    async def submit_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = SuggestionModal(self.bot, self.cog)
        await interaction.response.send_modal(modal)


class Suggestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # <<< MODIFICATION: Connect to MongoDB >>>
        self.mongo = MongoClient(MONGO_URL)
        self.db = self.mongo.hxhbot.system_messages
        
        # <<< MODIFICATION: Add the persistent view, passing the cog itself >>>
        self.bot.add_view(SuggestionView(bot, self))
        print("Suggestion Cog initialized with MongoDB.")

    async def delete_old_setup_message(self):
        """Finds and deletes the previous setup message."""
        doc = self.db.find_one({"_id": "suggestion_setup_message"})
        if not doc:
            return

        message_id = doc.get("message_id")
        channel = self.bot.get_channel(SUGGESTIONS_CHANNEL_ID)
        if not channel or not message_id:
            return
        
        try:
            old_message = await channel.fetch_message(message_id)
            await old_message.delete()
        except discord.NotFound:
            print("Old setup message not found, it might have been deleted manually.")
        except discord.Forbidden:
            print("Bot lacks permissions to delete the old setup message.")

    async def post_new_setup_message(self, channel: discord.TextChannel):
        """Posts a new setup message and saves its ID to the database."""
        new_message = await channel.send(embed=create_setup_embed(), view=SuggestionView(self.bot, self))
        self.db.update_one(
            {"_id": "suggestion_setup_message"},
            {"$set": {"message_id": new_message.id}},
            upsert=True
        )

    @app_commands.command(name="suggestion_setup", description="Sets up the auto-moving suggestion button in this channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def suggestion_setup(self, interaction: discord.Interaction):
        if interaction.channel.id != SUGGESTIONS_CHANNEL_ID:
            await interaction.response.send_message(f"❗ This command can only be used in the designated suggestions channel.", ephemeral=True)
            return

        await interaction.response.send_message("Setting up the suggestion system...", ephemeral=True)
        
        # Clean up any old message first
        await self.delete_old_setup_message()
        # Post the new one
        await self.post_new_setup_message(interaction.channel)

        await interaction.edit_original_response(content="✅ Suggestion setup message has been posted. It will now stay at the bottom of the channel.")

    @suggestion_setup.error
    async def on_suggestion_setup_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        else:
            raise error
            
    def cog_unload(self):
        self.mongo.close()
        print("Suggestion Cog MongoDB connection closed.")

async def setup(bot):
    await bot.add_cog(Suggestion(bot))
