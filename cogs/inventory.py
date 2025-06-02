import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URL

CHICKEN_EMOJI = "<:cockfight:1378658097954033714>"
ANTI_ROB_EMOJI = "<:lock:1378669263325495416>"
CUSTOM_ROLE_EMOJI = "<:role:1378669470737891419>"  # Replace with your emoji
CUSTOM_ROLE_CHANNEL_ID = 1357656511974871202  # Replace with your actual channel ID

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    @app_commands.command(name="inventory", description="View your owned items and protection status.")
    async def inventory(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = datetime.utcnow()
        await interaction.response.defer(ephemeral=False)

        user_data = self.db.find_one({"_id": user_id})
        balance = int(user_data.get("balance", 0)) if user_data else 0
        chickens_owned = int(user_data.get("chickens_owned", 0)) if user_data else 0
        anti_rob_items_owned = int(user_data.get("anti_rob_items", 0)) if user_data else 0
        custom_role_items = int(user_data.get("custom_role_items", 0)) if user_data else 0
        anti_rob_expires_at = user_data.get("anti_rob_expires_at") if user_data else None

        # Anti-Rob status
        anti_rob_status = "Inactive"
        if anti_rob_expires_at and current_time < anti_rob_expires_at:
            remaining = anti_rob_expires_at - current_time
            days = remaining.days
            hours, rem = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            time_parts = []
            if days: time_parts.append(f"{days} day{'s' if days > 1 else ''}")
            if hours: time_parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
            if minutes: time_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
            time_str = ", ".join(time_parts) or "a few seconds"
            anti_rob_status = f"Active! Ends in **{time_str}** (<t:{int(anti_rob_expires_at.timestamp())}:R>)"
        elif anti_rob_expires_at:
            self.db.update_one({"_id": user_id}, {"$unset": {"anti_rob_expires_at": ""}})

        # Create Embed
        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}'s Inventory 🎒",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_footer(text="Manage your assets wisely!")

        embed.add_field(name="💰 Cash", value=f"₱{balance:,}", inline=True)
        embed.add_field(name="🐔 Chickens", value=f"{chickens_owned} {CHICKEN_EMOJI}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(name=f"{ANTI_ROB_EMOJI} Anti-Rob Shields", value=f"{anti_rob_items_owned} owned", inline=False)
        embed.add_field(name="🛡️ Anti-Rob Protection Status", value=anti_rob_status, inline=False)
        embed.add_field(name=f"{CUSTOM_ROLE_EMOJI} Custom Role Tokens", value=f"{custom_role_items} owned", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="inventory_use", description="Use an item from your inventory.")
    @app_commands.describe(item="The item you want to use, like 'custom-role'")
    async def inventory_use(self, interaction: discord.Interaction, item: str):
        user_id = str(interaction.user.id)
        item = item.lower()

        await interaction.response.defer(ephemeral=True)
        user_data = self.db.find_one({"_id": user_id})
        if not user_data:
            return await interaction.followup.send("❌ You don't have any items to use.")

        if item == "custom-role":
            custom_role_items = int(user_data.get("custom_role_items", 0))
            if custom_role_items <= 0:
                return await interaction.followup.send("❌ You don't own any Custom Role Tokens.")
            
            self.db.update_one({"_id": user_id}, {"$inc": {"custom_role_items": -1}})
            channel = self.bot.get_channel(CUSTOM_ROLE_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"{CUSTOM_ROLE_EMOJI} **{interaction.user.mention}** has used a Custom Role Token for their exclusive perk!"
                )
            await interaction.followup.send(f"✅ You used one {CUSTOM_ROLE_EMOJI} Custom Role Token.")
        else:
            await interaction.followup.send("❌ That item cannot be used or does not exist.")

    def cog_unload(self):
        self.client.close()
        print("Inventory MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Inventory(bot))
