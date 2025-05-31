import discord
from discord.ext import commands
from discord import app_commands
import motor.motor_asyncio
from config import MONGO_URL

class StickyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        self.db = self.client["sticky_db"]
        self.collection = self.db["stickies"]

    # Fetch sticky data
    async def get_sticky(self, channel_id: int):
        sticky = await self.collection.find_one({"channel_id": int(channel_id)})
        print(f"[get_sticky] Fetched sticky for channel {channel_id}: {sticky}")
        return sticky

    # Save sticky data
    async def save_sticky(self, channel_id: int, message_id: int, content: str, author_id: int):
        print(f"[save_sticky] Saving sticky for channel {channel_id}")
        await self.collection.update_one(
            {"channel_id": int(channel_id)},
            {"$set": {
                "message_id": message_id,
                "content": content,
                "author_id": author_id
            }},
            upsert=True
        )

    # Delete sticky data
    async def delete_sticky(self, channel_id: int):
        print(f"[delete_sticky] Attempting to delete sticky for channel {channel_id}")
        result = await self.collection.delete_one({"channel_id": int(channel_id)})
        print(f"[delete_sticky] Deleted count: {result.deleted_count}")

    # Command: $sticky
    @commands.command(name="sticky", help="Set a sticky message in this channel (Manage Messages required)")
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, ctx, *, message: str):
        existing = await self.get_sticky(ctx.channel.id)
        if existing:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` to remove it first.", delete_after=6)
            return
        
        try:
            sent_msg = await ctx.channel.send(message)
            await self.save_sticky(ctx.channel.id, sent_msg.id, message, ctx.author.id)
            await ctx.send("Sticky message set successfully.", delete_after=6)
        except discord.Forbidden:
            await ctx.send("I don't have permission to send messages in this channel.", delete_after=6)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}", delete_after=6)

    @sticky.error
    async def sticky_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the **Manage Messages** permission to use this command.", delete_after=6)

    # Command: $unsticky
    @commands.command(name="unsticky", help="Remove the sticky message from this channel (Manage Messages required)")
    @commands.has_permissions(manage_messages=True)
    async def unsticky(self, ctx):
        print(f"[unsticky] Command triggered in channel {ctx.channel.id}")
        existing = await self.get_sticky(ctx.channel.id)
        if not existing:
            await ctx.send("There's no sticky message in this channel.", delete_after=6)
            return

        try:
            old_msg = await ctx.channel.fetch_message(existing["message_id"])
            await old_msg.delete()
            print(f"[unsticky] Deleted sticky message with ID {existing['message_id']}")
        except discord.NotFound:
            print(f"[unsticky] Sticky message not found (possibly deleted already)")
            pass

        await self.delete_sticky(ctx.channel.id)
        await ctx.send("Sticky message removed successfully.", delete_after=6)

    @unsticky.error
    async def unsticky_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the **Manage Messages** permission to use this command.", delete_after=6)

    # Slash command: /sticky
    @app_commands.command(name="sticky", description="Set a sticky message in this channel (Manage Messages required)")
    @app_commands.describe(message="The message to stick")
    async def sticky_slash(self, interaction: discord.Interaction, message: str):
        if not interaction.permissions.manage_messages:
            await interaction.response.send_message("You need the **Manage Messages** permission to use this command.", ephemeral=True)
            return

        existing = await self.get_sticky(interaction.channel.id)
        if existing:
            await interaction.response.send_message("There's already a sticky message in this channel. Use `/unsticky` to remove it first.", ephemeral=True)
            return

        try:
            sent_msg = await interaction.channel.send(message)
            await self.save_sticky(interaction.channel.id, sent_msg.id, message, interaction.user.id)
            await interaction.response.send_message("Sticky message set successfully.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to send messages in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    # Slash command: /unsticky
    @app_commands.command(name="unsticky", description="Remove the sticky message from this channel (Manage Messages required)")
    async def unsticky_slash(self, interaction: discord.Interaction):
        if not interaction.permissions.manage_messages:
            await interaction.response.send_message("You need the **Manage Messages** permission to use this command.", ephemeral=True)
            return

        print(f"[unsticky_slash] Command triggered in channel {interaction.channel.id}")
        existing = await self.get_sticky(interaction.channel.id)
        if not existing:
            await interaction.response.send_message("There's no sticky message in this channel.", ephemeral=True)
            return

        try:
            old_msg = await interaction.channel.fetch_message(existing["message_id"])
            await old_msg.delete()
            print(f"[unsticky_slash] Deleted sticky message with ID {existing['message_id']}")
        except discord.NotFound:
            print("[unsticky_slash] Sticky message not found (possibly already deleted)")
            pass

        await self.delete_sticky(interaction.channel.id)
        await interaction.response.send_message("Sticky message removed successfully.", ephemeral=True)

    # Auto-resend sticky on new message
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        existing = await self.get_sticky(message.channel.id)
        if not existing:
            return

        try:
            old_msg = await message.channel.fetch_message(existing["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            print("[on_message] Previous sticky message already deleted")

        new_msg = await message.channel.send(existing["content"])
        await self.save_sticky(message.channel.id, new_msg.id, existing["content"], existing["author_id"])
        print(f"[on_message] Resent sticky in channel {message.channel.id}")

async def setup(bot):
    await bot.add_cog(StickyCog(bot))
