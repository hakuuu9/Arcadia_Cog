import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

CONFESS_CHANNEL_ID = 1364848318034739220
CONFESSION_LOG_CHANNEL_ID = 1364839238960549908

class Confess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = MongoClient(MONGO_URL)
        self.db = self.mongo.hxhbot.confessions
        print("Confess Cog initialized with MongoDB.")

    async def post_confession(self, source, message, author):
        counter = self.db.find_one_and_update(
            {"_id": "confession_count"},
            {"$inc": {"count": 1}},
            upsert=True,
            return_document=True
        )
        count = counter["count"]

        confess_channel = self.bot.get_channel(CONFESS_CHANNEL_ID)
        log_channel = self.bot.get_channel(CONFESSION_LOG_CHANNEL_ID)

        public_embed = discord.Embed(
            title=f"Arcadia Confession #{count}",
            description=message,
            color=discord.Color.purple()
        )
        public_embed.set_footer(text="Submitted anonymously • Powered by Arcadia with love")

        log_embed = discord.Embed(
            title=f"Confession #{count} Logged",
            description=message,
            color=discord.Color.red()
        )
        log_embed.set_author(name=f"{author} ({author.id})", icon_url=author.display_avatar.url)
        log_embed.set_footer(text=f"Sent from: {source.guild.name if isinstance(source, discord.Message) and source.guild else 'DMs'}")

        if confess_channel:
            await confess_channel.send(embed=public_embed)

            # Delete original message (for prefix in server only)
            if isinstance(source, commands.Context) and isinstance(source.channel, discord.TextChannel):
                try:
                    await source.message.delete()
                except discord.Forbidden:
                    pass

            try:
                await author.send(f"✅ Your confession has been anonymously posted as **Confession #{count}**.")
            except discord.Forbidden:
                pass

        if log_channel:
            await log_channel.send(embed=log_embed)

    # Prefix version (supports DM too)
    @commands.command(name="confess")
    async def confess_prefix(self, ctx, *, message=None):
        if message is None:
            await ctx.send("❗ Please include a confession message.\nExample: `$confess I love Noir`")
            return
        await self.post_confession(ctx, message, ctx.author)

    # Slash version
    @app_commands.command(name="confess", description="Send an anonymous confession.")
    @app_commands.describe(message="The content of your confession")
    async def confess_slash(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        await self.post_confession(interaction, message, interaction.user)
        await interaction.followup.send("✅ Your confession has been anonymously posted.", ephemeral=True)

    def cog_unload(self):
        self.mongo.close()
        print("Confess MongoDB connection closed.")

async def setup(bot):
    await bot.add_cog(Confess(bot))
