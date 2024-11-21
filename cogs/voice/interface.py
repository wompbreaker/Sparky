from typing import List
from logging import getLogger
import json

import discord
import requests

from helpers import (
    make_embed_warning, 
    make_embed_success,
    make_embed_lockdown,
    make_embed_visible
)
from .utils import *
from .db import get_custom_voice_channels
from .helper import *

log = getLogger(__name__)

class DisconnectSelect(discord.ui.Select):
    def __init__(self, voice_members: List[discord.Member]):
        options = [discord.SelectOption(
            emoji='\N{BUST IN SILHOUETTE}', 
            label=f'{member.name} ({member.id})', 
            value=str(member.id)
        ) for member in voice_members]
        super().__init__(
            placeholder="Choose members...", 
            options=options, min_values=1, max_values=min(len(options), 25)
        )
    
    async def callback(self, interaction: discord.Interaction):
        member_ids = [int(value) for value in self.values]
        success = 0
        failed = 0
        for member_id in member_ids:
            if member_id == interaction.user.id:
                failed += 1
                continue
            member = interaction.guild.get_member(member_id)
            try:
                await member.move_to(None)
                success += 1
            except Exception as e:
                log.error(f"Failed to disconnect member: {e}")
                failed += 1
                continue
        message = f"Successfully **disconnected** `{success}` members"
        if failed:
            message += f" (`{failed}` failed)"
        lrm = "\u200E"
        embed = discord.Embed(
            color=discord.Color.green(),
            description=f"{lrm}{CHECKED} {interaction.user.mention}: "
                        f"{lrm}{message}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DisconnectView(discord.ui.View):
    def __init__(self, voice_members: List[discord.Member]):
        super().__init__(timeout=None)
        self.voice_members = voice_members
        self.add_item(DisconnectSelect(voice_members))

class ActivitySelect(discord.ui.Select):
    def __init__(self):
        # create a list of options from the ACTIVITIES dictionary
        try:
            options = [discord.SelectOption(
                emoji=ACTIVITIES[activity]['activity_emoji'], 
                label=ACTIVITIES[activity]['activity_name'], 
                value=activity
            ) for activity in ACTIVITIES]
            super().__init__(
                placeholder="Choose an activity...", 
                options=options, min_values=1, max_values=1
            )
        except Exception as e:
            log.exception(f"Failed to create activity options: {e}")

    def activity_cover_url(self, activity_id: int) -> str:
        base_url = f"https://discord.com/api/v10/oauth2/applications/{activity_id}/assets"
        response = requests.get(base_url)
        data = json.loads(response.text)
        for asset in data:
            if asset['name'] == 'embedded_cover':
                asset_id = asset['id']
                break
        cover_url = f"https://cdn.discordapp.com/app-assets/{activity_id}/{asset_id}.png?size=4096"
        return cover_url

    async def callback(self, interaction: discord.Interaction):
        activity = self.values[0]
        activity_id = ACTIVITIES[activity]['activity_id']
        voice_channel = interaction.user.voice.channel
        activity_url = self.activity_cover_url(int(activity_id))

        try:
            invite = await voice_channel.create_invite(
                target_type=discord.InviteTarget.embedded_application,
                target_application_id=int(activity_id)
            )
            invite_url = invite.url
            embed = discord.Embed(
                title=ACTIVITIES[activity]['activity_name'],
                color=discord.Color.darker_gray(),
                description=f"Click the button **below** to start the **activity**!"
            )
            embed.set_thumbnail(url=activity_url)
            avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
            embed.set_author(name=voice_channel.name, icon_url=avatar_url)
            invite_view = ActivityInviteView(invite_url)
            await interaction.response.send_message(embed=embed, view=invite_view, ephemeral=True)
        except Exception as e:
            log.exception(f"Failed to start activity: {e}")
            await interaction.response.send_message("Failed to start the activity", ephemeral=True)

class ActivityView(discord.ui.View):
    def __init__(self):
        try:
            super().__init__(timeout=None)
            self.add_item(ActivitySelect())
        except Exception as e:
            log.exception(f"Failed to create activity view: {e}")

class ActivityInviteButton(discord.ui.Button):
    def __init__(self, activity_url: str):
        super().__init__(style=discord.ButtonStyle.link, label="Start activity", url=activity_url)

class ActivityInviteView(discord.ui.View):
    def __init__(self, activity_url: str):
        try:
            super().__init__(timeout=None)
            self.add_item(ActivityInviteButton(activity_url))
        except Exception as e:
            log.exception(f"Failed to create invite view: {e}")

class InterfaceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def user_is_voice_member(self, user: discord.Member) -> bool:
        voice_channels = user.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await get_custom_voice_channels(user.guild)
            except Exception as e:
                log.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    if user in voice_channel.members:
                        return True
        # raise NotVoiceMember("You're not connected to a **voice channel**")
    
    async def user_is_voice_owner(self, user: discord.Member) -> bool:
        voice_channels = user.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await get_custom_voice_channels(user.guild)
            except Exception as e:
                log.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    for custom_channel in custom_channels:
                        if custom_channel['channel_id'] == voice_channel.id:
                            owner_id = custom_channel['owner_id']
                            if user.id == owner_id:
                                return True
        # raise NotVoiceOwner("You don't own a **voice channel**!")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await self.user_is_voice_member(interaction.user):
            embed = make_embed_warning(
                interaction.user,
                "You're not connected to a **voice channel**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        elif not await self.user_is_voice_owner(interaction.user):
            embed = make_embed_warning(
                interaction.user,
                "You don't own a **voice channel**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    # async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception, item: discord.ui.Item[Any]) -> None:
    # 	if isinstance(error, NotVoiceMember):
    # 		embed = make_embed_warning(interaction.user, str(error))
    # 		await interaction.response.send_message(embed=embed, ephemeral=True)
    # 	elif isinstance(error, NotVoiceOwner):
    # 		embed = make_embed_warning(interaction.user, str(error))
    # 		await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @discord.ui.button(emoji=LOCK, style=discord.ButtonStyle.gray, row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_lock_channel(interaction.guild, interaction.user)
        if val:
            message = "Your **voice channel** is now **locked**"
            embed = make_embed_lockdown(interaction.user, True, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to **lock** the **voice channel**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=UNLOCK, style=discord.ButtonStyle.gray, row=0)
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_unlock_channel(interaction.guild, interaction.user)
        if val:
            message = "Your **voice channel** is now **unlocked**"
            embed = make_embed_lockdown(interaction.user, False, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to **unlock** the **voice channel**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=GHOST, style=discord.ButtonStyle.gray, row=0)
    async def ghost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_ghost_channel(interaction.guild, interaction.user)
        if val:
            message = "Your **voice channel** is now **ghosted**"
            embed = make_embed_visible(interaction.user, False, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to **hide** the **voice channel**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=REVEAL, style=discord.ButtonStyle.gray, row=0)
    async def reveal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_reveal_channel(interaction.guild, interaction.user)
        if val:
            message = "Your **voice channel** is now **visible**"
            embed = make_embed_visible(interaction.user, True, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to **reveal** the **voice channel**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=CLAIM, style=discord.ButtonStyle.gray, row=0)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        val = await helper_claim_channel(interaction.guild, interaction.user)
        if val is None:
            message = "You can't claim this **voice channel** - the owner is still active here"
            warning_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)
        elif val is True:
            message = "You have **claimed** this **voice channel**"
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "You already **own** this **voice channel**"
            warning_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)

    @discord.ui.button(emoji=DISCONNECT, style=discord.ButtonStyle.gray, row=1)
    async def disconnect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        voice_members = await helper_disconnect_member(interaction.guild, interaction.user)
        if voice_members:
            embed = discord.Embed(
                description=f"<{DISCONNECT}> {interaction.user.mention}: Select **members** below to **disconnect** from your channel",
                color=discord.Color.darker_grey()
            )
            disconnect_view = DisconnectView(voice_members)
            await interaction.response.send_message(embed=embed, view=disconnect_view, ephemeral=True)
        else:
            message = "Failed to **disconnect** members from the **voice channel**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=START, style=discord.ButtonStyle.gray, row=1)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        try:
            embed = discord.Embed(
                description=f"<{START}> {interaction.user.mention} Select an **activity** from the **dropdown** to start!",
                color=discord.Color.darker_grey()
            )
            activity_view = ActivityView()
            await interaction.response.send_message(embed=embed, view=activity_view, ephemeral=True)
        except Exception as e:
            log.error(f"Failed to start activity: {e}")
            message = "Failed to **start** the **activity**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=VIEW, style=discord.ButtonStyle.gray, row=1)
    async def view_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        embed = await helper_view_channel(interaction.guild, interaction.user)
        if embed is not None:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to view channel"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=INCREASE, style=discord.ButtonStyle.gray, row=1)
    async def increase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_increase_limit(interaction.guild, interaction.user)
        if val:
            message = f"Your **voice channel**'s limit changed to `{interaction.user.voice.channel.user_limit}`"
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif val is False:
            message = "**Channel limit** cannot be greater than `99`"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            message = "Failed to **increase** the **voice channel** limit"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=DECREASE, style=discord.ButtonStyle.gray, row=1)
    async def decrease_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await self.user_is_voice_member(interaction.user)
        # await self.user_is_voice_owner(interaction.user)
        val = await helper_decrease_limit(interaction.guild, interaction.user)
        if val:
            message = f"Your **voice channel**'s limit changed to `{interaction.user.voice.channel.user_limit}`"
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif val is False:
            message = "**Channel limit** cannot be less than `0`"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            message = "Failed to **decrease** the **voice channel** limit"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)