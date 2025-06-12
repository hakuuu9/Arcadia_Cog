import discord
from discord.ext import commands
import re

class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="emoji")
    async def enlarge_emoji(self, ctx: commands.Context):
        # Make sure the command is used as a reply
        if not ctx.message.reference:
            return await ctx.send("❌ You must reply to a message containing a custom emoji.")

        # Fetch the replied message
        try:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            return await ctx.send("❌ Couldn't find the replied message.")

        # Regex to find custom emoji
        emoji_pattern = r"<(a?):([a-zA-Z0-9_]+):(\d+)>"
        match = re.search(emoji_pattern, replied_msg.content)

        if not match:
            return await ctx.send("❌ No custom emoji found in the replied message.")

        is_animated = match.group(1) == "a"
        emoji_id = match.group(3)
        ext = "gif" if is_animated else "png"
        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?v=1"

        await ctx.send(f"🔍 Enlarged Emoji:\n{url}")

async def setup(bot):
    await bot.add_cog(Emoji(bot))
