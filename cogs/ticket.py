import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button

# Configuration
TICKET_COMMAND_CHANNEL_ID = 1361757195686907925
SUPPORT_CATEGORY_ID = 1343219140864901150
STAFF_ROLE_NAME = "Moderator"
LOG_CHANNEL_ID = 1364839238960549908

open_tickets = {}

class CloseView(View):
    def __init__(self, user_id, ticket_channel):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_channel = ticket_channel

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = any(role.name == STAFF_ROLE_NAME for role in interaction.user.roles)
        if interaction.user.id != self.user_id and not is_staff:
            await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)
            return

        await self.ticket_channel.send("Closing ticket...")
        await self.ticket_channel.delete()
        open_tickets.pop(self.user_id, None)

class TicketTypeDropdown(Select):
    def __init__(self, user):
        self.user = user
        options = [
            discord.SelectOption(label="Claim", value="claim", description="Open a ticket to claim something"),
            discord.SelectOption(label="Concern", value="concern", description="Report a concern or issue"),
            discord.SelectOption(label="Suggestion", value="suggestion", description="Share your suggestion")
        ]
        super().__init__(placeholder="Choose a ticket type", options=options, custom_id="ticket_type_dropdown")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user

        if user.id in open_tickets:
            await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
            return

        category = guild.get_channel(SUPPORT_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            category = await guild.create_category("Tickets")

        channel_name = f"{self.values[0]}-{user.name}".replace(" ", "-").lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True)
        }

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"Ticket opened ({self.values[0]})"
        )

        open_tickets[user.id] = ticket_channel.id

        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

        close_view = CloseView(user.id, ticket_channel)
        await ticket_channel.send(f"{user.mention}, your ticket has been created for **{self.values[0].capitalize()}**.", view=close_view)

        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"Ticket opened by {user.mention} in {ticket_channel.mention} for **{self.values[0].capitalize()}**.")

class DropdownView(View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.add_item(TicketTypeDropdown(user))

class OpenTicketButton(Button):
    def __init__(self):
        super().__init__(label="🎫 Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Please choose a ticket type:", view=DropdownView(interaction.user), ephemeral=True)

class OpenTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticket")
    async def manual_ticket(self, ctx):
        """Manual prefix-based command (e.g., hxh ticket)"""
        if ctx.channel.id != TICKET_COMMAND_CHANNEL_ID:
            await ctx.send("You can only use this command in the ticket channel.", delete_after=5)
            return

        await self.send_ticket_embed(ctx.channel, ctx.guild)

    @app_commands.command(name="ticket", description="Create a ticket for support")
    async def slash_ticket(self, interaction: discord.Interaction):
        """Slash command: /ticket"""
        if interaction.channel.id != TICKET_COMMAND_CHANNEL_ID:
            await interaction.response.send_message("You can only use this command in the ticket channel.", ephemeral=True)
            return

        await interaction.response.send_message("Ticket menu sent!", ephemeral=True)
        await self.send_ticket_embed(interaction.channel, interaction.guild)

    async def send_ticket_embed(self, channel, guild):
        embed = discord.Embed(
            title="Need Support?",
            description="Click the button below to open a **private ticket** with our staff.\nThen choose the ticket type.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Ticket System by ARCADIA")
        await channel.send(embed=embed, view=OpenTicketView())

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(OpenTicketView())
        print("✅ Ticket View registered")

async def setup(bot):
    await bot.add_cog(TicketCog(bot))