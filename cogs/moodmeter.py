import discord, aiohttp, random
from discord.ext import commands
from discord import app_commands

class MoodMeter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="moodmeter")
    async def mood_prefix(self, ctx, *, text: str = None):
        await self.send_mood(ctx, text)

    @app_commands.command(name="moodmeter", description="Check mood with style!")
    @app_commands.describe(text="Optional: Explain your mood and I'll analyze it")
    async def mood_slash(self, interaction, text: str = None):
        await self.send_mood(interaction, text)

    async def get_quote(self):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.quotable.io/random") as r:
                j = await r.json()
                return f'"{j["content"]}" — {j["author"]}'

    async def analyze_sentiment(self, text):
        # Example using Google Cloud NL sentiment:
        # returns score and magnitude
        # For brevity, omitted; call your configured API here
        return None

    async def send_mood(self, ctx_or_int, text):
        mood_desc = await self.get_quote()

        embed = discord.Embed(title="🧠 Mood Meter", color=discord.Color.random())
        if text:
            res = await self.analyze_sentiment(text)
            if res:
                score = res["score"]
                mag = res["magnitude"]
                mood_emoji = "😊" if score > 0.2 else "😐" if score > -0.2 else "😢"
                embed.add_field(name="Sentiment", value=f"{mood_emoji} Score: {score:+.2f}, Intensity: {mag:.2f}", inline=False)
        embed.add_field(name="Mood Quote", value=mood_desc, inline=False)
        user = ctx_or_int.user if isinstance(ctx_or_int, discord.Interaction) else ctx_or_int.author
        embed.set_footer(text=f"Requested by {user}")

        if isinstance(ctx_or_int, commands.Context):
            await ctx_or_int.send(embed=embed)
        else:
            if ctx_or_int.response.is_done():
                await ctx_or_int.followup.send(embed=embed)
            else:
                await ctx_or_int.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MoodMeter(bot))
