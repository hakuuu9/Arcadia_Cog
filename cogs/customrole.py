import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL

CHANNEL_ID_TO_NOTIFY = 1357656511974871202  # Replace with your channel ID

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.customroles
        self.trio_role = {879936602414133288, 1275065396705362041, 1092795368556732478}
        self.check_expiry.start()

    def is_staff(self, user: discord.User | discord.Member):
        return user.id in self.trio_role

    @app_commands.command(name="role-list", description="Add a member's custom role (staff only)")
    @app_commands.describe(member="Member to add", role_name="Name of the custom role")
    async def role_list(self, interaction: discord.Interaction, member: discord.Member, role_name: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        role_name = role_name.lower()
        valid_until = datetime.utcnow() + timedelta(days=15)

        self.db.update_one(
            {"_id": f"{member.id}_{role_name}"},
            {"$set": {
                "member_id": member.id,
                "member_name": str(member),
                "role_name": role_name,
                "valid_until": valid_until
            }},
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Added role **{role_name}** for {member.mention} (valid until <t:{int(valid_until.timestamp())}:R>)."
        )

    @app_commands.command(name="role-edit", description="Edit a custom role's name (staff only)")
    @app_commands.describe(member="Member to edit", role_name="Current role name", new_role_name="New role name")
    async def role_edit(self, interaction: discord.Interaction, member: discord.Member, role_name: str, new_role_name: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

        role_name = role_name.lower()
        new_role_name = new_role_name.lower()

        entry = self.db.find_one({"_id": f"{member.id}_{role_name}"})
        if not entry:
            return await interaction.response.send_message("❌ No such role entry found.", ephemeral=True)

        # Delete old and insert updated entry
        self.db.delete_one({"_id": f"{member.id}_{role_name}"})
        entry["_id"] = f"{member.id}_{new_role_name}"
        entry["role_name"] = new_role_name
        entry["member_name"] = str(member)

        self.db.update_one(
            {"_id": entry["_id"]},
            {"$set": entry},
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Role name updated for {member.mention}:\n- New name: **{new_role_name}**"
        )

    @app_commands.command(name="role-view", description="View all custom roles")
    async def role_view(self, interaction: discord.Interaction):
        entries = list(self.db.find({}))
        if not entries:
            return await interaction.response.send_message("No custom roles found.", ephemeral=True)

        lines = []
        for r in entries:
            member_name = r.get("member_name", "Unknown Member")
            role_name = r.get("role_name", "Unknown Role")
            valid_until = r.get("valid_until")
            valid_str = f"<t:{int(valid_until.timestamp())}:R>" if valid_until else "Unknown"
            lines.append(f"**{member_name}** — Role: **{role_name}**\nValid until: {valid_str}")

        chunks = []
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > 1900:
                chunks.append(chunk)
                chunk = ""
            chunk += line + "\n\n"
        if chunk:
            chunks.append(chunk)

        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.response.send_message(chunk)
            else:
                await interaction.followup.send(chunk)

    @tasks.loop(minutes=1)
    async def check_expiry(self):
        expired = list(self.db.find({
            "valid_until": {"$lt": datetime.utcnow()}
        }))

        if expired:
            channel = self.bot.get_channel(CHANNEL_ID_TO_NOTIFY)
            if channel:
                for entry in expired:
                    member_name = entry.get("member_name", "Unknown")
                    role_name = entry.get("role_name", "Unknown Role")
                    await channel.send(f"⚠️ Custom role **{role_name}** for **{member_name}** has expired.")
                    self.db.delete_one({"_id": entry["_id"]})

    @check_expiry.before_loop
    async def before_check_expiry(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
