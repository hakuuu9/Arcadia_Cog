import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import time
from config import MONGO_URL

class EconomyMultiplier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users
        self.mult_db = self.client.hxhbot.multipliers
        self._cooldowns = {}  # user_id: last_coin_time

    # Passive earning with cooldown and multiplier only if set
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        now = time.time()
        cooldown = 60  # seconds

        last_earn = self._cooldowns.get(user_id, 0)
        if now - last_earn < cooldown:
            print(f"[Cooldown] {message.author} still cooling down ({now - last_earn:.1f}/{cooldown}s)")
            return

        multiplier = await self.get_user_multiplier(message)
        print(f"[DEBUG] {message.author} | Multiplier: {multiplier} | Cooldown Ready")

        if multiplier == 1:
            return  # no multiplier set, do not give coins

        self._cooldowns[user_id] = now

        base_coins = 10
        coins_to_add = int(base_coins * multiplier)
        self.db.update_one({'_id': str(user_id)}, {'$inc': {'balance': coins_to_add}}, upsert=True)

        print(f"[Economy] {message.author} earned {coins_to_add} coins (x{multiplier})")

    async def get_user_multiplier(self, message):
        multiplier = 1

        # Check channel multiplier
        channel_data = self.mult_db.find_one({'_id': str(message.channel.id)})
        if channel_data and channel_data.get('multiplier', 1) > multiplier:
            multiplier = channel_data['multiplier']

        # Check role multipliers
        for role in message.author.roles:
            role_data = self.mult_db.find_one({'_id': str(role.id)})
            if role_data and role_data.get('multiplier', 1) > multiplier:
                multiplier = role_data['multiplier']

        return multiplier

    # ---------- PREFIX COMMANDS ----------

    @commands.command(name="multiset")
    @commands.has_permissions(administrator=True)
    async def multiset(self, ctx, target: str, multiplier: str):
        target_obj = None
        if ctx.message.role_mentions:
            target_obj = ctx.message.role_mentions[0]
        elif ctx.message.channel_mentions:
            target_obj = ctx.message.channel_mentions[0]
        else:
            return await ctx.send("❌ Please mention a valid role or channel.")

        if not multiplier.endswith('x'):
            return await ctx.send("❌ Please specify the multiplier like `2x` or `1.5x`.")

        try:
            value = float(multiplier[:-1])
        except ValueError:
            return await ctx.send("❌ Invalid multiplier value.")

        if value <= 0:
            return await ctx.send("❌ Multiplier must be greater than 0.")

        target_type = "role" if isinstance(target_obj, discord.Role) else "channel"
        self.mult_db.update_one(
            {'_id': str(target_obj.id)},
            {'$set': {'type': target_type, 'multiplier': value}},
            upsert=True
        )
        await ctx.send(f"✅ Multiplier for {target_obj.mention} set to **x{value}**.")

    @commands.command(name="multishow")
    async def multishow(self, ctx):
        data = list(self.mult_db.find())
        if not data:
            return await ctx.send("📄 No multipliers set yet.")

        lines = []
        for entry in data:
            target_type = entry['type']
            target_id = int(entry['_id'])
            multiplier = entry['multiplier']

            if target_type == "channel":
                target = ctx.guild.get_channel(target_id)
                name = f"#{target.name}" if target else f"Deleted channel ({target_id})"
            else:
                target = ctx.guild.get_role(target_id)
                name = f"@{target.name}" if target else f"Deleted role ({target_id})"

            lines.append(f"{name}: x{multiplier}")

        message = "**📊 Current Coin Multipliers:**\n" + "\n".join(lines)
        await ctx.send(message)

    @commands.command(name="multiremove")
    @commands.has_permissions(administrator=True)
    async def multiremove(self, ctx, target: str):
        target_obj = None
        if ctx.message.role_mentions:
            target_obj = ctx.message.role_mentions[0]
        elif ctx.message.channel_mentions:
            target_obj = ctx.message.channel_mentions[0]
        else:
            return await ctx.send("❌ Please mention a valid role or channel to remove multiplier.")

        self.mult_db.delete_one({'_id': str(target_obj.id)})
        await ctx.send(f"✅ Multiplier for {target_obj.mention} has been removed.")

    # ---------- SLASH COMMANDS ----------

    @app_commands.command(name="multiset", description="Set coin multiplier for a channel or role (admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        multiplier="Multiplier value like 1x or 2x",
        role="Role to set multiplier for",
        channel="Channel to set multiplier for"
    )
    async def multiset_slash(self, interaction: discord.Interaction, multiplier: str, role: discord.Role = None, channel: discord.TextChannel = None):
        if (role is None and channel is None) or (role is not None and channel is not None):
            return await interaction.response.send_message("❌ Please provide exactly one of `role` or `channel`.", ephemeral=True)

        target_obj = role if role else channel

        if not multiplier.endswith('x'):
            return await interaction.response.send_message("❌ Please specify the multiplier like `2x` or `1.5x`.", ephemeral=True)

        try:
            value = float(multiplier[:-1])
        except ValueError:
            return await interaction.response.send_message("❌ Invalid multiplier value.", ephemeral=True)

        if value <= 0:
            return await interaction.response.send_message("❌ Multiplier must be greater than 0.", ephemeral=True)

        target_type = "role" if isinstance(target_obj, discord.Role) else "channel"
        self.mult_db.update_one(
            {'_id': str(target_obj.id)},
            {'$set': {'type': target_type, 'multiplier': value}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Multiplier for {target_obj.mention} set to **x{value}**.")

    @app_commands.command(name="multishow", description="Show all set coin multipliers for channels and roles.")
    async def multishow_slash(self, interaction: discord.Interaction):
        data = list(self.mult_db.find())
        if not data:
            return await interaction.response.send_message("📄 No multipliers set yet.")

        lines = []
        for entry in data:
            target_type = entry['type']
            target_id = int(entry['_id'])
            multiplier = entry['multiplier']

            if target_type == "channel":
                target = interaction.guild.get_channel(target_id)
                name = f"#{target.name}" if target else f"Deleted channel ({target_id})"
            else:
                target = interaction.guild.get_role(target_id)
                name = f"@{target.name}" if target else f"Deleted role ({target_id})"

            lines.append(f"{name}: x{multiplier}")

        message = "**📊 Current Coin Multipliers:**\n" + "\n".join(lines)
        await interaction.response.send_message(message)

    @app_commands.command(name="multiremove", description="Remove coin multiplier for a channel or role (admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        role="Role to remove multiplier for",
        channel="Channel to remove multiplier for"
    )
    async def multiremove_slash(self, interaction: discord.Interaction, role: discord.Role = None, channel: discord.TextChannel = None):
        if (role is None and channel is None) or (role is not None and channel is not None):
            return await interaction.response.send_message("❌ Please provide exactly one of `role` or `channel` to remove multiplier.", ephemeral=True)

        target_obj = role if role else channel
        self.mult_db.delete_one({'_id': str(target_obj.id)})

        await interaction.response.send_message(f"✅ Multiplier for {target_obj.mention} has been removed.")

async def setup(bot):
    await bot.add_cog(EconomyMultiplier(bot))
