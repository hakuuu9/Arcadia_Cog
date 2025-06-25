import discord
from discord.ext import commands
import requests
import json
from config import TOGETHER_API_KEY

class AskTogether(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ask')
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def ask(self, ctx, *, question: str):
        if len(question) > 300:
            return await ctx.send("❌ Please keep your question under 300 characters.")

        await ctx.typing()

        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }

        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            embed = discord.Embed(
                title="🤖 AI says:",
                description=reply,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Asked by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            await ctx.reply(embed=embed)
        else:
            await ctx.send(f"⚠️ API Error: {response.status_code} — {response.text}")

    @ask.error
    async def ask_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Cooldown: Try again in {round(error.retry_after, 1)} seconds.")
        else:
            await ctx.send("⚠️ An unexpected error occurred.")

async def setup(bot):
    await bot.add_cog(AskTogether(bot))
