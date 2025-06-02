import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

# Define item emojis and costs
CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
CHICKEN_COST = 10

ANTI_ROB_EMOJI = "<:lock:1378669263325495416>"
ANTI_ROB_COST = 10000

CUSTOM_ROLE_EMOJI = "<:role:1378669470737891419>"
CUSTOM_ROLE_COST = 150000

# Replace with your staff channel ID
STAFF_CHANNEL_ID = 1357656511974871202  # ← UPDATE THIS

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    @app_commands.command(name="shop", description="View items available for purchase.")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ARCADIA BLACKMARKET",
            description=(
                f"Welcome to the dark alley of Arcadia where power is sold to the bold.\n\n"
                f"**Available Items:**\n"
                f"• {CHICKEN_EMOJI} **Chicken** - ₱{CHICKEN_COST}\n"
                f"  *(Use `/buy chicken <amount>` to purchase)*\n\n"
                f"• {ANTI_ROB_EMOJI} **Anti-Rob Shield** - ₱{ANTI_ROB_COST}\n"
                f"  *(Use `/buy anti-rob <amount>` to purchase. Requires `/use anti-rob` later!)*\n\n"
                f"• {CUSTOM_ROLE_EMOJI} **Custom Role** - ₱{CUSTOM_ROLE_COST}\n"
                f"  *(Use `/buy custom-role <amount>` to purchase. Staff will reach out for role setup)*"
            ),
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url="https://i.imgur.com/JxsCfCe.gif")
        embed.set_footer(text="🕶️ Welcome to the underworld of Arcadia.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy items from the shop.")
    @app_commands.describe(item="The item you want to buy.", amount="The quantity to buy.")
    async def buy(self, interaction: discord.Interaction, item: str, amount: int):
        user_id = str(interaction.user.id)
        item = item.lower()

        await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0
        anti_rob_items_owned = int(user_data.get("anti_rob_items", 0)) if user_data else 0
        custom_roles_owned = int(user_data.get("custom_roles", 0)) if user_data else 0

        if amount <= 0:
            return await interaction.followup.send("❌ You need to buy at least 1 item.", ephemeral=True)

        if item == "chicken":
            total_cost = CHICKEN_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You don't have enough money! You need ₱{total_cost:,} but only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost, "chickens_owned": amount}},
                upsert=True
            )
            await interaction.followup.send(
                f"✅ You bought {amount} {CHICKEN_EMOJI} **Chicken(s)** for ₱{total_cost:,}!\n"
                f"New balance: ₱{current_balance - total_cost:,}.\n"
                f"Total chickens owned: {chickens_owned + amount}."
            )

        elif item == "anti-rob":
            total_cost = ANTI_ROB_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You don't have enough money! You need ₱{total_cost:,} but only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost, "anti_rob_items": amount}},
                upsert=True
            )
            await interaction.followup.send(
                f"✅ You bought {amount} {ANTI_ROB_EMOJI} **Anti-Rob Shield(s)** for ₱{total_cost:,}!\n"
                f"New balance: ₱{current_balance - total_cost:,}.\n"
                f"Total shields owned: {anti_rob_items_owned + amount}."
            )

        elif item == "custom-role":
            total_cost = CUSTOM_ROLE_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You need ₱{total_cost:,} to buy {amount} custom role(s), but you only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost, "custom_roles": amount}},
                upsert=True
            )
            await interaction.followup.send(
                f"🎨 You bought {amount} {CUSTOM_ROLE_EMOJI} **Custom Role(s)** for ₱{total_cost:,}!\n"
                f"New balance: ₱{current_balance - total_cost:,}.\n"
                f"Staff will contact you soon to set up your role(s)."
            )

            # Notify staff
            staff_channel = interaction.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                await staff_channel.send(
                    f"🎨 {interaction.user.mention} just bought {amount} custom role(s)!\n"
                    f"Please reach out to help them set it up."
                )

        else:
            await interaction.followup.send(
                f"❌ '{item}' is not a valid item. Use `/shop` to view available options.",
                ephemeral=True
            )

    def cog_unload(self):
        self.client.close()
        print("Shop MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Shop(bot))
