import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import re
import config

cluster = MongoClient(config.MONGO_URL)
db = cluster["bot_db"]
collection = db["autoresponders"]

class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Manual message command
    @commands.command(name="autorespond")
    async def add_responder_manual(self, ctx, keyword: str, *, response: str):
        await self._add_responder(ctx.guild.id, keyword, response)
        await ctx.send(f"✅ Added responder: `{keyword}` → {response}")

    # Slash command to add
    @app_commands.command(name="add_autoresponder", description="Add an autoresponder for a keyword")
    @app_commands.describe(keyword="Trigger word", response="Bot's response message")
    async def add_responder_slash(self, interaction: discord.Interaction, keyword: str, response: str):
        await self._add_responder(interaction.guild.id, keyword, response)
        await interaction.response.send_message(f"✅ Added responder: `{keyword}` → {response}", ephemeral=True)

    # Slash command to remove
    @app_commands.command(name="remove_autoresponder", description="Remove an autoresponder keyword")
    @app_commands.describe(keyword="Trigger word to remove")
    async def remove_responder_slash(self, interaction: discord.Interaction, keyword: str):
        result = collection.delete_one({"guild_id": interaction.guild.id, "keyword": keyword.lower()})
        if result.deleted_count > 0:
            await interaction.response.send_message(f"✅ Removed responder for `{keyword}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ No responder found for `{keyword}`", ephemeral=True)

    # Message listener for partial matches
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        data = list(collection.find({"guild_id": message.guild.id}))
        content = message.content.lower()

        for entry in data:
            if re.search(rf"\b{re.escape(entry['keyword'])}\b", content):
                await message.channel.send(entry['response'])
                break

    async def _add_responder(self, guild_id, keyword, response):
        collection.update_one(
            {"guild_id": guild_id, "keyword": keyword.lower()},
            {"$set": {"response": response}},
            upsert=True
        )

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))