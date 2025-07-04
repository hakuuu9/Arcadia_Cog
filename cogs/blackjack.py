import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from pymongo import MongoClient
from config import MONGO_URL

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users
        self.emoji = "<:arcadiacoin:1378656679704395796>"
        self.suits = ['♠️', '♥️', '♦️', '♣️']
        self.cards = {
            'A': 11,
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
            '7': 7, '8': 8, '9': 9, '10': 10,
            'J': 10, 'Q': 10, 'K': 10
        }

    def draw_card(self):
        card = random.choice(list(self.cards.keys()))
        suit = random.choice(self.suits)
        value = self.cards[card]
        return f"{card}{suit}", value

    def calculate_total(self, hand):
        total = sum(card[1] for card in hand)
        aces = [card for card in hand if card[0].startswith('A')]
        while total > 21 and aces:
            total -= 10
            aces.pop()
        return total

    async def play_blackjack(self, user, amount, ctx=None, interaction=None):
        user_data = self.db.find_one({'_id': str(user.id)})
        balance = user_data['balance'] if user_data and 'balance' in user_data else 0

        if amount <= 0:
            return "❌ Bet must be more than 0."
        if balance < amount:
            return f"❌ Not enough coins! Your balance is ₱{balance:,} {self.emoji}"

        # Deduct bet
        self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': -amount}}, upsert=True)

        player_hand = []
        dealer_hand = []

        # Initial draw
        for _ in range(2):
            player_hand.append(self.draw_card())
            dealer_hand.append(self.draw_card())

        player_total = self.calculate_total(player_hand)
        dealer_total = self.calculate_total(dealer_hand)

        def display_embed(hidden=True):
            embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_gold())
            player_cards = ' '.join(card[0] for card in player_hand)
            dealer_cards = f"{dealer_hand[0][0]} ❔" if hidden else ' '.join(card[0] for card in dealer_hand)
            dealer_total_display = '' if hidden else f"(Total: {dealer_total})"

            embed.add_field(
                name=f"👤 {user.display_name}'s Hand",
                value=f"{player_cards}\n**Total:** {player_total}",
                inline=False
            )
            embed.add_field(
                name="🤵 Dealer's Hand",
                value=f"{dealer_cards} {dealer_total_display}",
                inline=False
            )
            embed.set_footer(text="Type 'hit' or 'stand' within 30 seconds.")
            return embed

        # Send initial embed
        if ctx:
            msg = await ctx.send(embed=display_embed())
        else:
            await interaction.response.defer()
            msg = await interaction.followup.send(embed=display_embed())

        def check(m):
            return m.author.id == user.id and m.content.lower() in ["hit", "stand"]

        while True:
            try:
                reply = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                embed = display_embed(hidden=False)
                embed.set_footer(text="⏰ Timed out. You stood automatically.")
                await msg.edit(embed=embed)
                break

            if reply.content.lower() == "hit":
                card = self.draw_card()
                player_hand.append(card)
                player_total = self.calculate_total(player_hand)

                embed = display_embed()
                embed.description = f"✨ You drew **{card[0]}**."
                await msg.edit(embed=embed)

                if player_total > 21:
                    embed = display_embed(hidden=False)
                    embed.color = discord.Color.red()
                    embed.description = f"💥 You busted and lost ₱{amount:,} {self.emoji}."
                    await msg.edit(embed=embed)
                    return
            else:
                break

        # Dealer's turn
        while dealer_total < 17:
            card = self.draw_card()
            dealer_hand.append(card)
            dealer_total = self.calculate_total(dealer_hand)

        # Final outcome embed
        embed = display_embed(hidden=False)

        if dealer_total > 21 or player_total > dealer_total:
            winnings = amount * 2
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': winnings}}, upsert=True)
            embed.color = discord.Color.green()
            embed.description = f"🎉 You win ₱{winnings:,} {self.emoji}!"
        elif player_total == dealer_total:
            self.db.update_one({'_id': str(user.id)}, {'$inc': {'balance': amount}}, upsert=True)
            embed.color = discord.Color.blurple()
            embed.description = f"⚖️ It's a tie! Your bet of ₱{amount:,} was returned."
        else:
            embed.color = discord.Color.red()
            embed.description = f"💔 You lost ₱{amount:,} {self.emoji}."

        await msg.edit(embed=embed)

    # $blackjack command
    @commands.command(name="blackjack")
    async def blackjack_text(self, ctx, amount: int):
        outcome = await self.play_blackjack(ctx.author, amount, ctx=ctx)
        if isinstance(outcome, str):
            await ctx.send(outcome)

    # /blackjack command
    @app_commands.command(name="blackjack", description="Play Blackjack and win coins!")
    @app_commands.describe(amount="The amount you want to bet")
    async def blackjack_slash(self, interaction: discord.Interaction, amount: int):
        outcome = await self.play_blackjack(interaction.user, amount, interaction=interaction)
        if isinstance(outcome, str):
            await interaction.followup.send(outcome, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
