import json
from typing import Literal, Union
from logging import getLogger

import discord
from discord.ext import commands
from discord import (
    Member, 
    TextChannel, 
    StageChannel, 
    CategoryChannel, 
    Thread, 
    VoiceChannel
)

from bot import Sparky
from helpers import Context, Emojis
from .decorators import *
from .db import *

log = getLogger(__name__)

class Logs(commands.Cog):
    """Logging commands for your server"""

    def __init__(self, bot):
        self.bot: Sparky = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return Emojis().get_emoji('scroll')
    
###############################################################################
#                               LISTENERS                                     #
###############################################################################
        
###############################################################################
#                                COMMANDS                                     #
###############################################################################

    @commands.group(
        name='log',
        aliases=['logging', 'log', 'logs'],
        usage="Syntax: log [subcommand] <args>\nExample: log add #logs messages",
        extras={'permissions': ['manage guild']},
        invoke_without_command=True
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def log(self, ctx: Context):
        """Set up logging for your community"""
        await ctx.send_help(ctx.command)

    @log.command(
        name='setup',
        alises=['init'],
        usage='Syntax: log setup',
        extras={'permissions': ['manage guild']}
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @logging_not_initialized()
    async def setup(self, ctx: Context):
        """Initialize logging for your community"""
        try:
            val = await setup_logging(ctx.guild.id)
            if val:
                await ctx.success("Logging has been **initialized**.")
            else:
                await ctx.warning("Failed to initialize logging.")
        except Exception as e:
            await ctx.error(f"Failed to initialize logging: {e}")		

    @log.command(
        name='reset',
        usage='Syntax: log reset',
        extras={'permissions': ['manage guild']}
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @logging_initialized()
    async def reset(self, ctx: Context):
        """Reset logging for your community"""
        try:
            val = await reset_logging(ctx.guild.id)
            if val:
                await ctx.success("Logging has been **reset**.")
            else:
                await ctx.warning("Failed to reset logging.")
        except Exception as e:
            await ctx.warning(f"Failed to reset logging: {e}")

    @log.command(
        name='add',
        usage=(
            "Syntax: log add <channel> [event]\n"
            "Example: log add #logs messages"
        ),
        extras={
            'permissions': ['manage guild'], 
            'information': [
                "Events: messages, members, roles, \nchannels, invites, emojis and voice"
            ]
        }
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @logging_initialized()
    async def add(
        self, 
        ctx: Context, 
        channel: Union[TextChannel, Thread], 
        option: Literal[
            'messages', 'members', 'roles', 'channels', 'invites', 'emojis', 'voice'
        ] = None
    ):
        """Set up logging in a channel"""
        option = option.lower() if option else 'all'
        try:
            val = await set_event_channel(ctx.guild.id, channel.id, option)
            if val:
                if option == 'all':
                    message = f"All events will be **logged** in {channel.mention}"
                else:
                    message = f"Event `{option}` will be **logged** in {channel.mention}"
                await ctx.success(message)
            else:
                await ctx.warning(
                    f"Channel {channel.mention} is already being logged for {option}."
                )
        except Exception as e:
            await ctx.error(f"Failed to add channel for logging: {e}")
        

    @log.command(
        name='ignore',
        usage="Syntax: log ignore <channel>\nExample: log ignore #logs",
        extras={'permissions': ['manage guild'], 'parameters': ['member or channel']}
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @logging_initialized()
    async def ignore(
        self, 
        ctx: Context, 
        member_or_channel: Union[
            Member, TextChannel, StageChannel, CategoryChannel, Thread, VoiceChannel
        ]
    ):
        """Ignore a member or channel from being logged"""
        try:
            if isinstance(member_or_channel, TextChannel) \
                or isinstance(member_or_channel, StageChannel) \
                or isinstance(member_or_channel, CategoryChannel) \
                or isinstance(member_or_channel, Thread) \
                or isinstance(member_or_channel, VoiceChannel):
                ignored_channels = await get_ignored_channels(ctx.guild)
                if member_or_channel in ignored_channels:
                    await ctx.warning("Channel is already being ignored.")
                else:
                    ignored_channels.append(member_or_channel)
                    await set_log_property(
                        ctx.guild.id, 
                        'ignored_channels', 
                        json.dumps([channel.id for channel in ignored_channels])
                    )
                    await ctx.success(f"Channel {member_or_channel.mention} has been ignored.")
            elif isinstance(member_or_channel, Member):
                ignored_members = await get_ignored_members(ctx.guild)
                if member_or_channel in ignored_members:
                    await ctx.warning("Member is already being ignored.")
                else:
                    ignored_members.append(member_or_channel)
                    await set_log_property(
                        ctx.guild.id,
                        'ignored_members', 
                        json.dumps([member.id for member in ignored_members])
                    )
                    await ctx.success(f"Member {member_or_channel.mention} has been ignored.")
        except Exception as e:
            await ctx.error(f"Failed to ignore member or channel: {e}")
