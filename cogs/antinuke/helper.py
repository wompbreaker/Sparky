from logging import getLogger
from typing import List, Optional, Literal

from discord import (
    Member,
    Guild,
    Embed,
    Role,
    User,
    Color,
    Forbidden,
    NotFound,
    utils
)

from .db import is_whitelisted

log = getLogger(__name__)

def get_punishment(value: int) -> Optional[Literal['stripstaff', 'kick', 'ban']]:
    """Get the punishment name from the value
    
    Parameters:
    -----------
    
    value: int
        The value of the punishment
        
    Returns:
    --------
    Optional[Literal['stripstaff', 'kick', 'ban']]
        The punishment name
    """
    value = int(value)
    try:
        punishments = {
            0: "stripstaff",
            1: "kick",
            2: "ban"
        }
        return punishments[value]
    except Exception as e:
        log.error(f"{type(e)} error in get_punishment: {e}")


def get_user_id_from_reason(reason: str) -> int:
    """Get the user id from the reason string. Used to check if the mod is abusing bot commands
    
    Parameters:
    -----------
    reason: str
        The reason string from the moderation action
        
    Returns:
    --------
    int
        The user id of the user who was moderated
    """
    i = 0
    user_id = ""
    while len(reason) > 0:
        if reason[i] != "(":
            i += 1
        else:
            i += 1
            while reason[i] != ")":
                user_id += reason[i]
                i += 1
            return int(user_id)
        
@staticmethod
def make_embed_vanity_alert(
    member: Member, 
    guild: Guild, 
    vanity_before: str, 
    vanity_after: str
) -> Embed:
    embed = Embed(
        color=Color.red(),
        description=f"Your server's vanity URL was changed in **{guild.name}**\n"
                    f"**{member}** changed `{vanity_before}` to `{vanity_after}`"
    )
    embed.set_footer(text="Note that bots do not have the ability to change vanities!")
    return embed

async def make_embed_antinuke_admins(author: Member, admins: List[str]) -> Embed:
    admins_str = f""
    count = 0
    if len(admins) == 0:
        admins_str += "No antinuke admins."
    else:
        for admin in admins:
            count += 1
            user: User = await utils.get(author.guild.members, id=int(admin))
            admins_str += f"`{count}` {user.mention}\n"
    embed = Embed(
        description=admins_str,
        color=0x000001,
        title="Antinuke admins"
    )
    embed.set_author(name=author, icon_url=author.display_avatar.url)
    return embed 

async def punish_moderator(member: Member, punishment: int, reason: str):
    punishment = get_punishment(int(punishment))
    whitelisted = await is_whitelisted(member.guild, member)
    if whitelisted or member == member.guild.me or member == member.guild.owner:
        return
    if punishment == "kick":
        try:
            await member.kick(reason=f"Kicked for {reason}")
        except Exception as e:
            log.error(f"{type(e)} error in punish_moderator kick: {e}")
    if punishment == "ban":
        try:
            await member.ban(reason=f"Banned for {reason}")
        except Exception as e:
            log.error(f"{type(e)} error in punish_moderator ban: {e}")
    if punishment == "stripstaff":
        await strip_staff(member)

async def strip_staff(member: Member | User):
    # check if a role in member's roles has any of the following perms:
    def check_role_perms(role: Role) -> bool:
        perm_list = [
            'administrator', 'ban_members', 'deafen_members', 'kick_members', 'manage_channels',
            'manage_emojis', 'manage_emojis_and_stickers', 'manage_events', 'manage_expressions',
            'manage_guild', 'manage_messages', 'manage_nicknames', 'manage_permissions',
            'manage_roles', 'manage_threads', 'manage_webhooks', 'mention_everyone',
            'moderate_members', 'move_members', 'mute_members', 'view_audit_log', 'create_expressions'
        ]
        for perm, value in role.permissions:
            if value:  # Check if permission is enabled
                if perm in perm_list:
                    return True
        return False

    if member:
        removed_roles = []
        roles_fail_bot = []
        for role in member.roles:
            if check_role_perms(role) and role.name != "@everyone":
                if role >= member.guild.me.top_role or role.is_bot_managed():
                    roles_fail_bot.append(role)
                    continue

                try:
                    await member.remove_roles(role)
                    removed_roles.append(role)
                except (Forbidden, NotFound):
                    continue
