import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

# Define item emojis and costs
CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
CHICKEN_COST = 10

ANTI_ROB_EMOJI = "<:lock:1378669263325495416>"
ANTI_ROB_COST = 1000

CUSTOM_ROLE_EMOJI = "<:role:1378669470737891419>"
CUSTOM_ROLE_COST = 150000

# Role shop items
ROLE_COST = 30000
ROLE_ITEMS = {
    "moss sprite": "<:mosssprite:1379352174718619738>",
    "enigma": "<:Enigma:1379352300300013618>",
    "elderleaf": "<:elderleaf:1379352378771509268>",
    "solace": "<:solace:1379352464624713758>",
    "sleepyhead": "<:sleepyhead:1379352570467844238>",
    "adytum": "<:adytum:1379352696145842306>",
}

STAFF_CHANNEL_ID = 1357656511974871202

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    @app_commands.command(name="shop", description="View items available for purchase.")
    async def shop(self, interaction: discord.Interaction):
        role_items_text = "\n".join(
            f"• {emoji} **{name.title()}** - ₱{ROLE_COST}\n  *(Use `/buy {name.replace(' ', '-')}`)*"
            for name, emoji in ROLE_ITEMS.items()
        )

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
                f"  *(Use `/buy custom-role <amount>` to purchase. Staff will reach out for role setup)*\n\n"
                f"**Special Roles:**\n{role_items_text}"
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
        item = item.lower().replace("-", " ")

        await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id}) or {}
        current_balance = int(user_data.get("balance", 0))

        if amount <= 0:
            return await interaction.followup.send("❌ You need to buy at least 1 item.", ephemeral=True)

        # Chicken purchase
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
            return await interaction.followup.send(
                f"✅ You bought {amount} {CHICKEN_EMOJI} **Chicken(s)** for ₱{total_cost:,}!\n"
                f"New balance: ₱{current_balance - total_cost:,}."
            )

        # Anti-rob purchase
        elif item == "anti rob":
            total_cost = ANTI_ROB_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You need ₱{total_cost:,} but only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost, "anti_rob_items": amount}},
                upsert=True
            )
            return await interaction.followup.send(
                f"✅ You bought {amount} {ANTI_ROB_EMOJI} **Anti-Rob Shield(s)** for ₱{total_cost:,}!\n"
                f"New balance: ₱{current_balance - total_cost:,}."
            )

        # Custom role purchase
        elif item == "custom role":
            total_cost = CUSTOM_ROLE_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You need ₱{total_cost:,} but only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost, "custom_roles": amount}},
                upsert=True
            )
            await interaction.followup.send(
                f"🎨 You bought {amount} {CUSTOM_ROLE_EMOJI} **Custom Role(s)** for ₱{total_cost:,}!\n"
                f"Staff will reach out to you soon."
            )
            staff_channel = interaction.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                await staff_channel.send(
                    f"🎨 {interaction.user.mention} bought {amount} **Custom Role(s)**.\nPlease help them set it up."
                )
            return

        # Role shop purchase
        elif item in ROLE_ITEMS:
            total_cost = ROLE_COST * amount
            if current_balance < total_cost:
                return await interaction.followup.send(
                    f"❌ You need ₱{total_cost:,} but only have ₱{current_balance:,}.",
                    ephemeral=True
                )
            self.db.update_one(
                {"_id": user_id},
                {"$inc": {"balance": -total_cost}},
                upsert=True
            )
            await interaction.followup.send(
                f"🎭 You bought {amount} {ROLE_ITEMS[item]} **{item.title()}** role(s) for ₱{total_cost:,}.\n"
                f"Staff will assign it to you shortly!"
            )
            staff_channel = interaction.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                await staff_channel.send(
                    f"🎭 {interaction.user.mention} bought {amount} **{item.title()}** role(s)!\n"
                    f"Please assign the role manually."
                )
            return

        # Invalid item
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
