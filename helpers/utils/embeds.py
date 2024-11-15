from typing import List
import pytz
from datetime import datetime, timezone
from discord import (
    Member, 
    Embed,
    Guild, 
    utils,
    Color
)
from .text import (
    format_timedelta,
    extract_extension
)
from .emojis import Emojis

try:
    EMBED_EMOJIS = Emojis().get_emojis(
        'warning', 'cooldown', 'deny', 'add', 'info', 
        'remove', 'approve', 'loading', 'unghost', 'ghost',
        'clock', 'sleep', 'wave', 'mag_right', 'lock_1', 'unlock_1'
    )
except ValueError:
    EMBED_EMOJIS = None

if EMBED_EMOJIS is not None:
    (
        WARNING, 
        COOLDOWN, 
        DENY, 
        ADD, 
        INFO, 
        REMOVE, 
        APPROVE, 
        LOADING, 
        UNGHOST, 
        GHOST, 
        CLOCK,
        SLEEP,
        WAVE,
        MAG_RIGHT,
        LOCK_1,
        UNLOCK_1
    ) = EMBED_EMOJIS

__all__ = (
    'make_embed_mute',
    'make_embed_warning',
    'make_embed_cooldown',
    'make_embed_error',
    'make_embed_add',
    'make_embed_info',
    'make_embed_progress',
    'make_embed_remove',
    'make_embed_success',
    'make_embed_sleep',
    'make_embed_wakeup',
    'make_embed_snipe',
    'make_embed_snipe_reaction',
    'make_embed_snipe_not_found',
    'make_embed_loading',
    'make_embed_index_not_found',
    'make_embed_warn',
    'make_embed_lockdown',
    'make_embed_visible'
)

def make_embed_mute(author: Member, mute_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color(0xff0000),
        description = f"{lrm}{author.mention}: {mute_message}"
    )
    return embed

def make_embed_warning(author: Member, warning_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.orange(),
        description = f"{lrm}{WARNING} {author.mention}: {warning_message}"
    )
    return embed

def make_embed_cooldown(self, author: Member, cooldown_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color(0x50c7ef),
        description = f"{lrm}{COOLDOWN} {author.mention}: {cooldown_message}"
    )
    return embed

def make_embed_error(author: Member, error_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.red(),
        description = f"{lrm}{DENY} {author.mention}: {error_message}"
    )
    return embed

def make_embed_add(self, author: Member, add_message) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.blue(),
        description = f"{lrm}{ADD} {author.mention}: {add_message}"
    )
    return embed

def make_embed_info(author: Member, info_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.from_rgb(109, 161, 203),
        description = f"{lrm}{INFO} {author.mention}: {info_message}"
    )
    return embed

def make_embed_progress(author: Member, progress_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.from_rgb(109, 161, 203),
        description = f"{lrm}{author.mention}: {progress_message}"
    )
    return embed

def make_embed_remove(self, author: Member, remove_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.blue(),
        description = f"{lrm}{REMOVE} {author.mention}: {remove_message}"
    )
    return embed

def make_embed_success(author: Member, success_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color(0x747f8d),
        description = f"{lrm}{APPROVE} {author.mention}: {success_message}"
    )
    return embed

def make_embed_sleep(mentioned_user: Member, afk_message: str, afk_timestamp: datetime) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color = Color.dark_gray(),
        description = f"{lrm}{SLEEP} {mentioned_user.mention} is AFK: **{afk_message}** - {utils.format_dt(afk_timestamp, 'R')}"
    )
    return embed 

def make_embed_wakeup(member: Member, afk_timestamp: datetime) -> Embed:
    lrm = "\u200E"
    time_elapsed = datetime.now(timezone.utc) - afk_timestamp
    time_str = format_timedelta(time_elapsed)
    embed = Embed(
        color = Color.dark_gray(),
        description = f"{lrm}{WAVE} {member.mention}: Welcome back, you were away for {time_str}."
    )
    return embed 

def make_embed_snipe(
    author: Member, 
    message_content: str, 
    message_attachments: List[dict], 
    message_author: Member, 
    deleted_timestamp: datetime, 
    snipe_number: int, 
    total_messages: int, 
    flag: int
) -> Embed:
    # flags can be 1, 2 and 3 (deleted, edited and reaction)
    # Calculate the time elapsed since the message was deleted/edited
    pytz.timezone('UTC').localize(deleted_timestamp)
    time_elapsed = datetime.now() - deleted_timestamp
    time_str = format_timedelta(time_elapsed)

    embed = Embed(
        color=Color.dark_gray(),
        description=f"{message_content}" if message_content else None
    )
    if message_attachments is not None:
        if len(message_attachments) == 1 and message_attachments[0]['url'].endswith('.webp?size=1024'):
            embed.set_image(url=message_attachments[0]['url'])
            message_attachments.pop(0)

        for i in range(len(message_attachments)):
            attachment_url = message_attachments[i]['url']
            extension = extract_extension(attachment_url)
            if extension in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                embed.set_image(url=attachment_url)
                message_attachments.pop(i)
                break

    embed.set_author(name=message_author.name, icon_url=message_author.display_avatar.url)
    if flag == 1:
        embed.set_footer(text=f"Deleted {time_str} ago • {snipe_number}/{total_messages} messages", icon_url=author.avatar.url)
    elif flag == 2:
        embed.set_footer(text=f"Edited {time_str} ago • {snipe_number}/{total_messages} edits", icon_url=author.avatar.url)
    return embed, message_attachments

def make_embed_snipe_reaction(
    reaction_name: str, 
    reaction_author: Member, 
    removed_timestamp: datetime
) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color=0x7289da,
        description=f"{lrm}**{reaction_author}** reacted with {reaction_name} <t:{int(removed_timestamp.replace(tzinfo=pytz.timezone('UTC')).timestamp())}:R>"
    )
    return embed

def make_embed_snipe_not_found(author: Member, snipe_type: int) -> Embed:
    lrm = "\u200E"
    snipe_messages = {
        1: "No **deleted messages** found",
        2: "No **edited messages** found",
        3: "No **removed reaction** found"
    }
    snipe_message = snipe_messages[snipe_type] if snipe_type in range(1, 4) else "No **deleted messages** found"
    embed = Embed(
        color=Color(0x7289da),
        description=f"{lrm}{MAG_RIGHT} {author.mention}: {snipe_message}"
    )
    return embed

def make_embed_loading(author: Member, loading_message: str) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color=Color(0x7289da),
        description=f"{lrm}{LOADING} {author.mention}: {loading_message}"
    )
    return embed

def make_embed_index_not_found(author: Member, index) -> Embed:
    lrm = "\u200E"
    embed = Embed(
        color=Color(0x7289da),
        description=f"{lrm}{MAG_RIGHT} {author.mention}: No **snipe** found for `Index {index}`"
    )
    return embed

def make_embed_warn(guild: Guild, moderator: Member, reason: str) -> Embed:
    embed = Embed(
        title="Warned",
        color=Color.yellow(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="You have been warned in", value=guild.name, inline=True)
    embed.add_field(name="Moderator", value=moderator.name, inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed

def make_embed_lockdown(author: Member, locked: bool, message: str) -> Embed:
    lrm = "\u200E"
    emoji = LOCK_1 if locked else UNLOCK_1
    embed = Embed(
        color=Color.orange(),
        description=f"{lrm}{emoji} {author.mention}: {message}"
    )
    return embed

def make_embed_visible(author: Member, visible: bool, message: str) -> Embed:
    lrm = "\u200E"
    emoji = GHOST if visible else UNGHOST
    embed = Embed(
        color=Color(0x69919d),
        description=f"{lrm}{emoji} {author.mention}: {message}"
    )
    return embed