import discord
from discord.ext import commands
import motor.motor_asyncio

class StickyCog(commands.Cog):
    def __init__(self, bot, mongo_uri, db_name):
        self.bot = bot
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.sticky_collection = self.db["sticky_messages"]

    def is_staff():
        async def predicate(ctx):
            return ctx.author.guild_permissions.manage_messages
        return commands.check(predicate)

    @commands.command()
    @is_staff()
    async def sticky(self, ctx, *, message: str):
        existing = await self.sticky_collection.find_one({"channel_id": ctx.channel.id})
        if existing:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=5)
            return

        sticky_msg = await ctx.send(message)
        await self.sticky_collection.insert_one({
            "channel_id": ctx.channel.id,
            "message": message,
            "message_id": sticky_msg.id,
            "author_id": ctx.author.id
        })

        await ctx.send("Sticky message set successfully.", delete_after=5)

    @commands.command()
    @is_staff()
    async def unsticky(self, ctx):
        sticky_data = await self.sticky_collection.find_one({"channel_id": ctx.channel.id})
        if not sticky_data:
            await ctx.send("There's no sticky message in this channel.", delete_after=5)
            return

        try:
            old_msg = await ctx.channel.fetch_message(sticky_data["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        await self.sticky_collection.delete_one({"channel_id": ctx.channel.id})
        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        sticky_data = await self.sticky_collection.find_one({"channel_id": message.channel.id})
        if not sticky_data:
            return

        try:
            old_msg = await message.channel.fetch_message(sticky_data["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        new_msg = await message.channel.send(sticky_data["message"])
        await self.sticky_collection.update_one(
            {"channel_id": message.channel.id},
            {"$set": {"message_id": new_msg.id}}
        )

async def setup(bot):
    # Replace with your MongoDB URI and DB name
    mongo_uri = "your_mongodb_connection_string_here"
    db_name = "your_db_name"
    await bot.add_cog(StickyCog(bot, mongo_uri, db_name))
