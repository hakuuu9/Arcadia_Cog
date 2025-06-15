import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL

ARC_EMOJI = "🗡️"
COIN_EMOJI = "🪙"
PET_EMOJI = "🐾"

HUNT_COOLDOWN = 20  # seconds

# Pets with rarities and sell prices
PETS = {
    "Wolf": {"rarity": "Common", "sell_price": 100},
    "Bear": {"rarity": "Uncommon", "sell_price": 200},
    "Falcon": {"rarity": "Rare", "sell_price": 500},
    "Fox": {"rarity": "Common", "sell_price": 120},
    "Tiger": {"rarity": "Epic", "sell_price": 1000},
}

class Arcadia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        self.cooldowns = {}

    async def run_hunt(self, ctx_or_interaction, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)
        now = asyncio.get_event_loop().time()

        if user_id in self.cooldowns and self.cooldowns[user_id] > now:
            remaining = int(self.cooldowns[user_id] - now)
            msg = f"⏳ You’re tired from hunting in **Arcadia**! Please wait {remaining} seconds before hunting again."
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        self.cooldowns[user_id] = now + HUNT_COOLDOWN

        if is_slash:
            await ctx_or_interaction.response.defer()

        user_data = self.db.find_one({"_id": user_id})
        if not user_data:
            user_data = {"_id": user_id, "coins": 0, "pets": []}
            self.db.insert_one(user_data)

        coins_found = random.randint(10, 50)

        new_pet = None
        if random.random() < 0.3:
            owned_pets = user_data.get("pets", [])
            available_pets = [pet for pet in PETS if pet not in owned_pets]
            if available_pets:
                new_pet = random.choice(available_pets)

        update_query = {"$inc": {"coins": coins_found}}
        if new_pet:
            update_query["$addToSet"] = {"pets": new_pet}

        self.db.update_one({"_id": user_id}, update_query)

        message = (
            f"{ARC_EMOJI} {user.mention}, you went hunting in **Arcadia** and earned {COIN_EMOJI} **{coins_found} coins**!"
        )
        if new_pet:
            pet_info = PETS[new_pet]
            message += f"\n{PET_EMOJI} You caught a **{new_pet}** (Rarity: {pet_info['rarity']})!"

        await self._send(ctx_or_interaction, message, is_slash)

    async def show_pets(self, ctx_or_interaction, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        if is_slash:
            await ctx_or_interaction.response.defer()

        user_data = self.db.find_one({"_id": user_id})
        pets = user_data.get("pets", []) if user_data else []

        if not pets:
            msg = f"{PET_EMOJI} {user.mention}, you have no pets yet. Go hunting to catch some!"
            return await self._send(ctx_or_interaction, msg, is_slash)

        # Group pets by rarity for nicer display
        pet_lines = []
        for pet in pets:
            pet_info = PETS.get(pet, {"rarity": "Unknown"})
            pet_lines.append(f"**{pet}** (Rarity: {pet_info['rarity']})")

        embed = discord.Embed(title=f"{user.display_name}'s Pets", color=discord.Color.green())
        embed.description = "\n".join(pet_lines)
        await self._send_embed(ctx_or_interaction, embed, is_slash)

    async def show_coins(self, ctx_or_interaction, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        if is_slash:
            await ctx_or_interaction.response.defer()

        user_data = self.db.find_one({"_id": user_id})
        coins = user_data.get("coins", 0) if user_data else 0

        msg = f"{COIN_EMOJI} {user.mention}, you have **{coins:,} coins**."
        await self._send(ctx_or_interaction, msg, is_slash)

    async def sell_pet(self, ctx_or_interaction, pet_name: str, is_slash: bool = False):
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        user_id = str(user.id)

        if is_slash:
            await ctx_or_interaction.response.defer()

        pet_name = pet_name.title()

        if pet_name not in PETS:
            msg = f"❌ That pet is not recognized. Available pets: {', '.join(PETS.keys())}"
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        user_data = self.db.find_one({"_id": user_id})
        pets = user_data.get("pets", []) if user_data else []

        if pet_name not in pets:
            msg = f"❌ You don't own a **{pet_name}**."
            return await self._send(ctx_or_interaction, msg, is_slash, ephemeral=True)

        sell_price = PETS[pet_name]["sell_price"]

        # Remove pet and add coins
        self.db.update_one(
            {"_id": user_id},
            {
                "$pull": {"pets": pet_name},
                "$inc": {"coins": sell_price}
            }
        )

        msg = f"{PET_EMOJI} You sold your **{pet_name}** for {COIN_EMOJI} **{sell_price} coins**."
        await self._send(ctx_or_interaction, msg, is_slash)

    async def leaderboard(self, ctx_or_interaction, is_slash: bool = False):
        if is_slash:
            await ctx_or_interaction.response.defer()

        # Get top 10 users by coins
        top_users = self.db.find().sort("coins", -1).limit(10)

        embed = discord.Embed(title="🏆 Arcadia Leaderboard (Coins)", color=discord.Color.gold())

        description_lines = []
        rank = 1
        for user_data in top_users:
            user_id = int(user_data["_id"])
            coins = user_data.get("coins", 0)
            # Get member display name safely
            member = ctx_or_interaction.guild.get_member(user_id) if hasattr(ctx_or_interaction, "guild") else None
            name = member.display_name if member else f"User ID: {user_id}"
            description_lines.append(f"**{rank}. {name}** — {COIN_EMOJI} {coins:,}")
            rank += 1

        if not description_lines:
            description_lines.append("No data yet.")

        embed.description = "\n".join(description_lines)

        await self._send_embed(ctx_or_interaction, embed, is_slash)

    async def _send(self, ctx_or_interaction, message: str, is_slash: bool, ephemeral: bool = False):
        if is_slash:
            await ctx_or_interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.send(message)

    async def _send_embed(self, ctx_or_interaction, embed: discord.Embed, is_slash: bool, ephemeral: bool = False):
        if is_slash:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.send(embed=embed)

    @commands.command(name="hunt")
    async def hunt_text(self, ctx):
        await self.run_hunt(ctx, is_slash=False)

    @app_commands.command(name="hunt", description="Go hunting in Arcadia to earn coins and maybe catch pets!")
    async def hunt_slash(self, interaction: discord.Interaction):
        await self.run_hunt(interaction, is_slash=True)

    @commands.command(name="pets")
    async def pets_text(self, ctx):
        await self.show_pets(ctx, is_slash=False)

    @app_commands.command(name="pets", description="Show your caught pets.")
    async def pets_slash(self, interaction: discord.Interaction):
        await self.show_pets(interaction, is_slash=True)

    @commands.command(name="coins")
    async def coins_text(self, ctx):
        await self.show_coins(ctx, is_slash=False)

    @app_commands.command(name="coins", description="Show your current coin balance.")
    async def coins_slash(self, interaction: discord.Interaction):
        await self.show_coins(interaction, is_slash=True)

    @commands.command(name="sellpet")
    async def sellpet_text(self, ctx, *, pet_name: str = None):
        if not pet_name:
            return await ctx.send(f"❌ Usage: `$sellpet <petname>` — e.g. `$sellpet Wolf`")
        await self.sell_pet(ctx, pet_name, is_slash=False)

    @app_commands.command(name="sellpet", description="Sell a pet for coins.")
    @app_commands.describe(pet_name="Name of the pet to sell")
    async def sellpet_slash(self, interaction: discord.Interaction, pet_name: str):
        await self.sell_pet(interaction, pet_name, is_slash=True)

    @commands.command(name="top")
    async def leaderboard_text(self, ctx):
        await self.leaderboard(ctx, is_slash=False)

    @app_commands.command(name="top", description="Show top hunters by coins.")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await self.leaderboard(interaction, is_slash=True)

    def cog_unload(self):
        self.client.close()
        print("Arcadia MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Arcadia(bot))
