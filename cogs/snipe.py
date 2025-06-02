import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

sniped_messages = {}  # {channel_id: [list of deleted messages]}


class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Store deleted messages
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        channel_id = message.channel.id
        sniped_messages.setdefault(channel_id, [])
        sniped_messages[channel_id].insert(0, {
            "content": message.content,
            "author": str(message.author),
            "avatar": message.author.display_avatar.url,
            "time": discord.utils.format_dt(discord.utils.utcnow(), style="R")
        })

        if len(sniped_messages[channel_id]) > 10:
            sniped_messages[channel_id].pop()

    # $snipe message command
    @commands.command(name="snipe")
    async def snipe_command(self, ctx, amount: int = 1):
        await self.send_snipes(ctx.channel, ctx, amount)

    # /snipe slash command
    @app_commands.command(name="snipe", description="Snipe deleted messages from the channel")
    @app_commands.describe(amount="How many messages to snipe (1-10)")
    async def snipe_slash(self, interaction: discord.Interaction, amount: int = 1):
        await self.send_snipes(interaction.channel, interaction, amount)

    # Shared method to send sniped messages
    async def send_snipes(self, channel, ctx_or_inter, amount):
        messages = sniped_messages.get(channel.id, [])
        if not messages:
            if isinstance(ctx_or_inter, commands.Context):
                return await ctx_or_inter.send("There's nothing to snipe!")
            else:
                return await ctx_or_inter.response.send_message("There's nothing to snipe!", ephemeral=True)

        amount = max(1, min(amount, 10))
        gif_url = "https://i.imgur.com/JxsCfCe.gif"  # your top-right GIF

        embeds = []
        for i in range(min(amount, len(messages))):
            data = messages[i]
            embed = discord.Embed(
                description=data["content"] or "*No content*",
                color=discord.Color.blurple()
            )
            embed.set_author(name=data["author"], icon_url=data["avatar"])
            embed.set_thumbnail(url=gif_url)
            embed.set_footer(text=f"Deleted {data['time']}")
            embeds.append(embed)

        if isinstance(ctx_or_inter, commands.Context):
            for embed in embeds:
                await ctx_or_inter.send(embed=embed)
        else:
            await ctx_or_inter.response.send_message(embeds=embeds if len(embeds) == 1 else None)
            if len(embeds) > 1:
                for embed in embeds:
                    await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Snipe(bot))
