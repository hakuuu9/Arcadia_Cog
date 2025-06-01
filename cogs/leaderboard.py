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

    async def fetch_top_users(self):
        # Get top 100 users by balance (you can limit as needed)
        top_users = list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(100))
        return top_users

    def create_embed(self, guild, users, page, per_page=8):
        emoji = "<:11564whitecrown:1378027038614491226>"
        embed = discord.Embed(
            title=f"{emoji} ARCADIA LEADERBOARD {emoji}",
            description="\"Wealth is the ability to fully experience life.\" — Henry David Thoreau\n\n",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        start = page * per_page
        end = start + per_page
        page_users = users[start:end]

        if not page_users:
            embed.description += "No users found on this page."
            return embed

        for i, user in enumerate(page_users, start=start + 1):
            try:
                user_id = int(user["_id"])
                member = guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                balance = user.get("balance", 0)
                embed.description += f"**{i}.** {name} — ₱{balance:,}\n\n"  # extra newline for spacing
            except Exception:
                embed.description += f"**{i}.** <Unknown User> — ₱{user.get('balance', 0):,}\n\n"

        embed.set_footer(text=f"Page {page + 1} / {(len(users) - 1) // per_page + 1}")
        return embed

    class LeaderboardView(discord.ui.View):
        def __init__(self, cog, users, guild, *, timeout=60):
            super().__init__(timeout=timeout)
            self.cog = cog
            self.users = users
            self.guild = guild
            self.page = 0
            self.per_page = 8

            # Disable prev button on first page initially
            self.prev_button.disabled = True
            # Disable next button if only 1 page
            if len(users) <= self.per_page:
                self.next_button.disabled = True

        async def update_embed(self, interaction):
            embed = self.cog.create_embed(self.guild, self.users, self.page, self.per_page)
            await interaction.edit_original_response(embed=embed, view=self)

        @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            self.page -= 1
            if self.page <= 0:
                self.page = 0
                self.prev_button.disabled = True
            self.next_button.disabled = False
            await self.update_embed(interaction)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            max_page = (len(self.users) - 1) // self.per_page
            self.page += 1
            if self.page >= max_page:
                self.page = max_page
                self.next_button.disabled = True
            self.prev_button.disabled = False
            await self.update_embed(interaction)

        async def on_timeout(self):
            # Disable buttons when timed out
            for child in self.children:
                child.disabled = True
            # Try to edit the message to disable buttons
            try:
                # self.message is set after sending
                await self.message.edit(view=self)
            except Exception:
                pass

    @app_commands.command(name="leaderboard", description="View the top 20 richest members")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        users = await self.fetch_top_users()
        if not users:
            return await interaction.followup.send("❌ There are no rich people yet!")

        view = self.LeaderboardView(self, users, interaction.guild, timeout=60)
        embed = self.create_embed(interaction.guild, users, page=0, per_page=8)
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message  # Save message to update buttons on timeout

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx):
        users = await self.fetch_top_users()
        if not users:
            return await ctx.send("❌ There are no rich people yet!")

        view = self.LeaderboardView(self, users, ctx.guild, timeout=60)
        embed = self.create_embed(ctx.guild, users, page=0, per_page=8)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
