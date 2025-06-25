import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import config
import random
import datetime

MARRY_LINES = [
    "💍 {user1} got down on one knee and proposed to {user2}... and they said **YES**!",
    "👰 {user1} and {user2} just got engaged! Wedding bells are ringing!",
    "💘 {user1} and {user2} are now officially Discord soulmates!",
]

RING_GIFS = [
    "https://media.tenor.com/7V2KbWcMIWkAAAAC/married-anime.gif",
    "https://media.tenor.com/G5W6wA_3giIAAAAC/anime-couple-married.gif",
    "https://media.tenor.com/NxRuTnmtU-8AAAAd/yes-anime.gif",
    "https://media.tenor.com/LxWYPwTm9asAAAAd/anime-ring.gif",
    "https://media.tenor.com/EbrYlh6KMwYAAAAd/wedding-anime.gif"
]

class MarryView(discord.ui.View):
    def __init__(self, bot, author: discord.Member, target: discord.Member, db):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author
        self.target = target
        self.db = db

    @discord.ui.button(label="💍 Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            return await interaction.response.send_message("This isn't your proposal to accept!", ephemeral=True)

        self.db.insert_one({
            "user1_id": str(self.author.id),
            "user2_id": str(self.target.id),
            "married_at": datetime.datetime.utcnow()
        })

        line = random.choice(MARRY_LINES).format(user1=self.author.mention, user2=self.target.mention)
        gif = random.choice(RING_GIFS)

        await interaction.response.edit_message(content=f"💘 {self.target.mention} said **YES** to {self.author.mention}!", view=None)
        await interaction.channel.send(f"{line}\n{gif}")

    @discord.ui.button(label="💔 Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            return await interaction.response.send_message("You can't decline someone else's proposal!", ephemeral=True)

        await interaction.response.edit_message(content=f"💔 {self.target.mention} declined the proposal from {self.author.mention}.", view=None)


class Marry(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(config.MONGO_URL)
        self.db = self.client["discord"]["marriages"]

    # /marry and $marry
    @commands.command(name="marry")
    async def marry_prefix(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("❌ You need to mention someone to marry!")
        if member == ctx.author:
            return await ctx.send("💔 You can’t marry yourself!")

        existing = self.db.find_one({
            "$or": [
                {"user1_id": str(ctx.author.id), "user2_id": str(member.id)},
                {"user1_id": str(member.id), "user2_id": str(ctx.author.id)}
            ]
        })
        if existing:
            return await ctx.send("💍 You two are already married!")

        view = MarryView(self.bot, ctx.author, member, self.db)
        await ctx.send(f"{member.mention}, will you marry {ctx.author.mention}?", view=view)

    @app_commands.command(name="marry", description="Propose to someone and get married 💍")
    @app_commands.describe(member="The person you want to marry")
    async def marry_slash(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("💔 You can’t marry yourself!", ephemeral=True)

        existing = self.db.find_one({
            "$or": [
                {"user1_id": str(interaction.user.id), "user2_id": str(member.id)},
                {"user1_id": str(member.id), "user2_id": str(interaction.user.id)}
            ]
        })
        if existing:
            return await interaction.response.send_message("💍 You two are already married!", ephemeral=True)

        view = MarryView(self.bot, interaction.user, member, self.db)
        await interaction.response.send_message(f"{member.mention}, will you marry {interaction.user.mention}?", view=view)

    # /divorce and $divorce
    @commands.command(name="divorce")
    async def divorce_prefix(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("❌ Mention the person you want to divorce.")
        result = self.db.find_one_and_delete({
            "$or": [
                {"user1_id": str(ctx.author.id), "user2_id": str(member.id)},
                {"user1_id": str(member.id), "user2_id": str(ctx.author.id)}
            ]
        })

        if result:
            await ctx.send(f"💔 {ctx.author.mention} and {member.mention} are now divorced.")
        else:
            await ctx.send("❌ You are not married to that person.")

    @app_commands.command(name="divorce", description="Divorce someone you're married to 💔")
    @app_commands.describe(member="The person you want to divorce")
    async def divorce_slash(self, interaction: discord.Interaction, member: discord.Member):
        result = self.db.find_one_and_delete({
            "$or": [
                {"user1_id": str(interaction.user.id), "user2_id": str(member.id)},
                {"user1_id": str(member.id), "user2_id": str(interaction.user.id)}
            ]
        })

        if result:
            await interaction.response.send_message(f"💔 {interaction.user.mention} and {member.mention} are now divorced.")
        else:
            await interaction.response.send_message("❌ You are not married to that person.", ephemeral=True)

    # /marriedlist and $marriedlist
    @commands.command(name="marriedlist")
    async def married_list_prefix(self, ctx):
        marriages = list(self.db.find({
            "$or": [
                {"user1_id": str(ctx.author.id)},
                {"user2_id": str(ctx.author.id)}
            ]
        }))

        if not marriages:
            return await ctx.send("💤 You're not married to anyone...")

        partners = []
        for m in marriages:
            partner_id = m["user2_id"] if m["user1_id"] == str(ctx.author.id) else m["user1_id"]
            partner = await self.bot.fetch_user(int(partner_id))
            partners.append(partner.mention)

        await ctx.send(f"💞 You're married to: {', '.join(partners)}")

    @app_commands.command(name="marriedlist", description="See who you're married to 💕")
    async def married_list_slash(self, interaction: discord.Interaction):
        marriages = list(self.db.find({
            "$or": [
                {"user1_id": str(interaction.user.id)},
                {"user2_id": str(interaction.user.id)}
            ]
        }))

        if not marriages:
            return await interaction.response.send_message("💤 You're not married to anyone...", ephemeral=True)

        partners = []
        for m in marriages:
            partner_id = m["user2_id"] if m["user1_id"] == str(interaction.user.id) else m["user1_id"]
            partner = await self.bot.fetch_user(int(partner_id))
            partners.append(partner.mention)

        await interaction.response.send_message(f"💞 You're married to: {', '.join(partners)}")

    # /marriedserver and $marriedserver
    @commands.command(name="marriedserver")
    async def married_server_prefix(self, ctx):
        await self.show_server_marriages(ctx)

    @app_commands.command(name="marriedserver", description="Show all server members who are married 💞")
    async def married_server_slash(self, interaction: discord.Interaction):
        await self.show_server_marriages(interaction)

    async def show_server_marriages(self, ctx_or_interaction):
        guild = ctx_or_interaction.guild if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.guild
        marriages = list(self.db.find())

        valid_pairs = []
        for m in marriages:
            user1 = guild.get_member(int(m["user1_id"]))
            user2 = guild.get_member(int(m["user2_id"]))
            if user1 and user2:
                valid_pairs.append(f"💍 {user1.mention} ❤️ {user2.mention}")

        msg = "**Server Marriages:**\n" + "\n".join(valid_pairs) if valid_pairs else "💤 No one in this server is married yet."

        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(msg)
        else:
            await ctx_or_interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Marry(bot))
