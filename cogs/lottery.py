import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL

LOTTERY_TICKET_COST = 10000  # cost per ticket

class Lottery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        self.lotteries = {}  # active lotteries {message_id: {...}}

    @app_commands.command(name="lottery", description="Start a lottery event.")
    @app_commands.describe(
        channel="The channel where the lottery will be hosted.",
        duration="Duration in seconds (e.g., 3600 for 1h).",
        winners="Number of winners.",
        prize="Prize description.",
        embed_color="Embed color in hex (#RRGGBB). Optional.",
        thumbnail="Thumbnail image (upload). Optional.",
        image="Main image (upload). Optional."
    )
    async def lottery(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        duration: int,
        winners: int,
        prize: str,
        embed_color: str = "#2ecc71",
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None,
    ):
        """Start a lottery that requires a Lottery Ticket to join."""
        await interaction.response.defer()

        try:
            color = discord.Color.from_str(embed_color)
        except Exception:
            color = discord.Color.green()

        embed = discord.Embed(
            title="🎟️ Arcadia Lottery",
            description=(
                f"🎁 **Prize:** {prize}\n"
                f"🏆 **Winners:** {winners}\n"
                f"⏳ **Duration:** {duration} seconds\n\n"
                f"To join, you must buy **1 Lottery Ticket** from the shop!\n"
                f"Use `/buy lottery-ticket 1`."
            ),
            color=color
        )
        embed.set_footer(text="Arcadia Blackmarket Lottery")

        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)

        lottery_msg = await channel.send(embed=embed, view=self.JoinView(self, prize, winners))

        self.lotteries[lottery_msg.id] = {
            "message": lottery_msg,
            "prize": prize,
            "winners": winners,
            "entrants": set(),
            "ended": False,
        }

        await asyncio.sleep(duration)
        if lottery_msg.id in self.lotteries and not self.lotteries[lottery_msg.id]["ended"]:
            await self.end_lottery(interaction, lottery_msg.id)

    class JoinView(discord.ui.View):
        def __init__(self, cog, prize, winners):
            super().__init__(timeout=None)
            self.cog = cog
            self.prize = prize
            self.winners = winners

        @discord.ui.button(label="🎟️ Join Lottery", style=discord.ButtonStyle.green)
        async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = str(interaction.user.id)
            user_data = self.cog.db.find_one({"_id": user_id}) or {}

            if user_data.get("lottery_tickets", 0) <= 0:
                return await interaction.response.send_message(
                    "❌ You need a **Lottery Ticket** to join! Buy one with `/buy lottery-ticket 1`.",
                    ephemeral=True
                )

            if interaction.message.id not in self.cog.lotteries:
                return await interaction.response.send_message("❌ This lottery is no longer active.", ephemeral=True)

            lottery = self.cog.lotteries[interaction.message.id]
            if user_id in lottery["entrants"]:
                return await interaction.response.send_message("❌ You already joined this lottery!", ephemeral=True)

            self.cog.db.update_one({"_id": user_id}, {"$inc": {"lottery_tickets": -1}}, upsert=True)
            lottery["entrants"].add(user_id)

            await interaction.response.send_message("✅ You successfully joined the lottery!", ephemeral=True)

    @app_commands.command(name="lottery_end", description="Force end a lottery early.")
    @app_commands.describe(message_id="The ID of the lottery message.")
    async def lottery_end(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            message_id = int(message_id)
        except ValueError:
            return await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)

        if message_id not in self.lotteries:
            return await interaction.followup.send("❌ Lottery not found or already ended.", ephemeral=True)

        await self.end_lottery(interaction, message_id)
        await interaction.followup.send("✅ Lottery has been ended.", ephemeral=True)

    async def end_lottery(self, interaction: discord.Interaction, message_id: int):
        lottery = self.lotteries.get(message_id)
        if not lottery or lottery["ended"]:
            return

        entrants = list(lottery["entrants"])
        winners = []
        if entrants:
            winners = random.sample(entrants, min(len(entrants), lottery["winners"]))
        else:
            winners = []

        result_embed = discord.Embed(
            title="🎟️ Lottery Ended",
            description=(
                f"🎁 **Prize:** {lottery['prize']}\n"
                f"🏆 **Winners:** {', '.join(f'<@{w}>' for w in winners) if winners else 'No entrants'}"
            ),
            color=discord.Color.red()
        )
        await lottery["message"].edit(embed=result_embed, view=None)
        lottery["ended"] = True

    def cog_unload(self):
        self.client.close()
        print("Lottery MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Lottery(bot))
