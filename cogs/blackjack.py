import discord
from discord.ext import commands
from discord import app_commands
import random
from pymongo import MongoClient
from config import MONGO_URL

CARD_EMOJIS = {
    2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣",
    8: "8️⃣", 9: "9️⃣", 10: "🔟", 11: "🅰️"  # Ace = 11
}

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.users
        self.active_games = {}

    def draw_card(self):
        return random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])

    def calculate_score(self, hand):
        score = sum(hand)
        ace_count = hand.count(11)
        while score > 21 and ace_count:
            score -= 10
            ace_count -= 1
        return score

    def create_embed(self, player_hand, dealer_hand, reveal_dealer=False):
        def cards_str(hand):
            return ' '.join(CARD_EMOJIS.get(card, str(card)) for card in hand)

        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blurple())
        embed.add_field(name="👤 Your Hand", value=f"{cards_str(player_hand)}\n**Total:** {self.calculate_score(player_hand)}", inline=False)
        if reveal_dealer:
            embed.add_field(name="💼 Dealer's Hand", value=f"{cards_str(dealer_hand)}\n**Total:** {self.calculate_score(dealer_hand)}", inline=False)
        else:
            embed.add_field(name="💼 Dealer's Hand", value=f"{CARD_EMOJIS.get(dealer_hand[0], str(dealer_hand[0]))} ❓", inline=False)
        embed.set_footer(text="⏳ Respond within 60s or the game will time out.")
        return embed

    async def get_balance(self, user_id):
        user_data = self.db.find_one({'_id': str(user_id)})
        return user_data['balance'] if user_data and 'balance' in user_data else 0

    async def update_balance(self, user_id, amount):
        print(f"[Balance Update] User {user_id}: {'+' if amount > 0 else ''}{amount}")
        self.db.update_one({'_id': str(user_id)}, {'$inc': {'balance': amount}}, upsert=True)

    @commands.command(name='blackjack')
    async def blackjack_command(self, ctx, bet: int):
        await self.start_blackjack(ctx, ctx.author, bet)

    @app_commands.command(name='blackjack', description="Play a stylish game of blackjack!")
    @app_commands.describe(bet='How much would you like to bet?')
    async def blackjack_slash(self, interaction: discord.Interaction, bet: int):
        await self.start_blackjack(interaction, interaction.user, bet)

    async def start_blackjack(self, ctx_or_interaction, user, bet):
        emoji = "<:arcadiacoin:1378656679704395796>"

        if user.id in self.active_games:
            return await self.send_message(ctx_or_interaction, "⚠️ You already have an active game.")

        balance = await self.get_balance(user.id)

        if bet <= 0:
            return await self.send_message(ctx_or_interaction, "❌ Bet must be greater than zero.")
        if bet > balance:
            return await self.send_message(ctx_or_interaction, f"💸 You don't have enough coins. Balance: ₱{balance:,} {emoji}")

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
        self.active_games[user.id] = view

    async def send_message(self, ctx_or_interaction, content=None, embed=None, view=None):
        if isinstance(ctx_or_interaction, commands.Context):
            return await ctx_or_interaction.send(content=content, embed=embed, view=view)
        else:
            if not ctx_or_interaction.response.is_done():
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
            await interaction.response.send_message("⛔ This is not your game!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="➕ Hit", style=discord.ButtonStyle.green, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game['player'].append(self.game['draw']())
        if self.game['score'](self.game['player']) > 21:
            await self.finish_game(interaction, bust=True)
            self.stop()
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="✅ Stand", style=discord.ButtonStyle.red, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_game(interaction, bust=False)
        self.stop()

    async def update_message(self, interaction: discord.Interaction):
        embed = self.game['embed_func'](self.game['player'], self.game['dealer'], reveal_dealer=False)
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            await self.message.edit(embed=embed, view=self)
        self.responded = True

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
            result = f"💥 You busted with **{player_score}**.\n**Dealer wins!**\nYou lost ₱{bet:,} {emoji}."
        elif dealer_score > 21 or player_score > dealer_score:
            result = f"🎉 **You win!**\nYou earned ₱{bet * 2:,} {emoji}!"
            await db.update_one({'_id': str(user_id)}, {'$inc': {'balance': bet * 2}}, upsert=True)
        elif player_score == dealer_score:
            result = f"🤝 It's a tie!\nYou got back ₱{bet:,} {emoji}."
            await db.update_one({'_id': str(user_id)}, {'$inc': {'balance': bet}}, upsert=True)
        else:
            result = f"❌ Dealer wins with **{dealer_score}**.\nYou lost ₱{bet:,} {emoji}."

        final_embed = embed_func(player_hand, dealer_hand, reveal_dealer=True)
        final_embed.add_field(name="🏁 Result", value=result, inline=False)

        try:
            await interaction.response.edit_message(embed=final_embed, view=None)
        except discord.InteractionResponded:
            await self.message.edit(embed=final_embed, view=None)

        self.bot.get_cog("Blackjack").active_games.pop(user_id, None)
        self.responded = True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
        self.bot.get_cog("Blackjack").active_games.pop(self.user.id, None)

async def setup(bot):
    await bot.add_cog(Blackjack(bot))
