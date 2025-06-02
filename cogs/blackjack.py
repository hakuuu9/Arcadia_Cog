from discord.ext import commands
from discord import app_commands
import discord
import random
from pymongo import MongoClient
from config import MONGO_URL

class BlackjackView(discord.ui.View):
    def __init__(self, user, game, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.user = user
        self.game = game
        self.bot = bot
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the game starter can interact
        return interaction.user.id == self.user.id

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game['player'].append(self.game['draw']())
        player_score = self.game['score'](self.game['player'])

        if player_score > 21:
            await self.finish_game(interaction, bust=True)
            self.stop()
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_game(interaction, bust=False)
        self.stop()

    async def update_message(self, interaction):
        embed = self.game['embed'](self.game['player'], self.game['dealer'], reveal=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(content="⌛ Blackjack game ended due to inactivity.", view=None)

    async def finish_game(self, interaction, bust):
        dealer_hand = self.game['dealer']
        player_hand = self.game['player']
        draw = self.game['draw']
        score = self.game['score']
        db = self.game['db']
        bet = self.game['bet']
        user_id = self.user.id

        # Dealer draws until 17+
        while score(dealer_hand) < 17:
            dealer_hand.append(draw())

        player_score = score(player_hand)
        dealer_score = score(dealer_hand)

        emoji = "<:arcadiacoin:1378656679704395796>"

        if bust:
            result = f"💥 You busted with **{player_score}**. Dealer wins.\nYou lost ₱{bet:,} {emoji}."
        elif dealer_score > 21 or player_score > dealer_score:
            result = f"✅ You win! You earned ₱{bet * 2:,} {emoji}."
            db.update_one({'_id': str(user_id)}, {'$inc': {'balance': bet * 2}}, upsert=True)
        elif player_score == dealer_score:
            result = f"🤝 It's a tie. You got back ₱{bet:,} {emoji}."
            db.update_one({'_id': str(user_id)}, {'$inc': {'balance': bet}}, upsert=True)
        else:
            result = f"❌ Dealer wins with **{dealer_score}**. You lost ₱{bet:,} {emoji}."

        final_embed = self.game['embed'](player_hand, dealer_hand, reveal=True)
        final_embed.add_field(name="Result", value=result, inline=False)

        await interaction.response.edit_message(embed=final_embed, view=None)


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users

    def draw_card(self):
        cards = ['A'] + list(map(str, range(2, 11))) + ['J', 'Q', 'K']
        return random.choice(cards)

    def calculate_score(self, hand):
        values = {'J': 10, 'Q': 10, 'K': 10, 'A': 11}
        score = sum(values.get(card, int(card)) for card in hand)
        aces = hand.count('A')
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def format_hand(self, hand):
        return ' '.join(f"`{card}`" for card in hand)

    def build_embed(self, player_hand, dealer_hand, reveal=False):
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blurple())
        embed.add_field(name="Your Hand", value=f"{self.format_hand(player_hand)}\n**Total:** {self.calculate_score(player_hand)}", inline=False)
        if reveal:
            embed.add_field(name="Dealer's Hand", value=f"{self.format_hand(dealer_hand)}\n**Total:** {self.calculate_score(dealer_hand)}", inline=False)
        else:
            embed.add_field(name="Dealer's Hand", value=f"`{dealer_hand[0]}` `?`", inline=False)
        return embed

    @app_commands.command(name="blackjack", description="Play blackjack and bet your coins.")
    @app_commands.describe(amount="The amount to bet")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        await self.start_game(interaction, amount)

    @commands.command(name="blackjack")
    async def blackjack_manual(self, ctx: commands.Context, amount: int):
        # Wrap context into an Interaction-like object to reuse start_game logic
        class DummyInteraction:
            def __init__(self, ctx):
                self.user = ctx.author
                self.ctx = ctx
            async def response_send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)
            async def response_edit_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)
            async def send(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def response(self):
                return self

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

            async def send_message(self, *args, **kwargs):
                return await self.ctx.send(*args, **kwargs)

        dummy_interaction = DummyInteraction(ctx)
        await self.start_game(dummy_interaction, amount, manual_ctx=ctx)

    async def start_game(self, interaction, amount: int, manual_ctx=None):
        user_id = str(interaction.user.id)
        user_data = self.db.find_one({'_id': user_id})
        balance = user_data.get('balance', 0) if user_data else 0

        if amount <= 0:
            if manual_ctx:
                return await manual_ctx.send("❌ Bet must be more than 0.")
            else:
                return await interaction.response.send_message("❌ Bet must be more than 0.", ephemeral=True)
        if balance < amount:
            if manual_ctx:
                return await manual_ctx.send(f"❌ You only have ₱{balance:,}.")
            else:
                return await interaction.response.send_message(f"❌ You only have ₱{balance:,}.", ephemeral=True)

        # Deduct bet
        self.db.update_one({'_id': user_id}, {'$inc': {'balance': -amount}}, upsert=True)

        player_hand = [self.draw_card(), self.draw_card()]
        dealer_hand = [self.draw_card()]

        game_data = {
            'bet': amount,
            'player': player_hand,
            'dealer': dealer_hand,
            'draw': self.draw_card,
            'score': self.calculate_score,
            'embed': self.build_embed,
            'db': self.db,
        }

        view = BlackjackView(interaction.user, game_data, self.bot, timeout=60)
        embed = self.build_embed(player_hand, dealer_hand, reveal=False)
        if manual_ctx:
            msg = await manual_ctx.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()
        view.message = msg


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
