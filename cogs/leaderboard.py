import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from pymongo import MongoClient
from config import MONGO_URL

class LeaderboardView(View):
    def __init__(self, pages, author: discord.User):
        super().__init__(timeout=300)  # 5 minutes
        self.pages = pages
        self.current = 0
        self.author = author

    async def update_embed(self, interaction):
        for child in self.children:
            child.disabled = False

        if self.current == 0:
            self.children[0].disabled = True
        if self.current == len(self.pages) - 1:
            self.children[1].disabled = True

        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("This is not your leaderboard session.", ephemeral=True)
        self.current -= 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("This is not your leaderboard session.", ephemeral=True)
        self.current += 1
        await self.update_embed(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        # Edit message to disable buttons
        message = self.message
        await message.edit(view=self)


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def generate_leaderboard_pages(self, guild: discord.Guild):
        top_users = list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(100))

        if not top_users:
            return []

        pages = []
        quote = "*\"The battlefield may be silent, but the richest warriors stand tall.\"*"
        crown = "<:11564whitecrown:1378027038614491226>"

        for i in range(0, len(top_users), 8):
            embed = discord.Embed(
                title=f"{crown} ARCADIA LEADERBOARD {crown}",
                description=quote + "\n\n",
                color=discord.Color.dark_gold()
            )

            chunk = top_users[i:i+8]
            for index, user in enumerate(chunk, start=i+1):
                user_id = int(user["_id"])
                member = guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                balance = user.get("balance", 0)
                embed.description += f"**{index}.** {name} — ₱{balance:,}\n\n"

            pages.append(embed)

        return pages

    async def send_leaderboard(self, ctx_or_interaction, is_slash: bool = False):
        guild = ctx_or_interaction.guild
        author = ctx_or_interaction.user if is_slash else ctx_or_interaction.author

        pages = await self.generate_leaderboard_pages(guild)
        if not pages:
            msg = "❌ There are no rich people yet!"
            if is_slash:
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        view = LeaderboardView(pages, author)
        if is_slash:
            await ctx_or_interaction.response.defer()
            msg = await ctx_or_interaction.followup.send(embed=pages[0], view=view)
        else:
            msg = await ctx_or_interaction.send(embed=pages[0], view=view)

        view.message = msg

    @app_commands.command(name="leaderboard", description="View the top richest members in Arcadia")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await self.send_leaderboard(interaction, is_slash=True)

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx):
        await self.send_leaderboard(ctx, is_slash=False)

    def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
