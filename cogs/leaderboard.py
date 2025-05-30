import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to MongoDB collection where user balances are stored
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users  # Make sure this matches your coinflip/balance collection

    async def generate_leaderboard_embed(self, guild: discord.Guild):
        top_users = list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(20))

        if not top_users:
            return None

        # Replace these emoji strings with your bot's emojis (custom or unicode)
        emoji = "<:11564whitecrown:1378027038614491226>"  # Example animated emoji format
        # If you want plain unicode emojis, just do e.g. emoji = "🏆"

        embed = discord.Embed(
            title=f"{emoji}  HALL OF FAME  {emoji}",
            color=discord.Color.gold()
        )

        lines = []
        max_name_len = 0
        user_lines = []

        # Gather user display names and balances, find max name length for padding
        for user in top_users:
            user_id = int(user["_id"])
            member = guild.get_member(user_id)
            if member:
                name = f"{member.name}#{member.discriminator}"
            else:
                name = f"<@{user_id}>"
            balance = user.get("balance", 0)
            user_lines.append((name, balance))
            if len(name) > max_name_len:
                max_name_len = len(name)

        # Build each line with padding so amounts align vertically
        for idx, (name, balance) in enumerate(user_lines, start=1):
            padded_name = name.ljust(max_name_len)
            formatted_balance = f"₱{balance:,}"
            lines.append(f"{idx}. {padded_name}  —  {formatted_balance}")

        embed.description = "```\n" + "\n".join(lines) + "\n```"

        return embed

    # Prefix command version
    @commands.command(name="leaderboard")
    async def leaderboard_command(self, ctx):
        embed = await self.generate_leaderboard_embed(ctx.guild)
        if embed is None:
            await ctx.send("❌ There are no rich people yet!")
        else:
            await ctx.send(embed=embed)

    # Slash command version
    @app_commands.command(name="leaderboard", description="View the top 20 richest members")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await self.generate_leaderboard_embed(interaction.guild)
        if embed is None:
            await interaction.followup.send("❌ There are no rich people yet!")
        else:
            await interaction.followup.send(embed=embed)

    async def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
