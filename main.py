import discord
from discord.ext import commands
import motor.motor_asyncio
from pymongo.errors import PyMongoError

class StickyCog(commands.Cog):
    def __init__(self, bot, mongo_uri: str, staff_role_id: int):
        self.bot = bot
        try:
            self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.db = self.mongo_client.get_default_database()
            self.collection = self.db.sticky_messages
            print("MongoDB connection established successfully.")
        except PyMongoError as e:
            print(f"Failed to connect to MongoDB: {e}")
            self.mongo_client = None
            self.db = None
            self.collection = None
        
        self.staff_role_id = staff_role_id

    async def is_staff(self, ctx):
        if isinstance(ctx.author, discord.Member):
            return discord.utils.get(ctx.author.roles, id=self.staff_role_id) is not None
        return False

    @commands.command(name="sticky", help="Set a sticky message in the channel (staff only)")
    @commands.guild_only()
    async def sticky(self, ctx, *, message: str):
        if not self.collection:
            await ctx.send("Database connection not established. Please contact an administrator.", delete_after=10)
            return

        if not await self.is_staff(ctx):
            await ctx.send("You do not have permission to use this command.", delete_after=5)
            return

        try:
            exists = await self.collection.find_one({"channel_id": ctx.channel.id})
            if exists:
                await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=7)
                return

            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass

            sent_msg = await ctx.send(message)
            data = {
                "channel_id": ctx.channel.id,
                "message": message,
                "message_id": sent_msg.id,
                "author_id": ctx.author.id,
                "guild_id": ctx.guild.id
            }
            await self.collection.insert_one(data)
            await ctx.send("Sticky message set successfully.", delete_after=5)

        except PyMongoError as e:
            await ctx.send(f"An error occurred while setting the sticky message: {e}", delete_after=10)
        except discord.DiscordException as e:
            await ctx.send(f"An error occurred with Discord while setting the sticky message: {e}", delete_after=10)

    @commands.command(name="unsticky", help="Remove the sticky message from the channel (staff only)")
    @commands.guild_only()
    async def unsticky(self, ctx):
        if not self.collection:
            await ctx.send("Database connection not established. Please contact an administrator.", delete_after=10)
            return

        if not await self.is_staff(ctx):
            await ctx.send("You do not have permission to use this command.", delete_after=5)
            return

        try:
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass

            result = await self.collection.find_one_and_delete({"channel_id": ctx.channel.id})
            if not result:
                await ctx.send("There's no sticky message in this channel.", delete_after=5)
                return

            try:
                old_msg = await ctx.channel.fetch_message(result["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass

            await ctx.send("Sticky message removed successfully.", delete_after=5)

        except PyMongoError as e:
            await ctx.send(f"An error occurred while removing the sticky message: {e}", delete_after=10)
        except discord.DiscordException as e:
            await ctx.send(f"An error occurred with Discord while removing the sticky message: {e}", delete_after=10)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        if not self.collection:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        try:
            data = await self.collection.find_one({"channel_id": message.channel.id})
            if data:
                try:
                    old_msg = await message.channel.fetch_message(data["message_id"])
                    await old_msg.delete()
                except discord.NotFound:
                    await self.collection.delete_one({"channel_id": message.channel.id})
                    print(f"Sticky message for channel {message.channel.id} not found on Discord, removed from DB.")
                    return

                new_msg = await message.channel.send(data["message"])
                await self.collection.update_one(
                    {"channel_id": message.channel.id},
                    {"$set": {"message_id": new_msg.id}}
                )
        except PyMongoError as e:
            print(f"Database error in on_message: {e}")
        except discord.DiscordException as e:
            print(f"Discord API error in on_message: {e}")

        await self.bot.process_commands(message)

async def setup(bot):
    # This is where you will define your MongoDB URI
    # For demonstration, keeping it as a placeholder.
    # In a real application, consider using environment variables for this.
    MONGO_URI = "your_mongodb_connection_string_here" 

    # STAFF_ROLE_ID defined directly in this setup function
    STAFF_ROLE_ID = 1347181345922748456  # <--- Your staff role ID here

    if MONGO_URI == "your_mongodb_connection_string_here":
        print("WARNING: Please replace 'your_mongodb_connection_string_here' with your actual MongoDB URI.")
    
    # Optional: You could add a check if STAFF_ROLE_ID is 0 or an invalid ID if you're pulling it from a source that could be empty.
    # Since you're hardcoding it, this check is less critical, but still good practice if it might change later.

    cog = StickyCog(bot, MONGO_URI, STAFF_ROLE_ID)
    await bot.add_cog(cog)
