import discord
from discord.ext import commands
import motor.motor_asyncio

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Setup your MongoDB client and collection
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.mongo_client["your_database_name"]
        self.collection = self.db["sticky_messages"]

    # Check if user has manage_messages permission (staff only)
    def is_staff(self, ctx):
        return ctx.author.guild_permissions.manage_messages

    @commands.command()
    async def sticky(self, ctx, *, message: str):
        if not self.is_staff(ctx):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return

        existing = await self.collection.find_one({"channel_id": ctx.channel.id})
        if existing:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=5)
            return

        # Send sticky message and save to DB
        sticky_msg = await ctx.send(message)
        await self.collection.insert_one({
            "channel_id": ctx.channel.id,
            "message": message,
            "message_id": sticky_msg.id,
            "author_id": ctx.author.id
        })
        await ctx.send("Sticky message set successfully.", delete_after=5)

    @commands.command()
    async def unsticky(self, ctx):
        if not self.is_staff(ctx):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
            return

        existing = await self.collection.find_one({"channel_id": ctx.channel.id})
        if not existing:
            await ctx.send("There's no sticky message in this channel.", delete_after=5)
            return

        # Delete sticky message from DB and delete message in channel if exists
        try:
            old_msg = await ctx.channel.fetch_message(existing["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        await self.collection.delete_one({"channel_id": ctx.channel.id})
        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Avoid bots & commands
        if message.author.bot:
            return

        # Process commands first so commands still work
        await self.bot.process_commands(message)

        # Check if sticky message exists for this channel
        sticky_data = await self.collection.find_one({"channel_id": message.channel.id})
        if not sticky_data:
            return

        try:
            # Delete old sticky message
            old_msg = await message.channel.fetch_message(sticky_data["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        # Send new sticky message and update DB
        new_msg = await message.channel.send(sticky_data["message"])
        await self.collection.update_one(
            {"channel_id": message.channel.id},
            {"$set": {"message_id": new_msg.id}}
        )

async def setup(bot):
    await bot.add_cog(Sticky(bot))
