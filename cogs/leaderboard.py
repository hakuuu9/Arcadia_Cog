import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def generate_leaderboard_embed(self, guild: discord.Guild):
        # Fetch top 20 users sorted by balance
        top_users = list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(20))
        
        if not top_users:
            return None

        # You can replace this emoji with your actual bot's emoji
        emoji = "<:11564whitecrown:1378027038614491226>"  # Replace with actual animated or static emoji ID
        embed = discord.Embed(
            title=f"{emoji} Hall of Fame",
            description="",
            color=discord.Color.gold()
        )

        for index, user in enumerate(top_users, start=1):
            user_id = int(user["_id"])
            member = guild.get_member(user_id)
            name = member.display_name if member else f"<@{user_id}>"
            balance = user.get("balance", 0)
            embed.description += f"**{index}.** {name} — ₱{balance:,}\n"

        return embed

    @app_commands.command(name="leaderboard", description="View the top 20 richest members")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await self.generate_leaderboard_embed(interaction.guild)
        if embed:
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ There are no rich people yet!")

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx):
        embed = await self.generate_leaderboard_embed(ctx.guild)
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ There are no rich people yet!")

    def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
