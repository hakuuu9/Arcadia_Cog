import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URL, CHANNEL_ID_TO_NOTIFY

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.customroles
        self.trio_role = {879936602414133288, 1275065396705362041, 1092795368556732478}
        self.check_expiry.start()

    def is_staff(self, user: discord.User | discord.Member):
        return user.id in self.trio_role

    @app_commands.command(name="role-list", description="Register a custom role for a member (staff only)")
    @app_commands.describe(member="Member to assign custom role", role_name="Name of the custom role")
    async def role_list(self, interaction: discord.Interaction, member: discord.Member, role_name: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        role_name = role_name.lower()
        created_at = datetime.utcnow()

        self.db.update_one(
            {"_id": f"{member.id}_{role_name}"},
            {
                "$set": {
                    "member_id": member.id,
                    "member_name": str(member),
                    "role_name": role_name,
                    "created_at": created_at,
                    "expires_at": created_at + timedelta(days=15)
                }
            },
            upsert=True
        )

        await interaction.response.send_message(f"✅ Registered role **{role_name}** for {member.mention} (valid for 15 days).")

    @app_commands.command(name="role-edit", description="Edit a member's custom role name (staff only)")
    @app_commands.describe(member="Member whose role you want to edit", old_role_name="Current role name", new_role_name="New role name")
    async def role_edit(self, interaction: discord.Interaction, member: discord.Member, old_role_name: str, new_role_name: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        old_role_name = old_role_name.lower()
        new_role_name = new_role_name.lower()

        existing = self.db.find_one({"_id": f"{member.id}_{old_role_name}"})
        if not existing:
            return await interaction.response.send_message(f"❌ No role entry found for {member.mention} with role **{old_role_name}**.", ephemeral=True)

        self.db.delete_one({"_id": f"{member.id}_{old_role_name}"})
        self.db.insert_one({
            "_id": f"{member.id}_{new_role_name}",
            "member_id": member.id,
            "member_name": str(member),
            "role_name": new_role_name,
            "created_at": existing.get("created_at", datetime.utcnow()),
            "expires_at": existing.get("created_at", datetime.utcnow()) + timedelta(days=15)
        })

        await interaction.response.send_message(f"✅ Role name updated to **{new_role_name}** for {member.mention}.")

    @app_commands.command(name="role-delete", description="Delete a member's custom role entry (staff only)")
    @app_commands.describe(member="Member whose role to delete", role_name="Role name to delete")
    async def role_delete(self, interaction: discord.Interaction, member: discord.Member, role_name: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        role_name = role_name.lower()
        result = self.db.delete_one({"_id": f"{member.id}_{role_name}"})

        if result.deleted_count == 0:
            return await interaction.response.send_message(f"❌ No entry found for {member.mention} with role **{role_name}**.", ephemeral=True)

        await interaction.response.send_message(f"🗑️ Deleted role **{role_name}** entry for {member.mention}.")

    @app_commands.command(name="role-view", description="View all custom role assignments (visible to everyone)")
    async def role_view(self, interaction: discord.Interaction):
        results = list(self.db.find({}))
        if not results:
            return await interaction.response.send_message("No custom role entries found.", ephemeral=True)

        now = datetime.utcnow()
        lines = []

        for r in results:
            member_name = r.get("member_name", "Unknown Member")
            role_name = r.get("role_name", "Unknown Role")
            expires_at = r.get("expires_at")

            if expires_at:
                delta = expires_at - now
                if delta.total_seconds() <= 0:
                    time_left = "*expired*"
                else:
                    days = delta.days
                    hours = delta.seconds // 3600
                    mins = (delta.seconds % 3600) // 60
                    parts = []
                    if days > 0:
                        parts.append(f"{days} day{'s' if days != 1 else ''}")
                    if hours > 0:
                        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                    if mins > 0:
                        parts.append(f"{mins} min{'s' if mins != 1 else ''}")
                    time_left = "in " + ", ".join(parts)
            else:
                time_left = "*unknown*"

            lines.append(f"**{member_name}** — Role: **{role_name}** — ⏳ {time_left}")

        # Pagination for messages longer than 2000 characters
        chunks = []
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > 1900:
                chunks.append(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            chunks.append(chunk)

        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.response.send_message(chunk)
            else:
                await interaction.followup.send(chunk)

    @tasks.loop(hours=1)
    async def check_expiry(self):
        now = datetime.utcnow()
        expired = list(self.db.find({"expires_at": {"$lte": now}}))

        if not expired:
            return

        channel = self.bot.get_channel(CHANNEL_ID_TO_NOTIFY)
        if not channel:
            return

        for entry in expired:
            member_name = entry.get("member_name", "Unknown Member")
            role_name = entry.get("role_name", "Unknown Role")
            await channel.send(f"⏰ Custom role **{role_name}** for **{member_name}** has expired.")

            # Remove expired entry
            self.db.delete_one({"_id": entry["_id"]})

    @check_expiry.before_loop
    async def before_check_expiry(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
