import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

TRIO_ID = [879936602414133288, 1275065396705362041, 1092795368556732478]
MODLOG_CHANNEL_ID = 1364839238960549908  # Replace with your modlog channel ID

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users

    @commands.command(name='balance')
    async def balance_text(self, ctx):
        await self.show_balance(ctx.author, ctx)

    @app_commands.command(name='balance', description='Check your coin balance')
    async def balance_slash(self, interaction: discord.Interaction):
        await self.show_balance(interaction.user, interaction)

    async def show_balance(self, user, ctx_or_interaction):
        user_data = self.db.find_one({'_id': str(user.id)})
        balance = user_data['balance'] if user_data and 'balance' in user_data else 0
        emoji = "<:arcadiacoin:1378656679704395796>"
        message = f"Your current balance is ₱{balance:,} {emoji}"

        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(message)
        else:
            await ctx_or_interaction.response.send_message(message)

    @app_commands.command(name='give-money', description='Give coins to a user (Staff Only)')
    @app_commands.describe(
        member='The member to give coins to',
        amount='Amount of coins to give',
        reason='Reason for giving (optional)'
    )
    async def give_money(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "No reason provided"
    ):
        if interaction.user.id not in TRIO_ID:
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be greater than zero.", ephemeral=True)

        # Update balance by member.id (string)
        self.db.update_one(
            {"_id": str(member.id)},
            {"$inc": {"balance": amount}},
            upsert=True
        )

        emoji = "<:arcadiacoin:1378656679704395796>"
        await interaction.response.send_message(
            f"✅ Gave ₱{amount:,} {emoji} to {member.mention}.\n📝 Reason: {reason}"
        )

        try:
            await member.send(f"💰 You received ₱{amount:,} {emoji} from {interaction.user.mention}.\n📝 Reason: {reason}")
        except discord.Forbidden:
            pass

        modlog = interaction.guild.get_channel(MODLOG_CHANNEL_ID)
        if modlog:
            embed = discord.Embed(
                title="💰 Money Given",
                color=discord.Color.green()
            )
            embed.add_field(name="Staff", value=interaction.user.mention, inline=True)
            embed.add_field(name="Target", value=member.mention, inline=True)
            embed.add_field(name="Amount", value=f"₱{amount:,} {emoji}", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"User ID: {member.id}")
            await modlog.send(embed=embed)

    @app_commands.command(name='remove-money', description='Remove coins from a user (Staff Only)')
    @app_commands.describe(
        member='The member to deduct coins from',
        amount='Amount of coins to remove',
        reason='Reason for removal (optional)'
    )
    async def remove_money(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "No reason provided"
    ):
        if interaction.user.id not in TRIO_ID:
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be greater than zero.", ephemeral=True)

        user_data = self.db.find_one({'_id': str(member.id)})
        current_balance = user_data['balance'] if user_data and 'balance' in user_data else 0

        if current_balance < amount:
            return await interaction.response.send_message(
                f"❌ {member.mention} only has ₱{current_balance:,}. Cannot remove ₱{amount:,}.", ephemeral=True
            )

        self.db.update_one(
            {"_id": str(member.id)},
            {"$inc": {"balance": -amount}},
            upsert=True
        )

        emoji = "<:arcadiacoin:1378656679704395796>"
        await interaction.response.send_message(
            f"✅ Removed ₱{amount:,} {emoji} from {member.mention}.\n📝 Reason: {reason}"
        )

        try:
            await member.send(f"⚠️ ₱{amount:,} {emoji} was removed from your balance by {interaction.user.mention}.\n📝 Reason: {reason}")
        except discord.Forbidden:
            pass

        modlog = interaction.guild.get_channel(MODLOG_CHANNEL_ID)
        if modlog:
            embed = discord.Embed(
                title="💸 Money Removed",
                color=discord.Color.red()
            )
            embed.add_field(name="Staff", value=interaction.user.mention, inline=True)
            embed.add_field(name="Target", value=member.mention, inline=True)
            embed.add_field(name="Amount", value=f"₱{amount:,} {emoji}", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"User ID: {member.id}")
            await modlog.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Balance(bot))
