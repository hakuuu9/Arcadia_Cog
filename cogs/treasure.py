import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
import random
from config import MONGO_URL

# ========= CONSTANTS (edit to your server) =========
ARCADIA_COIN_EMOJI_ID = 1378662273836384256   # <a:arcadiacoin:{ID}>
CHEST_ANNOUNCE_EMOJI_ID = 1408390807836430417 # <a:moneydrop:{ID}> (reusing your animated)
TREASURE_EMBED_COLOR = 0xC6A969               # gold-ish
TREASURE_MIN = 500
TREASURE_MAX = 12000
TREASURE_ADMIN_ROLE_ID = 1347181345922748456  # staff role allowed to run commands

# Auto-drop every 60 minutes
TREASURE_DROP_INTERVAL_MIN = 60

class Treasure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.config_db = self.client.hxhbot.config
        self.users_db = self.client.hxhbot.users
        self.treasure_channels = self.config_db.treasure_channels  # {"_id":"treasure_channels","channel_ids":[...]}
        self.treasure_task.start()
        print("Treasure Cog initialized and connected to MongoDB.")

    def cog_unload(self):
        self.treasure_task.cancel()
        self.client.close()
        print("Treasure MongoDB client closed.")

    # ===== UI Components =====
    class TreasureClaimButton(discord.ui.Button):
        """Button to claim a treasure chest."""
        def __init__(self, parent_cog, amount: int, drop_message: discord.Message):
            super().__init__(label="Open Chest", style=discord.ButtonStyle.primary, emoji="🧰")
            self.parent_cog = parent_cog
            self.amount = amount
            self.drop_message = drop_message
            self.claimed = False

        async def callback(self, interaction: discord.Interaction):
            if self.claimed:
                await interaction.response.send_message("Someone already opened this chest!", ephemeral=True)
                return

            self.claimed = True
            # Disable all components
            self.view.stop()
            for item in self.view.children:
                item.disabled = True

            # Update DB balance
            self.parent_cog.users_db.update_one(
                {"_id": str(interaction.user.id)},
                {"$inc": {"balance": self.amount}},
                upsert=True
            )

            # Show claimed embed
            claimed_embed = self.parent_cog._create_treasure_claimed_embed(interaction.user, self.amount)
            await self.drop_message.edit(embed=claimed_embed, view=self.view)

            await interaction.response.send_message(
                f"🎉 You opened the chest and found **₱{self.amount:,} <a:arcadiacoin:{ARCADIA_COIN_EMOJI_ID}>**!",
                ephemeral=True
            )

    class TreasureView(discord.ui.View):
        """View for treasure chest with a 10s timeout."""
        def __init__(self, parent_cog, drop_message: discord.Message, amount: int):
            super().__init__(timeout=10.0)
            self.parent_cog = parent_cog
            self.drop_message = drop_message
            self.add_item(parent_cog.TreasureClaimButton(parent_cog, amount, drop_message))

        async def on_timeout(self):
            # If nobody claimed in time, mark as expired
            if not any(getattr(child, "claimed", False) for child in self.children):
                for item in self.children:
                    item.disabled = True
                    item.label = "Expired"
                    item.style = discord.ButtonStyle.danger
                await self.drop_message.edit(content="This treasure chest has expired.", view=self)

    # ===== Embeds =====
    def _create_treasure_drop_embed(self, amount_hint: bool = False) -> discord.Embed:
        hint = " (big haul!)" if amount_hint else ""
        return discord.Embed(
            description=(
                f"<a:moneydrop:{CHEST_ANNOUNCE_EMOJI_ID}> **A Treasure Chest appeared{hint}!**\n"
                "Be the first to press **Open Chest** to claim the loot!"
            ),
            color=TREASURE_EMBED_COLOR
        )

    def _create_treasure_claimed_embed(self, user: discord.Member, amount: int) -> discord.Embed:
        embed = discord.Embed(
            title="Treasure Claimed!",
            description=(
                f"🗝️ **{user.display_name}** opened the chest and found **₱{amount:,}** "
                f"<a:arcadiacoin:{ARCADIA_COIN_EMOJI_ID}>!"
            ),
            color=TREASURE_EMBED_COLOR
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    # ===== Core Send Logic =====
    async def _send_treasure_drop(self, channel: discord.TextChannel, min_amt: int = TREASURE_MIN, max_amt: int = TREASURE_MAX):
        amount = random.randint(min_amt, max_amt)
        amount_hint = amount >= int(max_amt * 0.85)  # fun hint on big chests
        embed = self._create_treasure_drop_embed(amount_hint=amount_hint)
        drop_message = await channel.send(embed=embed)
        view = self.TreasureView(self, drop_message, amount)
        await drop_message.edit(view=view)
        await view.wait()

    # ===== Auto Task (every 60 mins) =====
    @tasks.loop(minutes=TREASURE_DROP_INTERVAL_MIN)
    async def treasure_task(self):
        await self.bot.wait_until_ready()
        doc = self.treasure_channels.find_one({"_id": "treasure_channels"})
        if not doc or not doc.get("channel_ids"):
            # No configured channels; nothing to drop
            return
        # Pick a random configured channel
        channel_id = random.choice(doc["channel_ids"])
        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                await self._send_treasure_drop(channel)
            except Exception as e:
                print(f"[Treasure] Error sending drop in {channel_id}: {e}")

    # ===== Slash Commands (Staff) =====
    @app_commands.command(name="treasuredrop", description="(Staff) Drop a treasure chest now, optionally in a specific channel.")
    @app_commands.checks.has_role(TREASURE_ADMIN_ROLE_ID)
    async def treasuredrop(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        min_amount: app_commands.Range[int, 1] = TREASURE_MIN,
        max_amount: app_commands.Range[int, 1] = TREASURE_MAX
    ):
        if min_amount > max_amount:
            await interaction.response.send_message("Min amount cannot be greater than max amount.", ephemeral=True)
            return
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("Please run this in a text channel or provide one.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🧰 Dropping a treasure chest in {target_channel.mention} ...",
            ephemeral=True
        )
        await self._send_treasure_drop(target_channel, min_amount, max_amount)

    @app_commands.command(name="treasure_channel_add", description="(Staff) Allow treasure chests in a channel (auto-drops every 60 mins).")
    @app_commands.checks.has_role(TREASURE_ADMIN_ROLE_ID)
    async def treasure_channel_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.treasure_channels.update_one(
            {"_id": "treasure_channels"},
            {"$addToSet": {"channel_ids": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ {channel.mention} added for treasure auto-drops.", color=TREASURE_EMBED_COLOR),
            ephemeral=True
        )

    @app_commands.command(name="treasure_channel_remove", description="(Staff) Remove a channel from treasure auto-drops.")
    @app_commands.checks.has_role(TREASURE_ADMIN_ROLE_ID)
    async def treasure_channel_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.treasure_channels.update_one(
            {"_id": "treasure_channels"},
            {"$pull": {"channel_ids": channel.id}}
        )
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ {channel.mention} removed from treasure auto-drops.", color=TREASURE_EMBED_COLOR),
            ephemeral=True
        )

    @app_commands.command(name="treasure_channel_list", description="(Staff) List channels configured for treasure auto-drops.")
    @app_commands.checks.has_role(TREASURE_ADMIN_ROLE_ID)
    async def treasure_channel_list(self, interaction: discord.Interaction):
        doc = self.treasure_channels.find_one({"_id": "treasure_channels"}) or {}
        ids = doc.get("channel_ids", [])
        if not ids:
            msg = "No channels configured for treasure auto-drops."
        else:
            mentions = []
            for cid in ids:
                ch = self.bot.get_channel(cid)
                mentions.append(ch.mention if ch else f"`{cid}` (not found)")
            msg = "Configured channels:\n- " + "\n- ".join(mentions)
        await interaction.response.send_message(
            embed=discord.Embed(description=msg, color=TREASURE_EMBED_COLOR),
            ephemeral=True
        )

    @app_commands.command(name="treasure_channel_clear", description="(Staff) Clear all treasure auto-drop channels and stop drops.")
    @app_commands.checks.has_role(TREASURE_ADMIN_ROLE_ID)
    async def treasure_channel_clear(self, interaction: discord.Interaction):
        self.treasure_channels.delete_one({"_id": "treasure_channels"})
        await interaction.response.send_message(
            embed=discord.Embed(description="✅ Cleared all treasure auto-drop channels.", color=TREASURE_EMBED_COLOR),
            ephemeral=True
        )

    # Optional: generic command error handler for this cog
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("You don’t have permission to use this.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("You don’t have permission to use this.", ephemeral=True)
        else:
            try:
                await interaction.response.send_message("Something went wrong executing that command.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("Something went wrong executing that command.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Treasure(bot))
