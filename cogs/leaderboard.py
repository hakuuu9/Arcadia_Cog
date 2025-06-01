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
        # Fetch top 100 users to allow buffer for pagination
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

    async def show_leaderboard(self, target, guild, users, author_id):
        class LeaderboardView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.message = None

            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except Exception as e:
                        print(f"[Leaderboard] Timeout edit failed: {e}")

        view = LeaderboardView()

        prev_button = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.gray, custom_id="prev")
        next_button = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.gray, custom_id="next")

        prev_button.disabled = True
        if len(users) <= 8:
            next_button.disabled = True

        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != author_id:
                return await interaction.response.send_message("This is not your interaction.", ephemeral=True)

            if interaction.data["custom_id"] == "prev":
                if view.page > 0:
                    view.page -= 1
            elif interaction.data["custom_id"] == "next":
                if (view.page + 1) * 8 < len(users):
                    view.page += 1

            new_embed = self.generate_embed(guild, users, view.page)
            prev_button.disabled = (view.page == 0)
            next_button.disabled = (view.page + 1) * 8 >= len(users)

            await interaction.response.edit_message(embed=new_embed, view=view)

        prev_button.callback = button_callback
        next_button.callback = button_callback

        view.add_item(prev_button)
        view.add_item(next_button)

        embed = self.generate_embed(guild, users, view.page)
        view.message = await target.send(embed=embed, view=view)

    @app_commands.command(name="leaderboard", description="View the top richest members")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        users = await self.fetch_top_users()
        if not users:
            return await interaction.followup.send("❌ There are no rich people yet!")
        await self.show_leaderboard(interaction.followup, interaction.guild, users, interaction.user.id)

    @commands.command(name="leaderboard")
    async def leaderboard_prefix(self, ctx):
        users = await self.fetch_top_users()
        if not users:
            return await ctx.send("❌ There are no rich people yet!")
        await self.show_leaderboard(ctx, ctx.guild, users, ctx.author.id)

    def cog_unload(self):
        self.client.close()
        print("Leaderboard MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
