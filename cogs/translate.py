import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://libretranslate.com/translate"
        self.default_target = "en"  # Change this to your preferred default language code

    async def translate_text(self, text: str):
        try:
            payload = {
                "q": text,
                "source": "auto",
                "target": self.default_target,
                "format": "text"
            }
            headers = {
                "Accept": "application/json"
            }
            response = requests.post(self.api_url, data=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("translatedText", "Translation failed.")
        except Exception:
            return "❌ Sorry, I couldn't translate that."

    @commands.command(name="translate")
    async def translate_command(self, ctx, *, text: str = None):
        if not text:
            await ctx.send("❌ Please provide the text to translate.\nUsage: `!translate <text>`")
            return
        loading = await ctx.send("🌐 Translating...")
        translated = await self.translate_text(text)
        await asyncio.sleep(1)
        embed = discord.Embed(
            title=f"Translation (to English)",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await loading.edit(content=None, embed=embed)

    @app_commands.command(name="translate", description="Translate text to English (auto detect language)")
    @app_commands.describe(text="Text to translate")
    async def translate_slash(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message("🌐 Translating...")
        translated = await self.translate_text(text)
        embed = discord.Embed(
            title=f"Translation (to English)",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(Translate(bot))
