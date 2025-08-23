import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import datetime

# Role ID for giveaway staff
GIVEAWAY_STAFF_ID = 1347181345922748456  

def is_giveaway_staff(interaction: discord.Interaction) -> bool:
    return any(role.id == GIVEAWAY_STAFF_ID for role in interaction.user.roles)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = {}  # {message_id: {...}}

    # ========== START GIVEAWAY ==========
    @app_commands.check(is_giveaway_staff)
    @app_commands.command(
        name="giveaway",
        description="Start a giveaway event."
    )
    async def giveaway(
        self, interaction: discord.Interaction,
        duration: str,
        winners: int,
        prize: str,
        channel: discord.TextChannel,
        required_role: discord.Role = None,
        extra_entries_role: discord.Role = None,
        embed_color: str = "#ff0000",
        thumbnail: discord.Attachment = None,
        image: discord.Attachment = None
    ):
        await interaction.response.defer(ephemeral=True)

        # Convert duration
        time_multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = duration[-1]
        if unit not in time_multipliers:
            return await interaction.followup.send("❌ Invalid duration format! Use s/m/h/d.", ephemeral=True)
        try:
            duration_seconds = int(duration[:-1]) * time_multipliers[unit]
        except ValueError:
            return await interaction.followup.send("❌ Invalid number for duration!", ephemeral=True)

        end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)

        # Embed color
        try:
            color = discord.Color.from_str(embed_color)
        except Exception:
            color = discord.Color.red()

        # Role requirement text
        role_text = required_role.mention if required_role else "None"
        extra_role_text = extra_entries_role.mention if extra_entries_role else "None"

        # Create embed
        embed = discord.Embed(
            title="**ARCADIA GIVEAWAY**",
            description=(
                f"React with 🎟️ to enter!\n"
                f"Total Entries: `0`\n\n"
                f"Winners: `{winners}`\n"
                f"Ends: <t:{int(end_time.timestamp())}:R>\n"
                f"Requirements: {role_text}\n"
                f"Extra Entries Role: {extra_role_text}"
            ),
            color=color
        )

        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        if image:
            embed.set_image(url=image.url)

        # Default footer
        embed.set_footer(text="They Say That The Best Blaze Burns The Brightest When Circumstances Are At Their Worst.")

        # Send giveaway message
        giveaway_msg = await channel.send(embed=embed)
        await giveaway_msg.add_reaction("🎟️")

        # Store giveaway info
        self.giveaways[giveaway_msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "channel": channel.id,
            "host": interaction.user.id,
            "required_role": required_role.id if required_role else None,
            "extra_entries_role": extra_entries_role.id if extra_entries_role else None,
            "winner_ids": []
        }

        await interaction.followup.send(f"✅ Giveaway started in {channel.mention} (ID: `{giveaway_msg.id}`).", ephemeral=True)

        # Auto end
        self.bot.loop.create_task(self.end_giveaway_after(giveaway_msg.id, duration_seconds))

    # ========== FINISH GIVEAWAY ==========
    async def finish_giveaway(self, giveaway_id: int):
        giveaway = self.giveaways.pop(giveaway_id, None)
        if not giveaway:
            return

        channel = self.bot.get_channel(giveaway["channel"])
        if not channel:
            return

        try:
            message = await channel.fetch_message(giveaway_id)
        except discord.NotFound:
            return

        reaction = discord.utils.get(message.reactions, emoji="🎟️")
        if not reaction:
            return await channel.send("❌ No participants for this giveaway.")

        users = [u async for u in reaction.users() if not u.bot]

        # Filter required role
        if giveaway["required_role"]:
            users = [u for u in users if any(r.id == giveaway["required_role"] for r in u.roles)]

        if not users:
            return await channel.send("❌ No valid participants for this giveaway.")

        # Extra entries
        weighted_users = []
        for u in users:
            entries = 2 if giveaway["extra_entries_role"] and any(r.id == giveaway["extra_entries_role"] for r in u.roles) else 1
            weighted_users.extend([u]*entries)

        winners_count = min(giveaway["winners"], len(weighted_users))
        winners = random.sample(weighted_users, winners_count)
        unique_winners = list({w.id: w for w in winners}.values())
        giveaway["winner_ids"] = [w.id for w in unique_winners]

        winner_mentions = ", ".join(w.mention for w in unique_winners)

        # Winner embed
        win_embed = discord.Embed(
            title="🎉 Giveaway Winners 🎉",
            description=(
                f"**Prize:** {giveaway['prize']}\n"
                f"**Winners:** {winner_mentions}\n"
                f"**Hosted By:** <@{giveaway['host']}>"
            ),
            color=discord.Color.green()
        )
        win_embed.set_footer(text=f"Reroll with: /giveaway_reroll {giveaway_id}")
        await channel.send(embed=win_embed)

        # Update original message
        embed = message.embeds[0]
        embed.color = discord.Color.dark_gray()
        embed.description += f"\n\n**Ended!** Winners: {winner_mentions}"
        await message.edit(embed=embed)

    # ... include reaction add/remove listeners and entry updates same as before

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
