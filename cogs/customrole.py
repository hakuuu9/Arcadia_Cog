import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from config import MONGO_URL

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = MongoClient(MONGO_URL).hxhbot.customroles  # Mongo collection for role notes

        # Allowed staff USER IDs (renamed to trio_role)
        self.trio_role = {879936602414133288, 1275065396705362041, 1092795368556732478}

    def is_staff(self, user: discord.User | discord.Member):
        return user.id in self.trio_role

    @app_commands.command(name="role-list", description="Add a note to a member's custom role (staff only)")
    @app_commands.describe(member="Member to add note for", role_name="Name of the custom role", note="Note about the role purchase")
    async def role_list(self, interaction: discord.Interaction, member: discord.Member, role_name: str, note: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        role_name = role_name.lower()

        # Upsert a document keyed by member ID + role_name
        self.db.update_one(
            {"_id": f"{member.id}_{role_name}"},
            {"$set": {"member_id": member.id, "member_name": str(member), "role_name": role_name, "note": note}},
            upsert=True
        )

        await interaction.response.send_message(f"✅ Note added for {member.mention}'s role **{role_name}**:\n{note}")

    @app_commands.command(name="role-edit", description="Edit a note for a member's custom role (staff only)")
    @app_commands.describe(member="Member to edit note for", role_name="Name of the custom role", note="New note")
    async def role_edit(self, interaction: discord.Interaction, member: discord.Member, role_name: str, note: str):
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

        role_name = role_name.lower()

        existing = self.db.find_one({"_id": f"{member.id}_{role_name}"})
        if not existing:
            return await interaction.response.send_message(f"❌ No note found for {member.mention} with role **{role_name}**.", ephemeral=True)

        self.db.update_one(
            {"_id": f"{member.id}_{role_name}"},
            {"$set": {"note": note}}
        )

        await interaction.response.send_message(f"✅ Note updated for {member.mention}'s role **{role_name}**:\n{note}")

    @app_commands.command(name="role-view", description="View all custom role notes")
    async def role_view(self, interaction: discord.Interaction):
        results = list(self.db.find({}))
        if not results:
            return await interaction.response.send_message("No custom role notes found.", ephemeral=True)

        lines = []
        for r in results:
            member_name = r.get("member_name", "Unknown Member")
            role_name = r.get("role_name", "Unknown Role")
            note = r.get("note", "")
            lines.append(f"**{member_name}** — Role: **{role_name}**\nNote: {note}")

        # Discord messages max length ~2000, split if needed
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

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
