import discord
from discord import app_commands
from discord.ext import commands
import requests
import json
from config import TOGETHER_API_KEY

class AskTogetherSlash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Ask the AI anything!")
    @app_commands.describe(question="Your question to the AI")
    async def ask(self, interaction: discord.Interaction, question: str):
        if len(question) > 300:
            await interaction.response.send_message("❌ Please keep your question under 300 characters.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {"role": "system", "content": "You are a helpful and friendly assistant."},
                {"role": "user", "content": question}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }

        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content'].strip()

            embed = discord.Embed(
                title="🗣️ Arcadia Says:",
                description=f"✨ {reply}",
                color=discord.Color.dark_grey()
            )
            embed.set_footer(text=f"Asked by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"⚠️ API Error: {response.status_code} — {response.text}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AskTogetherSlash(bot))
