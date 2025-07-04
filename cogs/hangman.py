import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import random

class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_word(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://random-word-api.herokuapp.com/word") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data[0].lower()
            except Exception:
                pass
        return random.choice(["python", "discord", "hangman", "developer"])

    def get_stages(self):
        return [
            "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```"
        ]

    def format_display(self, display):
        return " ".join(display)

    async def play_game(self, ctx_or_interaction, mode, players, send_func):
        word = await self.fetch_word()
        display = ["_" for _ in word]
        guessed = set()
        attempts = 6
        turn = 0
        stages = self.get_stages()

        # Announce start
        await send_func(
            f"🎯 **Hangman Game Started!** Mode: `{mode.upper()}`\n"
            f"Word: `{self.format_display(display)}`\nYou have {attempts} tries.\n{stages[0]}"
        )

        while attempts > 0 and "_" in display:
            current_player = None
            if players:
                current_player = players[turn % len(players)]
                await send_func(f"🔁 {current_player.mention}, it's your turn to guess a letter.")

            def check(m):
                if isinstance(ctx_or_interaction, discord.Interaction):
                    # Interaction channel check
                    channel = ctx_or_interaction.channel
                else:
                    channel = ctx_or_interaction.channel
                if m.channel != channel or len(m.content) != 1 or not m.content.isalpha():
                    return False
                if players is None:
                    return True
                return m.author == current_player

            try:
                guess_msg = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                await send_func("⏰ Time's up! Game cancelled due to inactivity.")
                return

            guess = guess_msg.content.lower()

            if guess in guessed:
                await send_func("⚠️ Letter already guessed. Try a different one.")
                continue

            guessed.add(guess)
            if guess in word:
                for i, c in enumerate(word):
                    if c == guess:
                        display[i] = guess
                await send_func(f"✅ Correct! `{self.format_display(display)}`")
            else:
                attempts -= 1
                await send_func(f"❌ Wrong! `{self.format_display(display)}`\nTries left: {attempts}\n{stages[6 - attempts]}")

            if players:
                turn += 1

        if "_" not in display:
            await send_func(f"🎉 Congrats! The word was: `{word}`")
        else:
            await send_func(f"💀 Game Over! The word was `{word}`")

    # PREFIX COMMAND
    @commands.command(name="hangman")
    async def hangman(self, ctx, mode: str = None, opponent: discord.Member = None):
        # Validate mode
        valid_modes = {"solo", "duo", "ffa"}
        if mode is None or mode.lower() not in valid_modes:
            return await ctx.send(
                "❌ Invalid usage!\n"
                "Usage:\n"
                "`$hangman solo` - Play alone\n"
                "`$hangman duo @user` - Play with a friend\n"
                "`$hangman ffa` - Free for all guessing"
            )
        mode = mode.lower()

        players = [ctx.author]
        if mode == "duo":
            if opponent is None or opponent == ctx.author or opponent.bot:
                return await ctx.send("❌ You must mention a valid user (not yourself or a bot) for duo mode.")
            players.append(opponent)
        elif mode == "ffa":
            players = None

        async def send_func(msg):
            await ctx.send(msg)

        await self.play_game(ctx, mode, players, send_func)

    # SLASH COMMAND
    @app_commands.command(name="hangman", description="Play Hangman game")
    @app_commands.describe(
        mode="Game mode: solo, duo, or ffa",
        opponent="Opponent member (only for duo mode)"
    )
    async def hangman_slash(self, interaction: discord.Interaction, mode: str, opponent: discord.Member = None):
        valid_modes = {"solo", "duo", "ffa"}
        if mode.lower() not in valid_modes:
            await interaction.response.send_message(
                "❌ Invalid mode! Choose from: solo, duo, ffa.",
                ephemeral=True
            )
            return

        mode = mode.lower()

        players = [interaction.user]
        if mode == "duo":
            if opponent is None or opponent == interaction.user or opponent.bot:
                await interaction.response.send_message(
                    "❌ You must select a valid user (not yourself or a bot) for duo mode.",
                    ephemeral=True
                )
                return
            players.append(opponent)
        elif mode == "ffa":
            players = None

        async def send_func(msg):
            await interaction.followup.send(msg)

        await interaction.response.defer()
        await self.play_game(interaction, mode, players, send_func)

async def setup(bot):
    await bot.add_cog(Hangman(bot))
