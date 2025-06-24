import discord
from discord.ext import commands
from discord import app_commands
import requests

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tagalog_to_english = {
            "kamusta": "how are you",
            "kamusta ka": "how are you",
            "kamusta kana": "how are you",
            "mahal kita": "i love you",
            "anong ginagawa mo": "what are you doing",
            "nasaan ka": "where are you",
            "wala lang": "nothing",
            "tara na": "let's go",
            "ingat ka": "take care",
        }

    async def fallback_api(self, text):
        try:
            params = {
                "q": text,
                "langpair": "auto|en"
            }
            r = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=10)
            data = r.json()
            return data["responseData"]["translatedText"]
        except Exception:
            return "❌ I couldn’t translate that."

    @commands.command(name="translate")
    async def translate_command(self, ctx, *, text: str):
        lower = text.lower()
        translated = self.tagalog_to_english.get(lower)
        if not translated:
            translated = await self.fallback_api(text)
        embed = discord.Embed(
            title="🌍 Translation",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @app_commands.command(name="translate", description="Translate Tagalog or auto-detect to English")
    @app_commands.describe(text="Text to translate")
    async def translate_slash(self, interaction: discord.Interaction, text: str):
        lower = text.lower()
        translated = self.tagalog_to_english.get(lower)
        if not translated:
            translated = await self.fallback_api(text)
        embed = discord.Embed(
            title="🌍 Translation",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Translate(bot))
