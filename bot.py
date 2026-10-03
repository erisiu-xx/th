"""
Tag application bot (discord.py 2.x)

Flow:  panel embed + button -> dropdown of tags -> modal (Roblox profile)
       -> private channel with applicant + that tag's manager role.

Config: DISCORD_TOKEN and APPLICATION_CATEGORY_ID env vars, tags in tags.json.
Then use /setup_panel in the channel where the panel should live.
"""
import json
import os
import re
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ["DISCORD_TOKEN"]
APPLICATION_CATEGORY_ID = int(os.environ["APPLICATION_CATEGORY_ID"])

# tags.json: {"SEKAI": {"group_id": 123, "manager_role_id": 456}, ...}
with open(os.path.join(os.path.dirname(__file__), "tags.json"), encoding="utf-8") as f:
    TAGS = json.load(f)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- Modal: Roblox profile ----------
class ApplyModal(discord.ui.Modal):
    roblox = discord.ui.TextInput(
        label="Your Roblox profile",
        placeholder="Profile link or username",
        required=True,
        max_length=200,
    )

    def __init__(self, tag: str):
        super().__init__(title=f"Apply for [{tag}]")
        self.tag = tag

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        tag_cfg = TAGS[self.tag]
        manager_role = guild.get_role(tag_cfg["manager_role_id"])
        category = guild.get_channel(APPLICATION_CATEGORY_ID)

        if manager_role is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "Bot isn't configured correctly for this tag, contact an admin.",
                ephemeral=True,
            )
            return

        # one open application per user per tag
        channel_name = f"{self.tag}-{interaction.user.name}".lower()
        channel_name = re.sub(r"[^a-z0-9\-_]", "", channel_name)[:90]
        if discord.utils.get(category.text_channels, name=channel_name):
            await interaction.response.send_message(
                "You already have an open application for this tag.", ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            manager_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
        }

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Application for [{self.tag}] by {interaction.user} ({interaction.user.id})",
        )

        embed = discord.Embed(
            title=f"Application: [{self.tag}]",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Applicant", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="Group",
            value=f"[Open group](https://www.roblox.com/groups/{tag_cfg['group_id']})",
            inline=True,
        )
        embed.add_field(name="Roblox profile", value=self.roblox.value, inline=False)

        await channel.send(
            content=f"{manager_role.mention} {interaction.user.mention}",
            embed=embed,
            view=CloseView(),
            allowed_mentions=discord.AllowedMentions(roles=True, users=True),
        )
        await interaction.response.send_message(
            f"Your application was created: {channel.mention}", ephemeral=True
        )


# ---------- Dropdown ----------
class TagSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=name) for name in TAGS]
        super().__init__(placeholder="Choose a tag...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # a modal can be sent directly as the response to a select interaction
        await interaction.response.send_modal(ApplyModal(self.values[0]))


class TagSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(TagSelect())


# ---------- Panel button (persistent) ----------
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apply for a tag",
        style=discord.ButtonStyle.primary,
        custom_id="tag_panel:apply",
    )
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select the tag you want to apply for:",
            view=TagSelectView(),
            ephemeral=True,
        )


# ---------- Close button inside application channels (persistent) ----------
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        custom_id="tag_panel:close",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # only managers of any tag (or admins) can close
        manager_ids = {cfg["manager_role_id"] for cfg in TAGS.values()}
        is_manager = any(r.id in manager_ids for r in interaction.user.roles)
        if not (is_manager or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "Only managers can close this.", ephemeral=True
            )
            return
        await interaction.response.send_message("Closing channel...")
        await interaction.channel.delete()


# ---------- Setup ----------
@bot.event
async def setup_hook():
    bot.add_view(PanelView())
    bot.add_view(CloseView())
    await bot.tree.sync()


@bot.tree.command(name="setup_panel", description="Send the tag application panel here")
@app_commands.default_permissions(administrator=True)
async def setup_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Tag Applications",
        description=(
            "Want to join one of our tags?\n"
            "Click the button below, pick a tag, and fill in your Roblox profile.\n"
            "A private channel will be opened with that tag's managers."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Available tags",
        value="\n".join(
            f"**[{name}]** - [group](https://www.roblox.com/groups/{cfg['group_id']})"
            for name, cfg in TAGS.items()
        ),
        inline=False,
    )
    await interaction.channel.send(embed=embed, view=PanelView())
    await interaction.response.send_message("Panel sent.", ephemeral=True)


bot.run(TOKEN)
