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
        self.embed_color = discord.Color.from_rgb(0, 0, 0)
        self.title = "🏆 ARCADIA LEADERBOARD 🏆"
        self.quote = "_“Fortune favors the bold. Here are the richest among us.”_"

    async def fetch_top_users(self):
        # Fetch top 100 users to allow some buffer for pagination
        return list(self.db.find({"balance": {"$exists": True}}).sort("balance", -1).limit(100))

    def generate_embed(self, guild: discord.Guild, users, page: int, per_page=8):
        start = page * per_page
        end = start + per_page
        selected_users = users[start:end]

        embed = discord.Embed(
            title=self.title,
            description=self.quote + "\n\n",
            color=self.embed_color
        )

        if not selected_users:
            embed.description += "No users found on this page."
            return embed

        for idx, user in enumerate(selected_users, start=start + 1):
            try:
                user_id = int(user["_id"])
                member = guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                balance = user.get("balance", 0)
                embed.description += f"**{idx}.** {name} — ₱{balance:,}\n\n"
            except Exception as e:
                print(f"[Leaderboard] Skipped user #{idx} — Error: {e}")
                continue
        
        embed.set_footer(text=f"Page {page + 1} / {((len(users) - 1) // per_page) + 1}")
        return embed

    @app_commands.command(name="leaderboard", description="View the top richest members")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        users = await self.fetch_top_users()
        if not users:
            return await interaction.followup.send("❌ There are no rich people yet!")

        # Start on page 0
        page = 0
        embed = self.generate_embed(interaction.guild, users, page)

        # Create buttons
        prev_button = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.gray)
        next_button = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.gray)

        # Disable prev initially because we start at page 0
        prev_button.disabled = True
        if len(users) <= 8:
            next_button.disabled = True

        view = discord.ui.View(timeout=180)
        view.add_item(prev_button)
        view.add_item(next_button)

        message = await interaction.followup.send(embed=embed, view=view)

        async def button_callback(inter_btn):
            nonlocal page
            if inter_btn.user.id != interaction.user.id:
                return await inter_btn.response.send_message("This is not your interaction.", ephemeral=True)

            if inter_btn.custom_id == "prev":
                if page > 0:
                    page -= 1
            elif inter_btn.custom_id == "next":
                if (page + 1) * 8 < len(users):
                    page += 1

            # Update embed and buttons
            new_embed = self.generate_embed(interaction.guild, users, page)
            prev_button.disabled = (page == 0)
            next_button.disabled = (page + 1) * 8 >= len(users)

            await inter_btn.response.edit_message(embed=new_embed, view=view)

        prev_button.callback = button_callback
        next_button.callback = button_callback

        # Set custom_ids for buttons for identification
        prev_button.custom_id = "prev"
        next_button.custom_id = "next"

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx):
        users = await self.fetch_top_users()
        if not users:
            return await ctx.send("❌ There are no rich people yet!")

        page = 0
        embed = self.generate_embed(ctx.guild, users, page)

        prev_button = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.gray)
        next_button = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.gray)
        prev_button.disabled = True
        if len(users) <= 8:
            next_button.disabled = True

        view = discord.ui.View(timeout=180)
        view.add_item(prev_button)
        view.add_item(next_button)

        message = await ctx.send(embed=embed, view=view)

        async def button_callback(inter_btn):
            nonlocal page
            # Only allow original ctx author to interact
            if inter_btn.user.id != ctx.author.id:
                return await inter_btn.response.send_message("This is not your interaction.", ephemeral=True)

            if inter_btn.custom_id == "prev":
                if page > 0:
                    page -= 1
            elif inter_btn.custom_id == "next":
                if (page + 1) * 8 < len(users):
                    page += 1

            new_embed = self.generate_embed(ctx.guild, users, page)
            prev_button.disabled = (page == 0)
            next_button.disabled = (page + 1) * 8 >= len(users)

            await inter_btn.response.edit_message(embed=new_embed, view=view)

        prev_button.callback = button_callback
        next_button.callback = button_callback

        prev_button.custom_id = "prev"
        next_button.custom_id = "next"

    def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
