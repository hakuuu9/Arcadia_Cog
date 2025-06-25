import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
from config import TOGETHER_API_KEY

class AskTogether(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def query_together_ai(self, prompt: str):
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {"role": "system", "content": "You are a helpful and friendly assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            raise Exception(f"API Error: {response.status_code} — {response.text}")

    def create_embed(self, answer: str, author: discord.User):
        embed = discord.Embed(
            title="🗣️ Arcadia Says:",
            description=f"✨ {answer}",
            color=discord.Color.dark_grey()
        )
        embed.set_footer(text=f"Asked by {author.display_name}", icon_url=author.display_avatar.url)
        return embed

    # PREFIX COMMAND
    @commands.command(name='ask')
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def ask_prefix(self, ctx, *, question: str):
        if len(question) > 300:
            return await ctx.send("❌ Please keep your question under 300 characters.")

        await ctx.typing()
        try:
            answer = await self.query_together_ai(question)
            embed = self.create_embed(answer, ctx.author)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"⚠️ {str(e)}")

    @ask_prefix.error
    async def ask_prefix_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Slow down! Try again in {round(error.retry_after, 1)} seconds.")
        else:
            await ctx.send("⚠️ An unexpected error occurred.")

    # SLASH COMMAND
    @app_commands.command(name="ask", description="Ask the AI anything!")
    @app_commands.describe(question="Your question to the AI")
    async def ask_slash(self, interaction: discord.Interaction, question: str):
        if len(question) > 300:
            await interaction.response.send_message("❌ Please keep your question under 300 characters.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            answer = await self.query_together_ai(question)
            embed = self.create_embed(answer, interaction.user)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"⚠️ {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AskTogether(bot))
