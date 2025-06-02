import discord
from discord.ext import commands
from discord import app_commands
import random
from balance import Balance  # Assuming you import your Balance cog like this

CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

def calculate_score(cards):
    score = sum(CARD_VALUES[card] for card in cards)
    # Adjust for Aces (11->1)
    aces = cards.count('A')
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def format_hand(cards):
    return ', '.join(cards)

class BlackjackView(discord.ui.View):
    def __init__(self, bot, ctx_or_interaction, user, bet, balance_cog):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx_or_interaction = ctx_or_interaction
        self.user = user
        self.bet = bet
        self.balance_cog = balance_cog

        # Start hands
        self.player_cards = [self.draw_card(), self.draw_card()]
        self.dealer_cards = [self.draw_card(), self.draw_card()]
        self.game_over = False
        self.message = None

    def draw_card(self):
        return random.choice(list(CARD_VALUES.keys()))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="⌛ Blackjack game ended due to inactivity.", view=self)

    async def update_message(self, interaction=None, content=None):
        embed = discord.Embed(title=f"{self.user.display_name}'s Blackjack", color=discord.Color.gold())
        embed.add_field(name="Your hand",
                        value=f"{format_hand(self.player_cards)}\nScore: {calculate_score(self.player_cards)}",
                        inline=False)
        embed.add_field(name="Dealer's hand",
                        value=f"{self.dealer_cards[0]}, ❓", inline=False)
        if content:
            embed.set_footer(text=content)
        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.message.edit(embed=embed, view=self)

    async def finish_game(self, interaction, player_bust=False, player_stand=False, double_down=False):
        dealer_score = calculate_score(self.dealer_cards)
        player_score = calculate_score(self.player_cards)

        # Dealer draws until 17 or higher
        while dealer_score < 17:
            self.dealer_cards.append(self.draw_card())
            dealer_score = calculate_score(self.dealer_cards)

        # Determine outcome
        if player_bust:
            result = f"💥 You busted with {player_score}. You lost ₱{self.bet:,}."
            payout = -self.bet
        elif dealer_score > 21:
            result = f"🏆 Dealer busted with {dealer_score}. You win ₱{self.bet * 2:,}!"
            payout = self.bet * 2
        elif player_score > dealer_score:
            result = f"🏆 You win with {player_score} vs dealer's {dealer_score}. You win ₱{self.bet * 2:,}!"
            payout = self.bet * 2
        elif player_score == dealer_score:
            result = f"⚖️ It's a tie with {player_score}. Your bet of ₱{self.bet:,} is returned."
            payout = self.bet
        else:
            result = f"😞 Dealer wins with {dealer_score} vs your {player_score}. You lost ₱{self.bet:,}."
            payout = -self.bet

        # Adjust for double down (bet already doubled)
        if double_down:
            # Bet was doubled at start, payout calculation accounted
            pass

        # Update balance
        await self.balance_cog.update_balance(self.user.id, payout)

        # Show final hands and disable buttons
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(title=f"{self.user.display_name}'s Blackjack - Game Over", color=discord.Color.gold())
        embed.add_field(name="Your hand",
                        value=f"{format_hand(self.player_cards)}\nScore: {player_score}", inline=False)
        embed.add_field(name="Dealer's hand",
                        value=f"{format_hand(self.dealer_cards)}\nScore: {dealer_score}", inline=False)
        embed.set_footer(text=result)

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game is already over.", ephemeral=True)
            return
        self.player_cards.append(self.draw_card())
        score = calculate_score(self.player_cards)
        if score > 21:
            self.game_over = True
            await self.finish_game(interaction, player_bust=True)
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game is already over.", ephemeral=True)
            return
        self.game_over = True
        await self.finish_game(interaction, player_stand=True)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.blurple)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.game_over:
            await interaction.response.send_message("Game is already over.", ephemeral=True)
            return
        user_data = await self.balance_cog.get_user_data(self.user.id)
        balance = user_data.get('balance', 0) if user_data else 0
        if balance < self.bet:
            await interaction.response.send_message("❌ You don't have enough coins to double down.", ephemeral=True)
            return

        # Deduct additional bet
        await self.balance_cog.update_balance(self.user.id, -self.bet)
        self.bet *= 2

        # Draw exactly one card, then stand
        self.player_cards.append(self.draw_card())
        score = calculate_score(self.player_cards)
        self.game_over = True

        if score > 21:
            await self.finish_game(interaction, player_bust=True, double_down=True)
        else:
            await self.finish_game(interaction, player_stand=True, double_down=True)

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Get your Balance cog instance
        self.balance_cog = bot.get_cog("Balance")

    async def get_user_balance(self, user_id: int):
        user_data = await self.balance_cog.get_user_data(user_id)
        return user_data.get('balance', 0) if user_data else 0

    @commands.command(name="blackjack")
    async def blackjack_command(self, ctx, bet: int):
        user = ctx.author
        balance = await self.get_user_balance(user.id)

        if bet <= 0:
            return await ctx.send("❌ Bet must be a positive number.")
        if bet > balance:
            return await ctx.send(f"❌ You don't have enough coins. Your balance: ₱{balance:,}")

        # Deduct bet at start
        await self.balance_cog.update_balance(user.id, -bet)

        view = BlackjackView(self.bot, ctx, user, bet, self.balance_cog)
        embed = discord.Embed(title=f"{user.display_name}'s Blackjack", color=discord.Color.gold())
        embed.add_field(name="Your hand",
                        value=f"{format_hand(view.player_cards)}\nScore: {calculate_score(view.player_cards)}",
                        inline=False)
        embed.add_field(name="Dealer's hand",
                        value=f"{view.dealer_cards[0]}, ❓", inline=False)
        embed.set_footer(text=f"Bet: ₱{bet:,}")

        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @app_commands.command(name="blackjack", description="Play blackjack by betting coins")
    @app_commands.describe(bet="Amount of coins to bet")
    async def blackjack_slash(self, interaction: discord.Interaction, bet: int):
        user = interaction.user
        balance = await self.get_user_balance(user.id)

        if bet <= 0:
            return await interaction.response.send_message("❌ Bet must be a positive number.", ephemeral=True)
        if bet > balance:
            return await interaction.response.send_message(f"❌ You don't have enough coins. Your balance: ₱{balance:,}", ephemeral=True)

        # Deduct bet at start
        await self.balance_cog.update_balance(user.id, -bet)

        view = BlackjackView(self.bot, interaction, user, bet, self.balance_cog)
        embed = discord.Embed(title=f"{user.display_name}'s Blackjack", color=discord.Color.gold())
        embed.add_field(name="Your hand",
                        value=f"{format_hand(view.player_cards)}\nScore: {calculate_score(view.player_cards)}",
                        inline=False)
        embed.add_field(name="Dealer's hand",
                        value=f"{view.dealer_cards[0]}, ❓", inline=False)
        embed.set_footer(text=f"Bet: ₱{bet:,}")

        message = await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        # Because response sent, get original message
        sent_message = await interaction.original_response()
        view.message = sent_message

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
