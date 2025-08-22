import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime
import random
import asyncio
from config import MONGO_URL

# Constants for the custom emoji, embed color, money range, and admin role ID
MONEYDROP_EMOJI_ID = 1408390807836430417
ARCADIA_COIN_EMOJI_ID = 1378662273836384256
EMBED_COLOR = 0xE1D3C4  # Beige color
MIN_MONEY = 200
MAX_MONEY = 5000
ARCDROP_ADMIN_ROLE_ID = 1347181345922748456

class Arcdrop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.config_db = self.client.hxhbot.config
        self.users_db = self.client.hxhbot.users
        self.channels_collection = self.config_db.arcdrop_channels
        self.drop_task.start()
        print("Arcdrop Cog initialized and connected to MongoDB.")

    def cog_unload(self):
        """Stops the background task when the cog is unloaded."""
        self.drop_task.cancel()
        self.client.close()
        print("Arcdrop MongoDB client closed.")

    async def _add_channel_to_db(self, channel_id: int):
        """Adds a channel ID to the database for arcdrop events."""
        self.channels_collection.update_one(
            {"_id": "arcdrop_channels"},
            {"$addToSet": {"channel_ids": channel_id}},
            upsert=True
        )

    async def _remove_channel_from_db(self, channel_id: int):
        """Removes a channel ID from the database."""
        self.channels_collection.update_one(
            {"_id": "arcdrop_channels"},
            {"$pull": {"channel_ids": channel_id}}
        )

    class ClaimButton(discord.ui.Button):
        """A custom button to handle the claim logic."""
        def __init__(self, arcdrop_cog, money_amount, drop_message):
            super().__init__(label="Claim", style=discord.ButtonStyle.green)
            self.arcdrop_cog = arcdrop_cog
            self.money_amount = money_amount
            self.drop_message = drop_message
            self.claimed = False

        async def callback(self, interaction: discord.Interaction):
            """Handles the button claim action."""
            if self.claimed:
                await interaction.response.send_message("Someone else already claimed this drop!", ephemeral=True)
                return

            self.claimed = True
            
            # Disable the button for all other users
            self.view.stop()
            for item in self.view.children:
                item.disabled = True

            claimed_embed = self.arcdrop_cog._create_claimed_embed(interaction.user, self.money_amount)
            await self.drop_message.edit(embed=claimed_embed, view=self.view)
            
            # Update the user's balance in the database
            self.arcdrop_cog.users_db.update_one(
                {"_id": str(interaction.user.id)},
                {"$inc": {"balance": self.money_amount}},
                upsert=True
            )
            
            # Acknowledge the claim to the user
            await interaction.response.send_message(
                f"🎉 You successfully claimed **₱{self.money_amount:,} <a:arcadiacoin:{ARCADIA_COIN_EMOJI_ID}>**!", ephemeral=True
            )
            

    class ArcdropView(discord.ui.View):
        """A View to hold the claim button with a 10-second timeout."""
        def __init__(self, arcdrop_cog, drop_message, money_amount):
            super().__init__(timeout=10.0)
            self.arcdrop_cog = arcdrop_cog
            self.drop_message = drop_message
            self.add_item(self.arcdrop_cog.ClaimButton(arcdrop_cog, money_amount, drop_message))

        async def on_timeout(self):
            """
            This method is automatically called when the view's timeout is reached.
            It handles the case where no one claims the money within the 10-second window.
            """
            if not any(item.claimed for item in self.children):
                for item in self.children:
                    item.disabled = True
                    item.label = "Expired"
                    item.style = discord.ButtonStyle.danger
                await self.drop_message.edit(content="This drop has expired.", view=self)

    def _create_drop_embed(self) -> discord.Embed:
        """Creates the initial embed for the money drop."""
        embed = discord.Embed(
            description=f"<a:moneydrop:{MONEYDROP_EMOJI_ID}> A wild stash of Arcadia Tokens has appeared! Grab them before they vanish!",
            color=EMBED_COLOR
        )
        return embed

    def _create_claimed_embed(self, user: discord.Member, amount: int) -> discord.Embed:
        """Creates the embed to show after the money has been claimed."""
        embed = discord.Embed(
            title="Arcadia Tokens Claimed!",
            description=f"🎉 **{user.display_name}** has claimed the stash of **₱{amount:,} <a:arcadiacoin:{ARCADIA_COIN_EMOJI_ID}>**!",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    @tasks.loop(minutes=60)
    async def drop_task(self):
        """A background task that drops Arcadia Tokens in a random configured channel."""
        await self.bot.wait_until_ready()
        
        channels_doc = self.channels_collection.find_one({"_id": "arcdrop_channels"})
        if not channels_doc or not channels_doc.get("channel_ids"):
            print("No channels configured for Arcadia drops. Task skipped.")
            return

        channel_ids = channels_doc["channel_ids"]
        channel_id = random.choice(channel_ids)
        channel = self.bot.get_channel(channel_id)

        if not channel:
            print(f"Could not find channel with ID {channel_id}. It may have been deleted.")
            return
        
        money_amount = random.randint(MIN_MONEY, MAX_MONEY)
        drop_embed = self._create_drop_embed()
        
        drop_message = await channel.send(embed=drop_embed)
        view = self.ArcdropView(self, drop_message, money_amount)
        await drop_message.edit(view=view)
        await view.wait()
        
    @app_commands.command(name="arcdrop_channel_add", description="Adds a channel to the list for random Arcadia token drops.")
    @app_commands.checks.has_role(ARCDROP_ADMIN_ROLE_ID)
    async def arcdrop_channel_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Adds a channel to the list for random Arcadia token drops."""
        await self._add_channel_to_db(channel.id)
        embed = discord.Embed(
            description=f"✅ {channel.mention} has been added to the list of channels for Arcadia token drops.",
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="arcdrop_channel_remove", description="Removes a channel from the list for random Arcadia token drops.")
    @app_commands.checks.has_role(ARCDROP_ADMIN_ROLE_ID)
    async def arcdrop_channel_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Removes a channel from the list for random Arcadia token drops."""
        await self._remove_channel_from_db(channel.id)
        embed = discord.Embed(
            description=f"✅ {channel.mention} has been removed from the list of channels for Arcadia token drops.",
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="arcdrop_channel_stop", description="Removes all channels from the list for random Arcadia token drops.")
    @app_commands.checks.has_role(ARCDROP_ADMIN_ROLE_ID)
    async def arcdrop_channel_stop(self, interaction: discord.Interaction):
        """Removes all channels from the list for random Arcadia token drops."""
        self.channels_collection.delete_one({"_id": "arcdrop_channels"})
        embed = discord.Embed(
            description="✅ All channels have been removed from the list for Arcadia token drops. The background task is now stopped.",
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Arcdrop(bot))
