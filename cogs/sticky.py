from discord.ext import commands
import discord
import motor.motor_asyncio  # async MongoDB driver

class StickyCog(commands.Cog):
    def __init__(self, bot, mongo_uri, db_name):
        self.bot = bot

        # MongoDB setup
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.collection = self.db['sticky_messages']

        self.sticky_messages = {}  # channel_id -> dict

        # Load existing sticky messages from DB
        self.bot.loop.create_task(self.load_sticky_messages())

    async def load_sticky_messages(self):
        async for doc in self.collection.find({}):
            channel_id = doc['channel_id']
            self.sticky_messages[channel_id] = {
                "message": doc['message'],
                "message_id": doc['message_id'],
                "author": doc['author']
            }

    def is_staff():
        async def predicate(ctx):
            staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
            return staff_role in ctx.author.roles or ctx.author.guild_permissions.manage_messages
        return commands.check(predicate)

    @commands.command(name="sticky")
    @is_staff()
    async def sticky(self, ctx, *, message: str):
        if ctx.channel.id in self.sticky_messages:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=5)
            return

        sticky_msg = await ctx.send(message)
        self.sticky_messages[ctx.channel.id] = {
            "message": message,
            "message_id": sticky_msg.id,
            "author": ctx.author.id
        }
        # Save to DB
        await self.collection.insert_one({
            "channel_id": ctx.channel.id,
            "message": message,
            "message_id": sticky_msg.id,
            "author": ctx.author.id
        })

        await ctx.send("Sticky message set successfully.", delete_after=5)

    @commands.command(name="unsticky")
    @is_staff()
    async def unsticky(self, ctx):
        if ctx.channel.id not in self.sticky_messages:
            await ctx.send("There's no sticky message in this channel.", delete_after=5)
            return

        # Try to delete the sticky message from the channel
        try:
            old_msg = await ctx.channel.fetch_message(self.sticky_messages[ctx.channel.id]["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        del self.sticky_messages[ctx.channel.id]
        # Remove from DB
        await self.collection.delete_one({"channel_id": ctx.channel.id})

        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        await self.bot.process_commands(message)

        channel_id = message.channel.id
        if channel_id in self.sticky_messages:
            data = self.sticky_messages[channel_id]

            try:
                old_msg = await message.channel.fetch_message(data["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass

            new_msg = await message.channel.send(data["message"])
            self.sticky_messages[channel_id]["message_id"] = new_msg.id

            # Update DB with new message ID
            await self.collection.update_one(
                {"channel_id": channel_id},
                {"$set": {"message_id": new_msg.id}}
            )


# To add this cog:
# bot.add_cog(StickyCog(bot, mongo_uri="mongodb+srv://username:password@clusterurl", db_name="yourdbname"))
