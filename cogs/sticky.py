import discord
from discord.ext import commands
from config import db  # Import your database object from config.py

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.collection = db["sticky_messages"]

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

        try:
            old_msg = await ctx.channel.fetch_message(existing["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        await self.collection.delete_one({"channel_id": ctx.channel.id})
        await ctx.send("Sticky message removed successfully.", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Let commands process normally
        await self.bot.process_commands(message)

        sticky_data = await self.collection.find_one({"channel_id": message.channel.id})
        if not sticky_data:
            return

        try:
            old_msg = await message.channel.fetch_message(sticky_data["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

        new_msg = await message.channel.send(sticky_data["message"])
        await self.collection.update_one(
            {"channel_id": message.channel.id},
            {"$set": {"message_id": new_msg.id}}
        )


async def setup(bot):
    await bot.add_cog(Sticky(bot))
