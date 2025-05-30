import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users  # Your MongoDB collection

    async def generate_leaderboard_embed(self, guild: discord.Guild):
        top_users = list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(20))

        if not top_users:
            return None

        emoji = "<:11564whitecrown:1378027038614491226>"

        embed = discord.Embed(
            title=f"{emoji}  HALL OF FAME  {emoji}",
            color=discord.Color.black()
        )

        lines = []
        for idx, user in enumerate(top_users, start=1):
            user_id = int(user["_id"])
            member = guild.get_member(user_id)
            if member:
                name = f"{member.name}#{member.discriminator}"
            else:
                name = f"<@{user_id}>"
            balance = user.get("balance", 0)
            lines.append(f"**{idx}.** {name} — ₱{balance:,}")

        embed.description = "\n".join(lines)

        return embed

    @commands.command(name="leaderboard")
    async def leaderboard_command(self, ctx):
        embed = await self.generate_leaderboard_embed(ctx.guild)
        if embed is None:
            await ctx.send("❌ There are no rich people yet!")
        else:
            await ctx.send(embed=embed)

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
