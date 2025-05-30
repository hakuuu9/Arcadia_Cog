import discord
from discord.ext import commands
import motor.motor_asyncio

class StickyCog(commands.Cog):
    def __init__(self, bot, mongo_uri: str, staff_role_id: int):
        self.bot = bot
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client.get_default_database()  # DB from URI
        self.collection = self.db.sticky_messages
        self.staff_role_id = staff_role_id

    async def is_staff(self, ctx):
        # Check if user has staff role
        return discord.utils.get(ctx.author.roles, id=self.staff_role_id) is not None

    @commands.command(name="sticky", help="Set a sticky message in the channel (staff only)")
    async def sticky(self, ctx, *, message: str):
        if not await self.is_staff(ctx):
            await ctx.send("You do not have permission to use this command.", delete_after=5)
            return

        exists = await self.collection.find_one({"channel_id": ctx.channel.id})
        if exists:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=5)
            return

        sent_msg = await ctx.send(message)
        data = {
            "channel_id": ctx.channel.id,
            "message": message,
            "message_id": sent_msg.id,
            "author_id": ctx.author.id
        }
        await self.collection.insert_one(data)
        await ctx.send("Sticky message set successfully.", delete_after=5)

    @commands.command(name="unsticky", help="Remove the sticky message from the channel (staff only)")
    async def unsticky(self, ctx):
        if not await self.is_staff(ctx):
            await ctx.send("You do not have permission to use this command.", delete_after=5)
            return

        result = await self.collection.find_one_and_delete({"channel_id": ctx.channel.id})
        if not result:
            await ctx.send("There's no sticky message in this channel.", delete_after=5)
            return

        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        data = await self.collection.find_one({"channel_id": message.channel.id})
        if data:
            try:
                old_msg = await message.channel.fetch_message(data["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass

            new_msg = await message.channel.send(data["message"])
            await self.collection.update_one(
                {"channel_id": message.channel.id},
                {"$set": {"message_id": new_msg.id}}
            )

        await self.bot.process_commands(message)

async def setup(bot):
    MONGO_URI = "your_mongodb_connection_string_here"
    STAFF_ROLE_ID = 123456789012345678  # Replace with your staff role ID

    cog = StickyCog(bot, MONGO_URI, STAFF_ROLE_ID)
    await bot.add_cog(cog)
