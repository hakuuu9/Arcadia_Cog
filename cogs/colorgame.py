import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from pymongo import MongoClient
from config import MONGO_URL  # Your MongoDB config

# Define animated emojis
GREEN_EMOJI = "<a:greencg:1378660883089330298>"
YELLOW_EMOJI = "<a:yellowcg:1378660868698538125>"
PINK_EMOJI = "<a:pinkcg:1378660898213990560>"

COLORS = {
    "green": GREEN_EMOJI,
    "yellow": YELLOW_EMOJI,
    "pink": PINK_EMOJI,
}
ROLLABLE_COLORS = list(COLORS.keys())

class ColorGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = MongoClient(MONGO_URL)
        self.db = self.client.hxhbot.users

    async def play_color_game(self, ctx, user, bet_amount, chosen_colors, send_func):
        user_id = str(user.id)
        chosen_colors = list(dict.fromkeys([c.lower() for c in chosen_colors if c.lower() in COLORS]))

        if not chosen_colors:
            return await send_func("❌ Invalid color choices. Choose from: `green`, `yellow`, or `pink`.")

        if bet_amount <= 0:
            return await send_func("❌ You must bet a positive amount.")

        user_data = self.db.find_one({"_id": user_id})
        current_balance = int(user_data.get("balance", 0)) if user_data else 0
        total_bet = bet_amount * len(chosen_colors)

        if total_bet > current_balance:
            return await send_func(
                f"❌ Not enough balance. You bet ₱{total_bet:,}, but you only have ₱{current_balance:,}.")

        emoji_display = [COLORS[c] for c in chosen_colors]
        await send_func(f"{user.mention} is betting ₱{bet_amount:,} on {', '.join(emoji_display)}!\n"
                        f"Total bet: ₱{total_bet:,}. Rolling the colors!")

        roll_message = await ctx.channel.send("Rolling... 🎲")
        for _ in range(5):
            temp_emojis = [random.choice(list(COLORS.values())) for _ in range(3)]
            await roll_message.edit(content=f"Rolling... {temp_emojis[0]} {temp_emojis[1]} {temp_emojis[2]}")
            await asyncio.sleep(0.7)

        final_roll = [random.choice(ROLLABLE_COLORS) for _ in range(3)]
        final_emojis = [COLORS[c] for c in final_roll]

        winnings = 0
        result_summary = {}
        for color in chosen_colors:
            count = final_roll.count(color)
            if count > 0:
                won = bet_amount * count
                winnings += won
                result_summary[color] = f"Won ₱{won:,} ({count}x)"
            else:
                result_summary[color] = f"Lost ₱{bet_amount:,}"

        net_change = winnings - total_bet
        new_balance = current_balance + net_change

        self.db.update_one({"_id": user_id}, {"$inc": {"balance": net_change}}, upsert=True)

        embed = discord.Embed(
            title="🎲 Color Game Results! 🎲",
            description=f"The colors rolled: {final_emojis[0]} {final_emojis[1]} {final_emojis[2]}\n\n",
            color=discord.Color.orange()
        )

        for color, result in result_summary.items():
            embed.add_field(name=f"{COLORS[color]} {color.capitalize()}", value=f"• {result}", inline=True)

        if net_change > 0:
            embed.description += f"**🎉 You won ₱{net_change:,}!**"
            embed.color = discord.Color.green()
        elif net_change < 0:
            embed.description += f"**💔 You lost ₱{abs(net_change):,}!**"
            embed.color = discord.Color.red()
        else:
            embed.description += "**⚖️ It's a draw! Net change ₱0.**"
            embed.color = discord.Color.gold()

        embed.set_footer(text=f"Your new balance: ₱{new_balance:,}")
        await roll_message.delete()
        await send_func(embed=embed)

    # Slash command
    @app_commands.command(name="colorgame", description="Bet on colors in a perya-style game!")
    @app_commands.describe(
        bet_amount="The amount of ₱ to bet on EACH chosen color.",
        color1="Your first color choice.",
        color2="Your second color choice (optional).",
        color3="Your third color choice (optional)."
    )
    @app_commands.choices(
        color1=[app_commands.Choice(name="Green", value="green"),
                app_commands.Choice(name="Yellow", value="yellow"),
                app_commands.Choice(name="Pink", value="pink")],
        color2=[app_commands.Choice(name="Green", value="green"),
                app_commands.Choice(name="Yellow", value="yellow"),
                app_commands.Choice(name="Pink", value="pink")],
        color3=[app_commands.Choice(name="Green", value="green"),
                app_commands.Choice(name="Yellow", value="yellow"),
                app_commands.Choice(name="Pink", value="pink")]
    )
    async def colorgame(self, interaction: discord.Interaction, bet_amount: int, color1: str,
                        color2: str = None, color3: str = None):
        await interaction.response.defer()
        colors = [color1]
        if color2: colors.append(color2)
        if color3: colors.append(color3)

        await self.play_color_game(
            ctx=interaction,
            user=interaction.user,
            bet_amount=bet_amount,
            chosen_colors=colors,
            send_func=interaction.followup.send
        )

    # Manual (prefix) command
    @commands.command(name="colorgame")
    async def colorgame_manual(self, ctx, bet_amount: int = None, *colors):
        if bet_amount is None or not colors:
            return await ctx.send("❌ Usage: `$colorgame <bet_amount> <color1> [color2] [color3]`\n"
                                  "Example: `$colorgame 100 green yellow pink`")
        await self.play_color_game(
            ctx=ctx,
            user=ctx.author,
            bet_amount=bet_amount,
            chosen_colors=colors,
            send_func=ctx.send
        )

    def cog_unload(self):
        self.client.close()
        print("ColorGame MongoDB client closed.")

async def setup(bot):
    await bot.add_cog(ColorGame(bot))
