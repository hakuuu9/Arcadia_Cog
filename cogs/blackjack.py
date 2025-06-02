import discord
from discord.ext import commands
from discord import app_commands
import random
from pymongo import MongoClient
from config import MONGO_URL  # Your mongo URL here

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users

    def draw_card(self):
        cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]
        return random.choice(cards)

    def calculate_score(self, hand):
        score = sum(hand)
        ace_count = hand.count(11)
        while score > 21 and ace_count:
            score -= 10
            ace_count -= 1
        return score

    def create_embed(self, player_hand, dealer_hand, reveal_dealer=False):
        def cards_str(hand):
            return ' '.join(str(card) for card in hand)

        embed = discord.Embed(title="Blackjack", color=discord.Color.gold())
        embed.add_field(name="Your Hand", value=f"{cards_str(player_hand)}\nTotal: {self.calculate_score(player_hand)}", inline=False)
        if reveal_dealer:
            embed.add_field(name="Dealer's Hand", value=f"{cards_str(dealer_hand)}\nTotal: {self.calculate_score(dealer_hand)}", inline=False)
        else:
            embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} ??", inline=False)
        return embed

    async def get_balance(self, user_id):
        user_data = self.db.find_one({'_id': str(user_id)})
        return user_data['balance'] if user_data and 'balance' in user_data else 0

    async def update_balance(self, user_id, amount):
        self.db.update_one({'_id': str(user_id)}, {'$inc': {'balance': amount}}, upsert=True)

    @commands.command(name='blackjack')
    async def blackjack_command(self, ctx, bet: int):
        await self.start_blackjack(ctx, ctx.author, bet)

    @app_commands.command(name='blackjack', description="Play blackjack")
    @app_commands.describe(bet='Amount of coins to bet')
    async def blackjack_slash(self, interaction: discord.Interaction, bet: int):
        await self.start_blackjack(interaction, interaction.user, bet)

    async def start_blackjack(self, ctx_or_interaction, user, bet):
        balance = await self.get_balance(user.id)
        emoji = "<:arcadiacoin:1378656679704395796>"

        if bet <= 0:
            return await self.send_message(ctx_or_interaction, "❌ Bet must be greater than zero.")
        if bet > balance:
            return await self.send_message(ctx_or_interaction, f"❌ You don't have enough coins. Your balance: ₱{balance:,} {emoji}")

        await self.update_balance(user.id, -bet)

        player_hand = [self.draw_card(), self.draw_card()]
        dealer_hand = [self.draw_card(), self.draw_card()]

        game = {
            'player': player_hand,
            'dealer': dealer_hand,
            'draw': self.draw_card,
            'score': self.calculate_score,
            'db': self.db,
            'bet': bet,
            'embed_func': self.create_embed,
        }

        embed = self.create_embed(player_hand, dealer_hand, reveal_dealer=False)
        view = BlackjackView(user, game, self.bot)
        message = await self.send_message(ctx_or_interaction, embed=embed, view=view)
        view.message = message

    async def send_message(self, ctx_or_interaction, content=None, embed=None, view=None):
        if isinstance(ctx_or_interaction, commands.Context):
            return await ctx_or_interaction.send(content=content, embed=embed, view=view)
        else:
            await ctx_or_interaction.response.defer()
            return await ctx_or_interaction.followup.send(content=content, embed=embed, view=view)

class BlackjackView(discord.ui.View):
    def __init__(self, user, game, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.user = user
        self.game = game
        self.bot = bot
        self.message = None
        self.responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True

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

    async def update_message(self, interaction: discord.Interaction):
        embed = self.game['embed_func'](self.game['player'], self.game['dealer'], reveal_dealer=False)
        if not self.responded:
            await interaction.response.edit_message(embed=embed, view=self)
            self.responded = True
        else:
            await interaction.followup.edit_message(self.message.id, embed=embed, view=self)

    async def finish_game(self, interaction: discord.Interaction, bust: bool):
        dealer_hand = self.game['dealer']
        player_hand = self.game['player']
        draw = self.game['draw']
        score = self.game['score']
        db = self.game['db']
        bet = self.game['bet']
        user_id = self.user.id
        embed_func = self.game['embed_func']

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

        final_embed = embed_func(player_hand, dealer_hand, reveal_dealer=True)
        final_embed.add_field(name="Result", value=result, inline=False)

        if not self.responded:
            await interaction.response.edit_message(embed=final_embed, view=None)
            self.responded = True
        else:
            await interaction.followup.edit_message(self.message.id, embed=final_embed, view=None)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
