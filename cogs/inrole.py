import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

class InRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_role(self, guild: discord.Guild, role_input: str):
        role = None
        if role_input.startswith("<@&") and role_input.endswith(">"):
            role_id = int(role_input[3:-1])
            role = guild.get_role(role_id)
        elif role_input.isdigit():
            role = guild.get_role(int(role_input))
        else:
            role = discord.utils.find(lambda r: r.name.lower() == role_input.lower(), guild.roles)
        return role

    async def send_inrole_embed(self, ctx, role: discord.Role):
        members_with_role = [f"{i+1}. {member.mention}" for i, member in enumerate(role.members)]

        if not members_with_role:
            await ctx.send(f"No members currently have the role **{role.name}**.")
            return

        pages = [members_with_role[i:i + 10] for i in range(0, len(members_with_role), 10)]
        total_pages = len(pages)

        def create_embed(page_index):
            embed = discord.Embed(
                title=f"Members in Role: {role.name}",
                description="\n".join(pages[page_index]),
                color=discord.Color.blurple()
            )
            if role.icon:
                embed.set_thumbnail(url=role.icon.url)
            else:
                embed.set_thumbnail(url="https://i.imgur.com/JxsCfCe.gif")
            embed.set_footer(text=f"Page {page_index + 1} of {total_pages} • Total members: {len(members_with_role)}")
            return embed

        class PaginationView(View):
            def __init__(self):
                super().__init__(timeout=300)
                self.page = 0

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
            async def previous(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command user can use this.", ephemeral=True)
                    return
                self.page = (self.page - 1) % total_pages
                await interaction.response.edit_message(embed=create_embed(self.page), view=self)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command user can use this.", ephemeral=True)
                    return
                self.page = (self.page + 1) % total_pages
                await interaction.response.edit_message(embed=create_embed(self.page), view=self)

        await ctx.send(embed=create_embed(0), view=PaginationView())

    @commands.command(name="inrole")
    async def inrole_prefix(self, ctx, *, role_input: str):
        role = await self.fetch_role(ctx.guild, role_input)
        if not role:
            await ctx.send("❌ Role not found.")
            return
        await self.send_inrole_embed(ctx, role)

    @app_commands.command(name="inrole", description="List all members in a specific role")
    @app_commands.describe(role_input="Role name, mention, or ID")
    async def inrole_slash(self, interaction: discord.Interaction, role_input: str):
        role = await self.fetch_role(interaction.guild, role_input)
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return
        await interaction.response.defer()
        class DummyCtx:
            def __init__(self, author, send, guild):
                self.author = author
                self.send = send
                self.guild = guild
        dummy_ctx = DummyCtx(interaction.user, interaction.followup.send, interaction.guild)
        await self.send_inrole_embed(dummy_ctx, role)

    @inrole_slash.autocomplete('role_input')
    async def autocomplete_roles(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=role.name, value=role.name)
            for role in interaction.guild.roles
            if current.lower() in role.name.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(InRole(bot))
