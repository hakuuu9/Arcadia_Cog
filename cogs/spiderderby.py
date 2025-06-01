import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Assuming config.py is in the same directory

# Custom animated spider emojis
SPIDER_RIGHT_EMOJI = "<:rspider:1378665074092412948>"
SPIDER_LEFT_EMOJI = "<:lspider:1378665089585909791>"
FIGHT_EMOJI = "⚔️"
CLASH_EMOJI = "💥"

class SpiderDerby(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users  # Connect to the 'users' collection

    # Slash command
    @app_commands.command(name="spiderderby", description="Bet your ₱ on a thrilling spider derby!")
    @app_commands.describe(
        bet_amount="The amount of ₱ you want to bet.",
        spider_choice="Choose your champion spider!"
    )
    @app_commands.choices(
        spider_choice=[
            app_commands.Choice(name="Right Spider", value="right"),
            app_commands.Choice(name="Left Spider", value="left"),
        ]
    )
    async def spiderderby(self, interaction: discord.Interaction, bet_amount: int, spider_choice: str):
        user_id = str(interaction.user.id)

        await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0

        if bet_amount <= 0:
            return await interaction.followup.send("❌ You must bet a positive amount.", ephemeral=True)

        if current_balance < bet_amount:
            return await interaction.followup.send(
                f"❌ You don't have enough money! You have ₱{current_balance:,} but tried to bet ₱{bet_amount:,}.",
                ephemeral=True
            )

        chosen_spider_emoji = SPIDER_RIGHT_EMOJI if spider_choice == "right" else SPIDER_LEFT_EMOJI
        chosen_spider_name = "Right Spider" if spider_choice == "right" else "Left Spider"

        await interaction.followup.send(
            f"{interaction.user.mention} placed a bet of ₱{bet_amount:,} on the **{chosen_spider_name}** {chosen_spider_emoji}!\n"
            f"The spiders are ready! {SPIDER_RIGHT_EMOJI} {FIGHT_EMOJI} {SPIDER_LEFT_EMOJI}"
        )

        battle_message = await interaction.channel.send("The spiders are battling fiercely... 🕷️💨🕸️")

        animation_frames = [
            f"{SPIDER_RIGHT_EMOJI}  {FIGHT_EMOJI}  {SPIDER_LEFT_EMOJI}",
            f"  {SPIDER_RIGHT_EMOJI}{FIGHT_EMOJI}{SPIDER_LEFT_EMOJI}  ",
            f"{SPIDER_RIGHT_EMOJI}{CLASH_EMOJI}{SPIDER_LEFT_EMOJI}",
            f" {SPIDER_LEFT_EMOJI} {FIGHT_EMOJI} {SPIDER_RIGHT_EMOJI}",
            f"{SPIDER_LEFT_EMOJI}   {FIGHT_EMOJI}   {SPIDER_RIGHT_EMOJI} {CLASH_EMOJI}",
            f"{SPIDER_RIGHT_EMOJI} {FIGHT_EMOJI} {SPIDER_LEFT_EMOJI} 💥",
            f"🕷️⚔️🕸️",
        ]

        for _ in range(7):
            frame = random.choice(animation_frames)
            await battle_message.edit(content=f"The spiders are battling fiercely... {frame}")
            await asyncio.sleep(0.5)

        await battle_message.delete()

        winning_spider_value = random.choice(["right", "left"])
        winning_spider_emoji = SPIDER_RIGHT_EMOJI if winning_spider_value == "right" else SPIDER_LEFT_EMOJI
        winning_spider_name = "Right Spider" if winning_spider_value == "right" else "Left Spider"

        if winning_spider_value == spider_choice:
            net_change = bet_amount
            new_balance = current_balance + net_change
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": net_change}},
                upsert=True
            )
            await interaction.followup.send(
                f"🎉 **VICTORY!** The **{winning_spider_name}** {winning_spider_emoji} emerged victorious!\n"
                f"{interaction.user.mention} won ₱{net_change:,}!\n"
                f"Your new balance is ₱{new_balance:,}."
            )
        else:
            net_change = -bet_amount
            new_balance = current_balance + net_change
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": net_change}},
                upsert=True
            )
            await interaction.followup.send(
                f"💔 **DEFEAT!** The **{winning_spider_name}** {winning_spider_emoji} reigned supreme.\n"
                f"{interaction.user.mention} lost ₱{bet_amount:,}.\n"
                f"Your new balance is ₱{new_balance:,}."
            )

    # Manual text command version
    @commands.command(name="spiderderby")
    async def spiderderby_text(self, ctx, bet_amount: int = None, spider_choice: str = None):
        if bet_amount is None or spider_choice is None:
            return await ctx.send(
                f"❌ Incorrect usage.\n**Correct format:** `$spiderderby <bet_amount> <right/left>`\n"
                f"Example: `$spiderderby 100 right`",
                delete_after=10
            )

        if spider_choice.lower() not in ["right", "left"]:
            return await ctx.send("❌ Invalid spider choice. Please choose either `right` or `left`.", delete_after=10)

        # Mimic a Discord Interaction for reuse
        class FakeInteraction:
            def __init__(self, user, channel):
                self.user = user
                self.channel = channel
                self.response = self
                self.followup = self

            async def defer(self, ephemeral=False):
                pass

            async def send(self, *args, **kwargs):
                return await self.channel.send(*args, **kwargs)

        interaction = FakeInteraction(ctx.author, ctx.channel)
        await self.spiderderby.callback(self, interaction, bet_amount, spider_choice.lower())

    def cog_unload(self):
        self.client.close()
        print("SpiderDerby MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(SpiderDerby(bot))
