import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient

class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient("YOUR_MONGO_URI")
        self.db = self.client["your_db"]
        self.collection = self.db["autoresponders"]

    @commands.command(name="autorespond")
    async def add_autorespond(self, ctx, keyword: str, *, response: str):
        """Add an autoresponse trigger (text command)"""
        await self._add_autoresponder(ctx.guild.id, keyword, response)
        await ctx.send(f"Autoresponder for `{keyword}` added!")

    @app_commands.command(name="autorespond", description="Add an autoresponse trigger")
    @app_commands.describe(keyword="Trigger word", response="Bot reply")
    async def slash_autorespond(self, interaction: discord.Interaction, keyword: str, response: str):
        await self._add_autoresponder(interaction.guild.id, keyword, response)
        await interaction.response.send_message(f"Autoresponder for `{keyword}` added!", ephemeral=True)

    async def _add_autoresponder(self, guild_id, keyword, response):
        await self.collection.insert_one({
            "guild_id": str(guild_id),
            "keyword": keyword.lower(),
            "response": response
        })

    @commands.command(name="removeautorespond")
    async def remove_autorespond(self, ctx, *, keyword: str):
        """Remove an autoresponse (text command)"""
        result = await self.collection.delete_one({
            "guild_id": str(ctx.guild.id),
            "keyword": keyword.lower()
        })
        msg = f"Removed autoresponder for `{keyword}`." if result.deleted_count else "Keyword not found."
        await ctx.send(msg)

    @app_commands.command(name="removeautorespond", description="Remove an autoresponse trigger")
    async def slash_remove_autorespond(self, interaction: discord.Interaction, keyword: str):
        result = await self.collection.delete_one({
            "guild_id": str(interaction.guild.id),
            "keyword": keyword.lower()
        })
        msg = f"Removed autoresponder for `{keyword}`." if result.deleted_count else "Keyword not found."
        await interaction.response.send_message(msg, ephemeral=True)

    @commands.command(name="listautorespond")
    async def list_autorespond(self, ctx):
        """List all autoresponders for this server"""
        data = self.collection.find({"guild_id": str(ctx.guild.id)})
        items = [f"`{d['keyword']}` → {d['response']}" async for d in data]
        await ctx.send("\n".join(items) or "No autoresponders set.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        data = self.collection.find({"guild_id": str(message.guild.id)})
        async for doc in data:
            if doc["keyword"].lower() in message.content.lower():
                await message.channel.send(doc["response"])
                break

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))