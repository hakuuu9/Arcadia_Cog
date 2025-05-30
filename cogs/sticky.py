import discord
from discord.ext import commands
import motor.motor_asyncio

def is_staff():
    def predicate(ctx):
        return ctx.author.guild_permissions.manage_messages
    return commands.check(predicate)

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.client["mydatabase"]
        self.collection = self.db["sticky_messages"]

    @commands.command()
    @is_staff()
    async def sticky(self, ctx, *, message: str):
        existing = await self.collection.find_one({"channel_id": ctx.channel.id})
        if existing:
            await ctx.send("There's already a sticky message in this channel. Use `$unsticky` first.", delete_after=5)
            return

        sent = await ctx.send(message)
        await self.collection.insert_one({
            "channel_id": ctx.channel.id,
            "message": message,
            "message_id": sent.id,
            "author_id": ctx.author.id
        })
        await ctx.send("Sticky message set successfully.", delete_after=5)

    @commands.command()
    @is_staff()
    async def unsticky(self, ctx):
        existing = await self.collection.find_one({"channel_id": ctx.channel.id})
        if not existing:
            await ctx.send("There's no sticky message in this channel.", delete_after=5)
            return

        try:
            msg = await ctx.channel.fetch_message(existing["message_id"])
            await msg.delete()
        except discord.NotFound:
            pass
        await self.collection.delete_one({"channel_id": ctx.channel.id})
        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        existing = await self.collection.find_one({"channel_id": message.channel.id})
        if existing:
            try:
                old_msg = await message.channel.fetch_message(existing["message_id"])
                await old_msg.delete()
            except discord.NotFound:
                pass
            new_msg = await message.channel.send(existing["message"])
            await self.collection.update_one(
                {"channel_id": message.channel.id},
                {"$set": {"message_id": new_msg.id}}
            )

        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Sticky(bot))
