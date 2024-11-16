from typing import Any, Dict, List, Optional, Tuple
import discord
from discord.ext import commands
from discord.ui.item import Item
import requests
from bot import Sparky
import logging
import aiomysql
import json
from .db import *

from helpers import (
    Context, 
    Emojis,
    make_embed_info,
    make_embed_warning,
    make_embed_success,
    make_embed_lockdown,
    make_embed_visible,
    make_embed_progress
)

INTERFACE_EMOJIS = Emojis().get_emojis(
    'lock', 'unlock', 'ghost', 'unghost', 'microphone',
    'hammer', 'computer', 'info_1', 'plus', 'minus'
)

LOCK = Emojis().strip_emoji(INTERFACE_EMOJIS[0])
UNLOCK = Emojis().strip_emoji(INTERFACE_EMOJIS[1])
GHOST = Emojis().strip_emoji(INTERFACE_EMOJIS[2])
REVEAL = Emojis().strip_emoji(INTERFACE_EMOJIS[3])
CLAIM = Emojis().strip_emoji(INTERFACE_EMOJIS[4])
DISCONNECT = Emojis().strip_emoji(INTERFACE_EMOJIS[5])
START = Emojis().strip_emoji(INTERFACE_EMOJIS[6])
VIEW = Emojis().strip_emoji(INTERFACE_EMOJIS[7])
INCREASE = Emojis().strip_emoji(INTERFACE_EMOJIS[8])
DECREASE = Emojis().strip_emoji(INTERFACE_EMOJIS[9])

ACTIVITY_EMOJIS = Emojis().get_emojis(
    'youtube', 'gartic_phone', 'poker_night', 'putt_party', 'chess',
    'checkers', 'blazing_8s', 'bobble_league', 'sketch_heads', 'color_together',
    'land_io', 'know_what_i_meme', 'letter_league', 'spellcast', 'chef_showdown',
    'whiteboard'
)

CHECKED = Emojis().get_emoji('approve')
DENY = Emojis().get_emoji('deny')
VOICE = Emojis().get_emoji('voice')
ACTIVITIES = {
    "watch_together": {
        "activity_id": 880218394199220334,
        "activity_name": "Watch Together",
        "activity_emoji": ACTIVITY_EMOJIS[0]
    },
    "gartic_phone": {
        "activity_id": 1007373802981822582,
        "activity_name": "Gartic Phone",
        "activity_emoji": ACTIVITY_EMOJIS[1]
    },
    "poker_night": {
        "activity_id": 755827207812677713,
        "activity_name": "Poker Night",
        "activity_emoji": ACTIVITY_EMOJIS[2]
    },
    "putt_party": {
        "activity_id": 945737671223947305,
        "activity_name": "Putt Party",
        "activity_emoji": ACTIVITY_EMOJIS[3]
    },
    "chess_in_the_park": {
        "activity_id": 832012774040141894,
        "activity_name": "Chess in the Park",
        "activity_emoji": ACTIVITY_EMOJIS[4]
    },
    "checkers_in_the_park": {
        "activity_id": 832013003968348200,
        "activity_name": "Checkers in the Park",
        "activity_emoji": ACTIVITY_EMOJIS[5]
    },
    "blazing_8s": {
        "activity_id": 832025144389533716,
        "activity_name": "Blazing 8s",
        "activity_emoji": ACTIVITY_EMOJIS[6]
    },
    "bobble_league": {
        "activity_id": 947957217959759964,
        "activity_name": "Bobble League",
        "activity_emoji": ACTIVITY_EMOJIS[7]
    },
    "sketch_heads": {
        "activity_id": 902271654783242291,
        "activity_name": "Sketch Heads",
        "activity_emoji": ACTIVITY_EMOJIS[8]
    },
    "color_together": {
        "activity_id": 1039835161136746497,
        "activity_name": "Color Together",
        "activity_emoji": ACTIVITY_EMOJIS[9]
    },
    "land_io": {
        "activity_id": 903769130790969345,
        "activity_name": "Land-io",
        "activity_emoji": ACTIVITY_EMOJIS[10]
    },
    "know_what_i_meme": {
        "activity_id": 950505761862189096,
        "activity_name": "Know What I Meme",
        "activity_emoji": ACTIVITY_EMOJIS[11]
    },
    "letter_league": {
        "activity_id": 879863686565621790,
        "activity_name": "Letter League",
        "activity_emoji": ACTIVITY_EMOJIS[12]
    },
    "spellcast": {
        "activity_id": 852509694341283871,
        "activity_name": "SpellCast",
        "activity_emoji": ACTIVITY_EMOJIS[13]
    },
    "chef_showdown": {
        "activity_id": 1037680572660727838,
        "activity_name": "Chef Showdown",
        "activity_emoji": ACTIVITY_EMOJIS[14]
    },
    "whiteboard": {
        "activity_id": 1070087967294631976,
        "activity_name": "Whiteboard",
        "activity_emoji": ACTIVITY_EMOJIS[15]
    }
}

SUPPORT_SERVER = "https://discord.gg/8MTyyEUsJb"

logger = logging.getLogger(__name__)

class NotVoiceMember(commands.CheckFailure):
    pass

class NotVoiceOwner(commands.CheckFailure):
    pass

def is_voice_owner():
    async def predicate(ctx: Context):
        user = ctx.author
        voice_channels = ctx.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await ctx.bot.voicemaster_cog.get_custom_voice_channels(ctx.guild)
            except Exception as e:
                logger.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    for custom_channel in custom_channels:
                        if custom_channel['channel_id'] == voice_channel.id:
                            owner_id = custom_channel['owner_id']
                            if user.id == owner_id:
                                return True
        raise NotVoiceOwner("You don't own a **voice channel**!")
    return commands.check(predicate)

def is_voice_member():
    async def predicate(ctx: Context):
        user = ctx.author
        voice_channels = ctx.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await ctx.bot.voicemaster_cog.get_custom_voice_channels(ctx.guild)
            except Exception as e:
                logger.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    if user in voice_channel.members:
                        return True
        raise NotVoiceMember("You're not connected to a **voice channel**")
    return commands.check(predicate)

#######################################################################################################
#                                         HELPER FUNCTIONS                                            #
#######################################################################################################

async def helper_lock_channel(guild: discord.Guild, member: discord.Member) -> bool:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        overwrites = discord.PermissionOverwrite(connect=False)
        try:
            await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
            return True
        except Exception as e:
            logger.error(f"Failed to lock channel: {e}")
            return False
        
async def helper_unlock_channel(guild: discord.Guild, member: discord.Member) -> bool:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        overwrites = discord.PermissionOverwrite(connect=None)
        try:
            await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
            return True
        except Exception as e:
            logger.error(f"Failed to unlock channel: {e}")
            return False
        
async def helper_ghost_channel(guild: discord.Guild, member: discord.Member) -> bool:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        overwrites = discord.PermissionOverwrite(view_channel=False, connect=False)
        try:
            await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
            return True
        except Exception as e:
            logger.error(f"Failed to ghost channel: {e}")
            return False
        
async def helper_reveal_channel(guild: discord.Guild, member: discord.Member) -> bool:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        overwrites = discord.PermissionOverwrite(view_channel=None, connect=None)
        try:
            await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
            return True
        except Exception as e:
            logger.error(f"Failed to unghost channel: {e}")
            return False

        
async def helper_claim_channel(bot: Sparky, guild: discord.Guild, member: discord.Member) -> Optional[bool]:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            custom_channels = await bot.voicemaster_cog.get_custom_voice_channels(guild)
        except Exception as e:
            logger.error(f"Failed to get custom voice channels: {e}")
            return False
        for custom_channel in custom_channels:
            if custom_channel['channel_id'] == voice_channel.id:
                owner_id = custom_channel['owner_id']
                if owner_id == member.id:
                    return False  # user is already the owner
                if owner_id in [member.id for member in voice_channel.members]:
                    return None  # owner is still in the voice channel
                else:
                    await bot.voicemaster_cog.transfer_custom_voice_channel(voice_channel, member)
                    return True
    raise NotVoiceMember("You're not connected to a **voice channel**")

async def helper_disconnect_member(guild: discord.Guild, member: discord.Member) -> Optional[List[discord.Member]]:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            voice_members = voice_channel.members
            return voice_members
        except Exception as e:
            logger.error(f"Failed to disconnect member: {e}")
            return False
    raise NotVoiceMember("You're not connected to a **voice channel**")
        
async def helper_start_activity(guild: discord.Guild, member: discord.Member) -> bool:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            await voice_channel.send("Starting a game...")
            return True
        except Exception as e:
            logger.error(f"Failed to start activity: {e}")
            return False
    raise NotVoiceMember("You're not connected to a **voice channel**")
        
async def helper_view_channel(bot: Sparky, guild: discord.Guild, member: discord.Member) -> Optional[discord.Embed]:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            custom_channel = await bot.voicemaster_cog.get_custom_voice_channel(voice_channel)
            owner_id = custom_channel['owner_id']
            owner = guild.get_member(owner_id)
            connect_permission = voice_channel.overwrites.get(guild.default_role, discord.PermissionOverwrite()).connect
            visible_permission = voice_channel.overwrites.get(guild.default_role, discord.PermissionOverwrite()).view_channel
            locked_emoji = CHECKED if connect_permission in [False, None] else DENY
            ghosted_emoji = CHECKED if visible_permission is False else DENY
            embed = discord.Embed(
                title=f"{voice_channel.name}",
                color=discord.Color(0x747f8d),
                description=f"**Owner**: {owner.name} (`{owner.id}`)\n"
                            f"**Locked**: {locked_emoji}\n"
                            f"**Ghosted**: {ghosted_emoji}\n"
                            f"**Created**: {discord.utils.format_dt(voice_channel.created_at, 'R')}\n" 
                            f"**Bitrate**: {voice_channel.bitrate // 1000} kbps\n"
                            f"**Connected**: `{len(voice_channel.members)}`\n"
            )
            if member.avatar:
                avatar_url = member.avatar.url
            else:
                avatar_url = member.default_avatar.url
            embed.set_author(name=member.name, icon_url=avatar_url)
            return embed

        except Exception as e:
            logger.error(f"{type(e)} Failed to view channel: {e}")
            return None
    raise NotVoiceMember("You're not connected to a **voice channel**")
        
async def helper_increase_limit(guild: discord.Guild, member: discord.Member) -> Optional[bool]:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            await voice_channel.edit(user_limit=voice_channel.user_limit + 1)
            return True
        except discord.HTTPException as e:
            return False
        except Exception as e:
            logger.error(f"{type(e)} - Failed to increase limit: {e}")
            return None
    raise NotVoiceMember("You're not connected to a **voice channel**")
        
async def helper_decrease_limit(guild: discord.Guild, member: discord.Member) -> Optional[bool]:
    voice_channels = guild.voice_channels
    voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
    if voice_channel is not None:
        try:
            await voice_channel.edit(user_limit=voice_channel.user_limit - 1)
            return True
        except discord.HTTPException as e:
            return False
        except Exception as e:
            logger.error(f"{type(e)} - Failed to decrease limit: {e}")
            return None
    raise NotVoiceMember("You're not connected to a **voice channel**")

#######################################################################################################
#                                         VIEWS AND MENUS                                             #
#######################################################################################################

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
                logger.error(f"Failed to disconnect member: {e}")
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
            logger.exception(f"Failed to create activity options: {e}")

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
            logger.exception(f"Failed to start activity: {e}")
            await interaction.response.send_message("Failed to start the activity", ephemeral=True)

class ActivityView(discord.ui.View):
    def __init__(self):
        try:
            super().__init__(timeout=None)
            self.add_item(ActivitySelect())
        except Exception as e:
            logger.exception(f"Failed to create activity view: {e}")

class ActivityInviteButton(discord.ui.Button):
    def __init__(self, activity_url: str):
        super().__init__(style=discord.ButtonStyle.link, label="Start activity", url=activity_url)

class ActivityInviteView(discord.ui.View):
    def __init__(self, activity_url: str):
        try:
            super().__init__(timeout=None)
            self.add_item(ActivityInviteButton(activity_url))
        except Exception as e:
            logger.exception(f"Failed to create invite view: {e}")

class InterfaceView(discord.ui.View):
    def __init__(self, bot: Sparky):
        super().__init__(timeout=None)
        self.bot: Sparky = bot
        self.voicemaster: Voicemaster = self.bot.get_cog("Voicemaster")
    
    async def user_is_voice_member(self, user: discord.Member) -> bool:
        voice_channels = user.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await get_custom_voice_channels(user.guild)
            except Exception as e:
                logger.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    if user in voice_channel.members:
                        return True
        raise NotVoiceMember("You're not connected to a **voice channel**")
    
    async def user_is_voice_owner(self, user: discord.Member) -> bool:
        voice_channels = user.guild.voice_channels
        if voice_channels:
            try:
                custom_channels = await get_custom_voice_channels(user.guild)
            except Exception as e:
                logger.error(f"Failed to get custom voice channels: {e}")
                return False
            for voice_channel in voice_channels:
                if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
                    for custom_channel in custom_channels:
                        if custom_channel['channel_id'] == voice_channel.id:
                            owner_id = custom_channel['owner_id']
                            if user.id == owner_id:
                                return True
        raise NotVoiceOwner("You don't own a **voice channel**!")
    
    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception, item: Item[Any]) -> None:
        if isinstance(error, NotVoiceMember):
            embed = make_embed_warning(interaction.user, str(error))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif isinstance(error, NotVoiceOwner):
            embed = make_embed_warning(interaction.user, str(error))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @discord.ui.button(emoji=LOCK, style=discord.ButtonStyle.gray, row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        val = await helper_claim_channel(self.bot, interaction.guild, interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        try:
            embed = discord.Embed(
                description=f"<{START}> {interaction.user.mention} Select an **activity** from the **dropdown** to start!",
                color=discord.Color.darker_grey()
            )
            activity_view = ActivityView()
            await interaction.response.send_message(embed=embed, view=activity_view, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to start activity: {e}")
            message = "Failed to **start** the **activity**"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=VIEW, style=discord.ButtonStyle.gray, row=1)
    async def view_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user_is_voice_member(interaction.user)
        embed = await helper_view_channel(self.bot, interaction.guild, interaction.user)
        if embed is not None:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            message = "Failed to view channel"
            error_embed = make_embed_warning(interaction.user, message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @discord.ui.button(emoji=INCREASE, style=discord.ButtonStyle.gray, row=1)
    async def increase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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
        await self.user_is_voice_member(interaction.user)
        await self.user_is_voice_owner(interaction.user)
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

    
class Voicemaster(commands.Cog):
    """Voice controls for your server"""
    
    def __init__(self, bot):
        try:
            self.bot: Sparky = bot
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return VOICE

    #######################################################################################################
    #                                           LISTENER                                                  #
    #######################################################################################################

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # get the Join to Create channel
        try:
            voicemaster_channel_id = await get_voicemaster_setting(member.guild, "voice_channel_id")
        except Exception as e:
            logger.error(f"Failed to get voice channel id: {e}")
            return
        # create a new channel if the user joins the Join to Create channel
        if after.channel and after.channel.id == voicemaster_channel_id:
            try:
                # create a new voice channel with settings from the database
                try:
                    voice_settings = await get_voicemaster_settings(member.guild)
                except Exception as e:
                    logger.error(f"Failed to get voice settings: {e}")
                    return
                category_channel_ids = await get_category_channel_ids(member.guild)
                if category_channel_ids is not None:
                    custom_category_id = category_channel_ids[0]
                    default_category_id = category_channel_ids[1]
                    category_channel_id = custom_category_id if custom_category_id is not None else default_category_id
                else:
                    category_channel_id = None
                default_name = voice_settings[5]
                if "{user.name}" in default_name:
                    default_name = default_name.format(user=member)
                default_region = voice_settings[6]
                default_bitrate = voice_settings[7]
                category_channel = member.guild.get_channel(category_channel_id)
                overwrites = {
                    member: discord.PermissionOverwrite(connect=True, view_channel=True)
                }
                new_channel = await member.guild.create_voice_channel(
                    name=default_name,
                    category=category_channel,
                    user_limit=0,
                    bitrate=default_bitrate,
                    rtc_region=default_region,
                    reason="VoiceMaster channel creation",
                    overwrites=overwrites
                )

                # move the user to the new channel
                await member.move_to(new_channel)
                # create a database entry for the new channel
                await insert_custom_voice_channel(new_channel, member)
            except Exception as e:
                logger.error(f"Failed to create voice channel: {e}")

        # delete custom voice channels if they are empty
        try:
            custom_channels = await get_custom_voice_channels(member.guild)
        except Exception as e:
            logger.error(f"Failed to get custom voice channels: {e}")
            return
        # check if the current channel is a custom channel
        if before.channel and before.channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
            # check if the custom channel is empty
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="VoiceMaster channel deletion")
                    await delete_custom_voice_channel(before.channel)
                except Exception as e:
                    logger.error(f"Failed to delete voice channel: {e}")

        # check if a user joins a custom voice channel that has automatic roles enabled or if the server has an auto role set
        if after.channel and after.channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
            default_role_id = await get_voicemaster_setting(member.guild, "default_role_id")
            channel_role = await get_custom_voice_channel_role(channel=after.channel)
            role_id = channel_role.id if channel_role is not None else default_role_id
            if role_id is not None:
                role = member.guild.get_role(role_id)
                if role is not None:
                    try:
                        await member.add_roles(role, reason="VoiceMaster role assignment")
                    except Exception as e:
                        logger.error(f"Failed to assign role: {e}")

    #######################################################################################################
    #                                           COMMANDS                                                  #
    #######################################################################################################

    @commands.group(
        name="voicemaster",
        aliases=["voice", "vm", "vc"],
        usage="Syntax: voicemaster [subcommand] <args>\nExample: voicemaster setup",
        invoke_without_command=True
    )
    async def voicemaster(self, ctx: Context):
        """Make temporary voice channels in your server!"""
        await ctx.send_help(self.voicemaster)

    @voicemaster.command(
        name="status",
        usage="Syntax: voicemaster status [status]\nExample: voicemaster status just chilling",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_status(self, ctx: Context, *, status: Optional[str]):
        """Set a status for your voice channel"""
        if status is None:
            await ctx.send_help(self.voicemaster_status)
            return
        if len(status) > 500:
            status = status[:500]
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(status=status)
                await ctx.message.add_reaction("✅")
                return
            except Exception as e:
                logger.error(f"Failed to set status: {e}")
                await ctx.message.add_reaction("❌")
                return
        raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="category",
        aliases=["cat"],
        usage="Syntax: voicemaster category <category>\nExample: voicemaster category 1298214103587749888",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def voicemaster_category(self, ctx: Context, category: Optional[discord.CategoryChannel]):
        """Redirect voice channels to custom category"""
        if category is None:
            category_channel_ids = await get_category_channel_ids(ctx.guild)
            if category_channel_ids is not None:
                custom_id = category_channel_ids[0]
                if custom_id is None:
                    await ctx.send_help(self.voicemaster_category)
                    return
                val = await set_category_channel_id(ctx.guild, None)
                if val:
                    await ctx.success("Set **VoiceMaster** category back to **default**")
                else:
                    await ctx.warning("Failed to reset category channel")
                return
            else:
                await ctx.warning("Failed to change category channel")
                return
        val = await set_category_channel_id(ctx.guild, category.id)
        if val:
            await ctx.success(f"New **VoiceMaster** channels will be created under **{category.name}**")
        else:
            await ctx.warning("Failed to set category channel")

    @voicemaster.command(
        name="limit",
        usage="Syntax: voicemaster limit <limit>\nExample: voicemaster limit 5"
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_limit(self, ctx: Context, limit: Optional[int]):
        """Set a member limit for your voice channel"""
        if limit is None:
            await ctx.send_help(self.voicemaster_limit)
            return
        if limit < 0 or limit > 99:
            await ctx.warning("**Channel limit** must be between `0` and `99` members")
            return
        voice_channels = ctx.guild.voice_channels
        for voice_channel in voice_channels:
            if ctx.author in voice_channel.members:
                try:
                    await voice_channel.edit(user_limit=limit)
                    await ctx.success(f"Your **voice channel**'s limit has been updated to `{limit}`")
                except Exception as e:
                    logger.error(f"Failed to set limit: {e}")
                    await ctx.error("Failed to set limit for the **voice channel**")

    @voicemaster.command(
        name="ghost",
        aliases=["hide"],
        usage="Syntax: voicemaster ghost"
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_ghost(self, ctx: Context):
        """Hide your voice channel"""
        try:
            val = await helper_ghost_channel(ctx.guild, ctx.author)
            if val:
                message = "Your **voice channel** is now **ghosted**"
                embed = make_embed_visible(ctx.author, False, message)
                await ctx.send(embed)
            else:
                await ctx.warning("Failed to **hide** the **voice channel**")
        except Exception as e:
            logger.error(f"Failed to ghost channel: {e}")
            await ctx.error("Failed to **hide** the **voice channel**")

    @voicemaster.command(
        name="claim",
        usage="Syntax: voicemaster claim"
    )
    @is_voice_member()
    async def voicemaster_claim(self, ctx: Context):
        """Claim an inactive voice channel"""
        # check if an owner is already present in the channel
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                custom_channels = await get_custom_voice_channels(ctx.guild)
            except Exception as e:
                logger.error(f"Failed to get custom channels: {e}")
                await ctx.warning("Failed to **claim** the **voice channel**")
                return
            for custom_channel in custom_channels:
                if custom_channel['channel_id'] == voice_channel.id:
                    owner_id = custom_channel['owner_id']
                    if owner_id == ctx.author.id:
                        await ctx.warning("You already have **ownership** of this **voice channel**")
                        return
                    if owner_id in [member.id for member in voice_channel.members]:
                        await ctx.warning("You can't claim this **voice channel** - the owner is still active here")
                        return
                    try:
                        await transfer_custom_voice_channel(voice_channel, ctx.author)
                        await ctx.success("You have **claimed** this **voice channel**")
                    except Exception as e:
                        logger.error(f"Failed to claim channel: {e}")
                        await ctx.warning("Failed to **claim** the **voice channel**")
                    return
        raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="transfer",
        usage="Syntax: voicemaster transfer <user>\nExample: voicemaster transfer @Sparky",
    )
    @is_voice_owner()
    async def voicemaster_transfer(self, ctx: Context, user: Optional[discord.Member]):
        """Transfer ownership of your channel to another member"""        
        user_channel = await get_users_voice_channel(user)
        if user_channel is None:
            await ctx.warning(f"{user.mention} is not connected to a **voice channel**")
            return
        owner_channel = await get_users_voice_channel(ctx.author)
        if owner_channel is None:
            await ctx.warning("You're not connected to a **voice channel**")
            return
        if user_channel == owner_channel:
            try:
                if user.id == ctx.author.id:
                    await ctx.warning("You already own this **voice channel**!")
                    return
                if user.id not in [member.id for member in user_channel.members]:
                    await ctx.warning("You can't transfer **ownership** to a member who is not active in this **voice channel**")
                    return
                await transfer_custom_voice_channel(owner_channel, user)
                await ctx.success(f"**Ownership** of the voice channel has been transferred to {user.mention}")
            except Exception as e:
                logger.error(f"Failed to transfer ownership: {e}")
                await ctx.warning("Failed to transfer **ownership**")
        else:
            await ctx.warning("You can only **transfer ownership** to users in your **voice channel**")

    @voicemaster.command(
        name="unghost",
        aliases=["unhide"],
        usage="Syntax: voicemaster unghost"
    )
    @is_voice_owner()
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def voicemaster_unghost(self, ctx: Context):
        """Unhide your voice channel"""
        val = await helper_reveal_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **visible**"
            embed = make_embed_visible(ctx.author, True, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **reveal** the **voice channel**")

    @voicemaster.group(
        name="default",
        aliases=["def"],
        usage="Syntax: voicemaster default [subcommand] <args>\nExample: voicemaster default region us-west",
        extras={"permissions": ["Manage Guild & Roles"]},
        invoke_without_command=True
    )
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_default(self, ctx: Context):
        """Configure the default settings for VM channels"""
        await ctx.send_help(ctx.command)

    @voicemaster_default.command(
        name="role",
        usage="Syntax: voicemaster default role <role>\nExample: voicemaster default role @Member",
        extras={"permissions": ["Manage Guild & Roles"]}
    )
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_default_role(self, ctx: Context, role: Optional[discord.Role]):
        """Set default role for voice channels"""
        if role is None:
            await ctx.warning("I couldn't find the **default join role**, try setting it by providing a role")
            return
        val = await set_voicemaster_setting(ctx.guild, "default_role_id", role.id)
        if val:
            await ctx.success(f"Set {role.mention} as the **default role** for **VoiceMaster** channels")
        else:
            await ctx.warning("Failed to set **default role**")

    @voicemaster_default.command(
        name="name",
        usage="Syntax: voicemaster default name <name>\nExample: voicemaster default name {user.name}'s vc",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_name(self, ctx: Context, name: Optional[str]):
        """Set default name for new Voice Channels"""
        try:
            db_name = await get_voicemaster_setting(ctx.guild, "default_name")
        except Exception as e:
            logger.error(f"Failed to get default name: {e}")
            await ctx.error("Failed to get **default name**")
            return
        default_name = "{user.name}'s channel"
        if name is None and db_name == default_name:
            await ctx.send_help(self.voicemaster_default_name)
            return
        if name is None and db_name != default_name:
            await set_voicemaster_setting(ctx.guild, "default_name", "{user.name}'s channel")
            await ctx.success("Reset the **default name** for **VoiceMaster** channels")
            return
        await set_voicemaster_setting(ctx.guild, "default_name", name)
        await ctx.success(f"Set **default name** for **VoiceMaster** channels to `{name}`")

    @voicemaster_default.command(
        name="region",
        usage="Syntax: voicemaster default region [region]\nExample: voicemaster default region russia",
        extras={"permissions": ["Manage Guild"], "information": ["Use option 'regions' to see available regions"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_region(self, ctx: Context, region: Optional[str] = None):
        """Edit default region for new Voice Channels"""
        region = region.lower() if region is not None else None
        region_list = ["automatic", "brazil", "europe", "hongkong", "india", "japan", "russia", "singapore", "southafrica", "sydney", "us-central", "us-east", "us-south", "us-west"]
        if region == "regions":
            message = f"**Voice regions** are: `{', '.join(region_list)}`"
            info_embed = make_embed_info(ctx.author, message)
            await ctx.send(info_embed)
            return
        try:
            db_region = await get_voicemaster_setting(ctx.guild, "default_region")
        except Exception as e:
            logger.error(f"Failed to get default region: {e}")
            await ctx.error("Failed to get **default region**")
            return
    
        if db_region is False:
            await ctx.warning("Failed to get **default region**")
            return
        if region is None and db_region is None:
            await ctx.send_help(self.voicemaster_default_region)
            return
        if region is None and db_region is not None:
            await set_voicemaster_setting(ctx.guild, "default_region", None)
            await ctx.success("Updated **default region** to `automatic` for **VM channels**")
            return
        if region not in region_list:
            await ctx.warning(f"**Voice region** must be one of the following: `{', '.join(region_list)}`")
            return
        if region == "automatic":
            region = None
        region_name = region if region is not None else "automatic"
        await set_voicemaster_setting(ctx.guild, "default_region", region)
        await ctx.success(f"Updated **default region** to `{region_name}` for **VM channels**")

    @voicemaster_default.command(
        name="bitrate",
        usage="Syntax: voicemaster default bitrate <bitrate>\nExample: voicemaster default bitrate 80",
        extras={"permissions": ["Manage Guild"], "information": ["Bitrate must be between 8 and 96 kbps"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_bitrate(self, ctx: Context, bitrate: Optional[int]):
        """Set default bitrate for voice channels"""
        if bitrate < 8 or bitrate > 96:
            await ctx.warning("**Bitrate** must be between `8` and `96` kbps")
            return
        await set_voicemaster_setting(ctx.guild, "default_bitrate", bitrate)
        await ctx.success(f"Updated **default bitrate** to `{bitrate}` for **VM channels**")

    @voicemaster.command(
        name="setup",
        usage="Syntax: voicemaster setup",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_setup(self, ctx: Context):
        """Begin VoiceMaster server configuration setup"""
        try:
            is_setup = await get_voicemaster_setting(ctx.guild, "is_setup")
        except Exception as e:
            logger.error(f"Failed to get voicemaster settings: {e}")
            await ctx.warning(f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})")
            return
        if is_setup:
            message = "Server is already configured for **VoiceMaster**, run `voicemaster reset` to reset the **VoiceMaster** server configuration"
            warning_embed = make_embed_warning(ctx.author, message)
            await ctx.warning(f"Server is already configured for **VoiceMaster**, run `{ctx.prefix}voicemaster reset` to reset the **VoiceMaster** server configuration")
            return
        if is_setup is None:
            # Voicemaster configuration not found for this server
            in_database = False
        else:
            in_database = True
        message = "Starting VoiceMaster setup..."
        progress_embed = make_embed_progress(ctx.author, message)
        progress_message = await ctx.send(progress_embed)
        guild_channel_count = len(ctx.guild.channels)
        if guild_channel_count > 497:
            message = "VoiceMaster requires at least 3 free channels to setup. Please delete some channels and try again."
            warning_embed = make_embed_warning(ctx.author, message)
            await progress_message.edit(embed=warning_embed)
            return
        
        try:
            # Create category channel
            category_channel = await ctx.guild.create_category(name="Voice Channels", reason="VoiceMaster setup")
            # Create text channel with permissions
            text_overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False, 
                    send_messages_in_threads=False, 
                    create_public_threads=False, 
                    create_private_threads=False, 
                    add_reactions=False
                )
            }
            interface_channel = await ctx.guild.create_text_channel(
                name="interface", 
                category=category_channel, 
                reason="VoiceMaster setup", 
                overwrites=text_overwrites
            )
            logger.info(f"Created interface channel: {interface_channel}")
            await self.create_interface(interface_channel)
            # Create voice channel
            voice_overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False
                )
            }
            voice_channel = await ctx.guild.create_voice_channel(
                name="Join to Create", 
                category=category_channel, 
                reason="VoiceMaster setup", 
                overwrites=voice_overwrites
            )
            logger.info(f"Created voice channel: {voice_channel}")
            # put category channel, interface channel and voice channel ID's in database
            if in_database:
                await set_voicemaster_setting(ctx.guild, "is_setup", True)
            else:
                val = await initialize_voicemaster(ctx.guild)
                if val is False:
                    logger.error("Failed to initialize VoiceMaster")
                    message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
                    warning_embed = make_embed_warning(ctx.author, message)
                    await progress_message.edit(embed=warning_embed)
                    return
            val_category = await init_category_channel_ids(ctx.guild, category_channel.id)
            logger.info(f"val_category: {val_category}")
            val_interface = await set_voicemaster_setting(ctx.guild, "interface_channel_id", interface_channel.id)
            logger.info(f"val_interface: {val_interface}")
            val_voice = await set_voicemaster_setting(ctx.guild, "voice_channel_id", voice_channel.id)
            logger.info(f"val_voice: {val_voice}")
            if not val_category or not val_interface or not val_voice:
                logger.error("Failed to initialize VoiceMaster")
                message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
                warning_embed = make_embed_warning(ctx.author, message)
                await progress_message.edit(embed=warning_embed)
                return
        except Exception as e:
            message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
            warning_embed = make_embed_warning(ctx.author, message)
            await progress_message.edit(embed=warning_embed)
            return
        message = "Finished setting up the **VoiceMaster** channels. A category and two channels have been created, you can move the channels or rename them if you want."        
        embed = make_embed_success(ctx.author, message)
        await progress_message.edit(embed=embed)

    @voicemaster.command(
        name="configuration",
        aliases=["config", 'info'],
        usage="Syntax: voicemaster configuration",
    )
    @is_voice_member()
    async def voicemaster_configuration(self, ctx: Context):
        """Show Voicemaster configuration"""
        embed = await helper_view_channel(self.bot, ctx.guild, ctx.author)
        if embed:
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to view the **VoiceMaster** configuration")

    @voicemaster.command(
        name="reset",
        aliases=["resetserver"],
        usage="Syntax: voicemaster reset",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    # @commands.cooldown(1, 20, commands.BucketType.guild)
    async def voicemaster_reset(self, ctx: Context):
        """Reset server configuration for VoiceMaster"""
        logger.info(f"Resetting VoiceMaster for {ctx.guild}")
        
        category_channel_ids = await get_category_channel_ids(ctx.guild)
        if category_channel_ids is not None:
            logger.info(f"category_channel_ids: {category_channel_ids}")
            default_category_id = category_channel_ids[1]
            category_channel = ctx.guild.get_channel(default_category_id)
            try:
                await category_channel.delete(reason="VoiceMaster reset")
                logger.info("Deleted VoiceMaster category channel")
            except Exception as e:
                logger.error(f"Failed to delete category channel: {e}")
        else:
            logger.error("Failed to get category channel ID")
        try:
            interface_channel_id = await get_voicemaster_setting(ctx.guild, "interface_channel_id")
        except Exception as e:
            logger.error(f"Failed to get interface channel ID: {e}")
            return
        if interface_channel_id is not None:
            interface_channel = ctx.guild.get_channel(interface_channel_id)
            try:
                await interface_channel.delete(reason="VoiceMaster reset")
                logger.info("Deleted VoiceMaster interface channel")
            except Exception as e:
                logger.error(f"Failed to delete interface channel: {e}")
        else:
            logger.error("Failed to get interface channel ID")
        try:
            voice_channel_id = await get_voicemaster_setting(ctx.guild, "voice_channel_id")
        except Exception as e:
            logger.error(f"Failed to get voice channel ID: {e}")
            return
        if voice_channel_id is not None:
            voice_channel = ctx.guild.get_channel(voice_channel_id)
            try:
                await voice_channel.delete(reason="VoiceMaster reset")
                logger.info("Deleted VoiceMaster voice channel")
            except Exception as e:
                logger.error(f"Failed to delete voice channel: {e}")
        else:
            logger.error("Failed to get voice channel ID")
        logger.info("Deleted VoiceMaster channels")
        reset = await reset_voicemaster_settings(ctx.guild)
        if reset:
            logger.info("Reset VoiceMaster settings")
            await ctx.success("Reset the **VoiceMaster** configuration.")
        else:
            logger.info("Failed to reset VoiceMaster settings")
            await ctx.warning(f"**VoiceMaster** server configuration was not found. Run `{ctx.prefix}voicemaster setup` to configure **VoiceMaster**.")

    @voicemaster.command(
        name="lock",
        usage="Syntax: voicemaster lock",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_lock(self, ctx: Context):
        """Lock your voice channel"""
        val = await helper_lock_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **locked**"
            embed = make_embed_lockdown(ctx.author, True, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **lock** the **voice channel**")

    @voicemaster.command(
        name="unlock",
        usage="Syntax: voicemaster unlock",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_unlock(self, ctx: Context):
        """Unlock your voice channel"""
        val = await helper_unlock_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **unlocked**"
            embed = make_embed_lockdown(ctx.author, False, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **unlock** the **voice channel**")

    @voicemaster.command(
        name="role",
        aliases=["roles"],
        usage="Syntax: voicemaster role <role>\nExample: voicemaster role @Member",
        extras={"permissions": ["manage roles"]}
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def voicemaster_role(self, ctx: Context, role: Optional[discord.Role]):
        """Grant roles to members who join and remove from members leaving"""
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is None:
            raise NotVoiceMember("You're not connected to a **voice channel**")

        if role is None:
            db_role = await get_custom_voice_channel_role(voice_channel)
            if db_role is None:
                await ctx.send_help(self.voicemaster_role)
                return
            try:
                default_role_id = await get_voicemaster_setting(ctx.guild, "default_role_id")
            except Exception as e:
                logger.error(f"Failed to get default role: {e}")
                await ctx.warning("Failed to get **default role**")
                return
            if default_role_id is None:
                await ctx.warning("Failed to get **default role**")
                return
            val = await set_custom_voice_channel_role(voice_channel, default_role_id)
            if val:
                await ctx.success("Reset the **role** for the **voice channel**")
            else:
                await ctx.warning("Failed to reset the **role** for the **voice channel**")
            return
        
        if role >= ctx.guild.me.top_role:
            await ctx.warning(f"{role.mention} is **higher** than my highest role")
            return
        
        if role >= ctx.author.top_role:
            await ctx.warning(f"{role.mention} is **too high** for you to manage")
            return
        
        # assign role to all members in the channel and all the future members
        val = await set_custom_voice_channel_role(voice_channel, role.id)
        if val:
            logger.info(f"Set role for voice channel: {role}")
        else:
            logger.error("Failed to set role for voice channel")

        success = 0
        failed = 0
        for member in voice_channel.members:
            try:
                await member.add_roles(role, reason="VoiceMaster role assignment")
                success += 1
            except Exception as e:
                logger.error(f"Failed to assign role: {e}")
                failed += 1
        message = f"Succesfully assigned {role.mention} to `{success}` members"
        if failed > 0:
            message += f" (`{failed}` failed)"

        await ctx.success(message)

    @voicemaster.command(
        name="bitrate",
        usage="Syntax: voicemaster bitrate <bitrate>\nExample: voicemaster bitrate 64",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_bitrate(self, ctx: Context, bitrate: Optional[int]):
        """Set bitrate for voice channels"""        
        if bitrate < 8 or bitrate > 96:
            await ctx.warning("**Bitrate** must be between `8` and `96` kbps")
            return
        
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(bitrate=bitrate*1000)
                await ctx.success(f"Set **bitrate** for **voice channel** to `{bitrate}` kbps")
            except Exception as e:
                logger.error(f"Failed to set bitrate: {e}")
                await ctx.warning("Failed to set bitrate")

    @voicemaster.command(
        name="music",
        usage="Syntax: voicemaster music <on or off>\nExample: voicemaster music on",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_music(self, ctx: Context, *, option: Optional[str]):
        """Change your channel to a Music Only channel"""
        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.warning(f"Invalid **option**: `{option}`. Use `on` or `off`")
            return
        
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is None:
            raise NotVoiceMember("You're not connected to a **voice channel**")
        enabled_message = "Your **voice channel** is now a **music only channel**"
        disabled_message = "Your **voice channel** is no longer a **music only channel**"
        permission = False if option == "on" else None
        message = enabled_message if option == "on" else disabled_message
        music_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                speak=permission
            )
        }
        try:
            await voice_channel.edit(overwrites=music_overwrites)
        except Exception as e:
            logger.error(f"Failed to set music only channel: {e}")
            await ctx.error("Failed to set music only channel")
        else:
            await ctx.success(message)

    @voicemaster.command(
        name="name",
        usage="Syntax: voicemaster name <name>\nExample: voicemaster name Jedi meeting room",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def voicemaster_name(self, ctx: Context, *, name: Optional[str]):
        """Set name for voice channels"""
        # get default name from database
        try:
            db_name = await get_voicemaster_setting(ctx.guild, "default_name")
        except Exception as e:
            logger.error(f"Failed to get default name: {e}")
            return
        # if name is None and db_name is None, display help
        # if name is None and db_name is not None, set name to db_name
        # if name is not None, set name to name
        if name is None and db_name is None:
            await ctx.send_help(self.voicemaster_name)
            return
        if name is None and db_name is not None:
            name = db_name
            message = f"Successfully reset **name** for **voice channel** to `{name}`"
        if name is not None:
            message = f"Set **name** for **voice channel** to `{name}`"

        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(name=name)
                await ctx.success(message)
            except Exception as e:
                logger.error(f"Failed to set name: {e}")
                await ctx.warning("Failed to set name")

    @voicemaster.command(
        name="permit",
        usage="Syntax: voicemaster permit <user>\nExample: voicemaster permit @Sparky",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_permit(self, ctx: Context, user: Optional[discord.Member]):
        """Permit a user to join your voice channel"""
        overwrites = discord.PermissionOverwrite(connect=True, view_channel=True)
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.set_permissions(user, overwrite=overwrites)
                await ctx.success(f"Permitted {user.mention} to **join** the **voice channel**")
            except Exception as e:
                logger.error(f"Failed to permit user: {e}")
                await ctx.warning("Failed to permit user")
        else:
            raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="reject",
        usage="Syntax: voicemaster reject <user>\nExample: voicemaster reject @Sparky",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_reject(self, ctx: Context, user: Optional[discord.Member]):
        """Reject a user from joining your voice channel"""
        overwrites = discord.PermissionOverwrite(connect=False, view_channel=False)
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            if user.id == ctx.author.id:
                await ctx.warning("You can't reject yourself from joining the **voice channel**")
                return
            if user.id in [member.id for member in voice_channel.members]:
                try:
                    # disconnect user from voice channel
                    await user.move_to(None)
                except Exception as e:
                    logger.error(f"Failed to disconnect user: {e}")
                    await ctx.warning(f"Failed to disconnect user {user.mention}")
                    return
            try:
                await voice_channel.set_permissions(user, overwrite=overwrites)
                await ctx.success(f"Rejected {user.mention} from **joining** the **voice channel**")
            except Exception as e:
                logger.error(f"Failed to reject user: {e}")
                await ctx.error("Failed to reject user")
        else:
            raise NotVoiceMember("You're not connected to a **voice channel**")

    #######################################################################################################
    #                                          INTERFACE                                                  #
    #######################################################################################################

    async def create_interface(self, interface_channel: discord.TextChannel):
        """Create the interface for the voice channel"""
        try:
            embed = discord.Embed(
                title="VoiceMaster Interface",
                description="Click the buttons below to control your voice channel",
                color=discord.Color(0x69919d),
                type='rich'
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            invite_link = "https://discord.gg/8MTyyEUsJb"
            embed.add_field(
                name='**Button Usage**',
                value=
                    f"<{LOCK}> — [`Lock`]({invite_link}) the voice channel\n"
                    f"<{UNLOCK}> — [`Unlock`]({invite_link}) the voice channel\n"
                    f"<{GHOST}> — [`Ghost`]({invite_link}) the voice channel\n"
                    f"<{REVEAL}> — [`Reveal`]({invite_link}) the voice channel\n"
                    f"<{CLAIM}> — [`Claim`]({invite_link}) the voice channel\n"
                    f"<{DISCONNECT}> — [`Disconnect`]({invite_link}) a member\n"
                    f"<{START}> — [`Start`]({invite_link}) an activity\n"
                    f"<{VIEW}> — [`View`]({invite_link}) channel information\n"
                    f"<{INCREASE}> — [`Increase`]({invite_link}) the user limit\n"
                    f"<{DECREASE}> — [`Decrease`]({invite_link}) the user limit",
                inline=True
            )
            if interface_channel.guild.icon:
                icon_url = interface_channel.guild.icon.url
            else:
                icon_url = None
            embed.set_author(name=interface_channel.guild.name, icon_url=icon_url)
            interface_view = InterfaceView(self.bot)
            await interface_channel.send(embed=embed, view=interface_view)
        except Exception as e:
            logger.error(f"Failed to create interface: {e}")
            await interface_channel.send("Failed to create interface")
