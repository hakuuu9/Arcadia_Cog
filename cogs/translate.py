import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def translate_text(self, text: str):
        try:
            params = {
                "q": text,
                "langpair": "auto|en"
            }
            response = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            translated = data["responseData"]["translatedText"]
            return translated
        except Exception as e:
            print("Translation error:", e)
            return "❌ Sorry, I couldn't translate that."

    @commands.command(name="translate")
    async def translate_command(self, ctx, *, text: str):
        if not text:
            await ctx.send("❌ Please provide text to translate. Usage: `!translate <text>`")
            return
        msg = await ctx.send("🌐 Translating...")
        translated = await self.translate_text(text)
        embed = discord.Embed(
            title="🌍 Translated to English",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await msg.edit(content=None, embed=embed)

    @app_commands.command(name="translate", description="Translate text to English (auto detect)")
    @app_commands.describe(text="Text to translate")
    async def translate_slash(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message("🌐 Translating...")
        translated = await self.translate_text(text)
        embed = discord.Embed(
            title="🌍 Translated to English",
            description=translated,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(Translate(bot))
