import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime 

# --- CONFIGURATION ---
# Replace with the channel ID where suggestions should be posted.
SUGGESTION_CHANNEL_ID = 1365065762104020992 
# Replace with the channel ID where the "Submit" button message will be. This can be the same as above.
SUGGESTION_SETUP_CHANNEL_ID = 1365065762104020992 

UPVOTE_EMOJI = '✅'
DOWNVOTE_EMOJI = '❌'

# <<< MODIFICATION: Thumbnail URL added >>>
SUGGESTION_THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1365065762104020992/1413479257459654677/IMG_2007.gif?ex=68bc14a4&is=68bac324&hm=2fc0c9732a46a69ec7adbf031c8267e2913e8f44ff1ed149ee1ed01a44eb021e"

# This is the pop-up form (Modal) that appears when the button is clicked.
class SuggestionModal(ui.Modal, title="Submit a Recommendation"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    # Text input field for the suggestion
    suggestion_text = ui.TextInput(
        label="What is your suggestion?",
        style=discord.TextStyle.paragraph, # Allows for multi-line input
        placeholder="e.g., We should add an UNO bot to the server for events.",
        required=True,
        max_length=1500,
    )

    # This function is called when the user clicks the "Submit" button on the modal.
    async def on_submit(self, interaction: discord.Interaction):
        # Get the channel where suggestions will be posted
        suggestion_channel = self.bot.get_channel(SUGGESTION_CHANNEL_ID)

        if not suggestion_channel:
            await interaction.response.send_message(
                "❗ Error: Suggestion channel not found. Please contact an admin.", 
                ephemeral=True
            )
            return

        # Create a beautiful embed for the suggestion
        suggestion_embed = discord.Embed(
            title="New Suggestion",
            description=self.suggestion_text.value,
            color=0xF5F5DC
        )
        suggestion_embed.set_author(
            name=f"{interaction.user.display_name}", 
            icon_url=interaction.user.display_avatar.url
        )
        
        # <<< MODIFICATION: Set the thumbnail >>>
        suggestion_embed.set_thumbnail(url=SUGGESTION_THUMBNAIL_URL)

        # Get the date from the interaction's creation time for accuracy
        formatted_date = interaction.created_at.strftime('%m/%d/%Y')
        
        suggestion_embed.set_footer(
            text=f"Submitted on: {formatted_date}"
        )

        # Send the suggestion embed to the suggestions channel
        suggestion_message = await suggestion_channel.send(embed=suggestion_embed)

        # Add upvote and downvote reactions
        await suggestion_message.add_reaction(UPVOTE_EMOJI)
        await suggestion_message.add_reaction(DOWNVOTE_EMOJI)

        # Send a confirmation message to the user
        await interaction.response.send_message(
            "✅ Thank you! Your recommendation has been submitted.", 
            ephemeral=True
        )

# This is the View that contains the "Submit Recommendation" button.
class SuggestionView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None) # timeout=None makes it persistent
        self.bot = bot

    @ui.button(label="Submit Recommendation", style=discord.ButtonStyle.primary, custom_id="submit_recommendation_button")
    async def submit_button(self, interaction: discord.Interaction, button: ui.Button):
        # When the button is clicked, create and send the SuggestionModal
        modal = SuggestionModal(self.bot)
        await interaction.response.send_modal(modal)

class Suggestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # We need to add the persistent view here so the bot knows about the button
        # after a restart.
        self.bot.add_view(SuggestionView(bot))
        print("Suggestion Cog initialized.")

    # Command to set up the suggestion message with the button
    @app_commands.command(name="suggestion_setup", description="Sets up the suggestion submission message in this channel.")
    @app_commands.checks.has_permissions(administrator=True) # Only admins can use this
    async def suggestion_setup(self, interaction: discord.Interaction):
        """Sets up the suggestion message with a button."""
        
        if interaction.channel.id != SUGGESTION_SETUP_CHANNEL_ID:
            await interaction.response.send_message(
                f"❗ This command can only be used in the designated setup channel.",
                ephemeral=True
            )
            return
            
        setup_embed = discord.Embed(
            title="📝 Submit a Suggestion",
            description="Click the button below to submit a suggestion for the server!",
            color=discord.Color.purple()
        )
        
        await interaction.channel.send(embed=setup_embed, view=SuggestionView(self.bot))
        
        await interaction.response.send_message(
            "✅ Suggestion setup message has been posted.", 
            ephemeral=True
        )

    # Error handler for the setup command
    @suggestion_setup.error
    async def on_suggestion_setup_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True
            )
        else:
            raise error

async def setup(bot):
    await bot.add_cog(Suggestion(bot))
