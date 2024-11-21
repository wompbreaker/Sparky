from __future__ import annotations
import re
import logging
from typing import List, Tuple
from discord.ext.commands import (
    ExtensionError,
    ExtensionAlreadyLoaded,
    ExtensionNotLoaded,
    NoEntryPointError,
    ExtensionFailed,
    ExtensionNotFound,
    BadArgument,
    MessageNotFound,
    MemberNotFound,
    GuildNotFound,
    UserNotFound,
    ChannelNotFound,
    ChannelNotReadable,
    BadColourArgument,
    RoleNotFound,
    BadInviteArgument,
    EmojiNotFound,
    GuildStickerNotFound,
    BadBoolArgument,
    ThreadNotFound,
    FlagError,	
    BadUnionArgument,
    BadLiteralArgument,
    ArgumentParsingError,
    UnexpectedQuoteError,
    InvalidEndOfQuotedStringError,
    ExpectedClosingQuoteError,
    CheckFailure,
    BotMissingPermissions,
    MissingPermissions,
    NotOwner,
    PrivateMessageOnly,
    NoPrivateMessage,
    DisabledCommand,
    CommandOnCooldown
)
# from cogs.voice.voice import NotVoiceMember, NotVoiceOwner
from .managers.context import Context
from .utils.embeds import make_embed_cooldown

log = logging.getLogger(__name__)

__all__ = (
    'handle_extension_error',
    'handle_bad_argument',
    'handle_bad_union_argument',
    'handle_bad_literal_argument',
    'handle_check_failure',
    'handle_disabled_command',
    'handle_argument_parsing_error',
    'handle_command_on_cooldown'
)

async def handle_extension_error(ctx: Context, error: ExtensionError) -> None:
    if isinstance(error, ExtensionAlreadyLoaded):
        message = f"Extension [{error.name}] is already loaded."
    if isinstance(error, ExtensionNotLoaded):
        message = f"Extension [{error.name}] is not loaded."
    if isinstance(error, NoEntryPointError):
        message = f"Extension [{error.name}] doesn't have a `setup` entry point function."
    if isinstance(error, ExtensionFailed):
        message = f"Extension [{error.name}] failed to load: {error.original}"
    if isinstance(error, ExtensionNotFound):
        message = f"Extension [{error.name}] not found."
    
    log.error(f"[ExtensionError]: {message}")
    await ctx.error(message)

async def handle_bad_argument(ctx: Context, error: BadArgument) -> None:
    if isinstance(error, MessageNotFound):
        message = "Invalid **message link** provided."
    elif isinstance(error, MemberNotFound):
        message = f"I was unable to find a member with the name: **{ctx.current_argument}**."
    elif isinstance(error, GuildNotFound):
        message = f"I was unable to find a guild with the name: **{ctx.current_argument}**."
    elif isinstance(error, UserNotFound):
        message = f"I was unable to find a user with the name: **{ctx.current_argument}**."
    elif isinstance(error, ChannelNotFound):
        message = "Could not convert **channel** into `Text Channel, Voice Channel, or Category Channel`."
    elif isinstance(error, ChannelNotReadable):
        message = "Could not **read messages** from the specified **channel**."
    elif isinstance(error, BadColourArgument):
        message = f"Color **{ctx.current_argument}** is not valid."
    elif isinstance(error, RoleNotFound):
        message = f"I was unable to find a role with the name: **{ctx.current_argument}**."
    elif isinstance(error, BadInviteArgument):
        message = f"{ctx.current_argument} is either an **invalid** or an **expired** invite."
    elif isinstance(error, EmojiNotFound):
        message = f"I was unable to find an emoji with the name: **{ctx.current_argument}**."
    elif isinstance(error, GuildStickerNotFound):
        message = f"I was unable to find a sticker with the name: **{ctx.current_argument}**."
    elif isinstance(error, BadBoolArgument):
        message = f"Boolean argument **{ctx.current_argument}** isn't convertible."
    elif isinstance(error, ThreadNotFound):
        message = f"I was unable to find a thread with the name: **{ctx.current_argument}**."
    elif isinstance(error, FlagError):
        message = str(error)
    else:
        message = str(error).replace('"', '**')

    log.error(f"[BadArgument]: {message}")
    await ctx.error(message)

async def handle_bad_union_argument(ctx: Context, error: BadUnionArgument) -> None:
    def camel_case_split(identifier: str) -> str:
        return ' '.join([word for word in re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', identifier)])
    
    def list_converters(converters: List[Tuple[type, ...]]) -> str:
        # separate converters with commas and add 'or' before the last converter
        converters: str = ', '.join([f"{camel_case_split(converter.__qualname__)}" for converter in converters])
        if len(converters) > 1:
            converters = converters.rsplit(', ', 1)
            converters = ' or '.join(converters)
        return converters
    
    param = error.param
    converters = error.converters
    message = f"Could not convert **{param.name.replace('_', ' ')}** into `{list_converters(converters)}`"

    log.error(f"[BadUnionArgument]: {message}")
    await ctx.warning(message)

async def handle_bad_literal_argument(ctx: Context, error: BadLiteralArgument) -> None:
    literals = ', '.join([f"`{literal}`" for literal in error.literals])
    if len(error.literals) > 1:
        literals = literals.rsplit(', ', 1)
        literals = ' or '.join(literals)
    message = f"**Option** must be one of the following: {literals}."
    await ctx.warning(message)

async def handle_argument_parsing_error(ctx: Context, error: ArgumentParsingError) -> None:
    if isinstance(error, UnexpectedQuoteError):
        message = f"Unexpected quote found: {error.quote}"
    elif isinstance(error, InvalidEndOfQuotedStringError):
        message = f"Invalid end of quoted string found: {error.char}"
    elif isinstance(error, ExpectedClosingQuoteError):
        message = f"Expected closing quote not found: {error.close_quote}"
    
    log.error(f"[ArgumentParsingError]: {message}")
    await ctx.warning(message)

async def handle_check_failure(ctx: Context, error: CheckFailure):
    if isinstance(error, BotMissingPermissions):
        permission_list = f""
        for perm in error.missing_permissions:
            perm: str = perm.replace('_', ' ')
            permission_list += f"`{perm}`, "
        permission_list = permission_list[:-2]
        message = f"I don't have the {permission_list} permissions."
        if len(error.missing_permissions) == 1:
            message = message[:-2] + "."
    elif isinstance(error, MissingPermissions):
        permission_list = f""
        for perm in error.missing_permissions:
            perm: str = perm.replace('_', ' ')
            permission_list += f"`{perm}`, "
        permission_list = permission_list[:-2]
        message = f"You don't have the {permission_list} permissions."
        if len(error.missing_permissions) == 1:
            message = message[:-2] + "."
    elif isinstance(error, PrivateMessageOnly):
        message = "This command can only be used in **private messages**."
    elif isinstance(error, NoPrivateMessage):
        message = "This command cannot be used in **private messages**."
    elif isinstance(error, NotOwner):
        message = "You must be the **bot owner** to run this command."
    else:
        from cogs.voice.voice import NotVoiceMember, NotVoiceOwner
        from cogs.logs.logs import LoggingNotInitialized, LoggingAlreadyInitialized
        if isinstance(error, NotVoiceMember):
            message = str(error)
        elif isinstance(error, NotVoiceOwner):
            message = str(error)
        elif isinstance(error, LoggingNotInitialized):
            message = str(error)
        elif isinstance(error, LoggingAlreadyInitialized):
            message = str(error)

    log.error(f"[CheckFailure]: {message}")
    await ctx.warning(message)

async def handle_disabled_command(ctx: Context, error: DisabledCommand) -> None:
    message = "This command is **disabled**."
    log.error(f"[DisabledCommand]: {message}")
    await ctx.warning(message)

async def handle_command_on_cooldown(ctx: Context, error: CommandOnCooldown) -> None:
    message = f"Please wait **{error.retry_after:.2f} seconds** before using this command again."
    embed = make_embed_cooldown(ctx.author, message)
    log.error(f"[CommandOnCooldown]: {message}")
    await ctx.send(embed)