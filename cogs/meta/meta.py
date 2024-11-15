# This file includes parts of code from https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/meta.py
# Original code by [Rapptz]
# Modifications by [wompbreaker]
# This file is licensed under the Mozilla Public License 2.0
# See the LICENSE file for more details

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from discord.ext import commands
import discord
import unicodedata
from helpers import (
    Context,
    Emojis,
    make_embed_info
)
from .views import InviteView, PaginatedHelpCommand

if TYPE_CHECKING:
    from bot import Sparky
import logging

# Configure logging
logger = logging.getLogger(__name__)

WARNING = Emojis().get_emoji('warning')
COOLDOWN = Emojis().get_emoji('cooldown')
CANCEL = Emojis().get_stripped_emoji('cancel')
VOICE = Emojis().get_emoji('voice')

class Meta(commands.Cog):
    """Commands for utilities related to Discord or the Bot itself."""

    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            self.old_help_command: Optional[commands.HelpCommand] = bot.help_command
            bot.help_command = PaginatedHelpCommand()
            bot.help_command.cog = self
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize Meta: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{WHITE QUESTION MARK ORNAMENT}')

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    async def cog_command_error(self, ctx: Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument):
            await ctx.error(str(error))

    @commands.command(usage='Syntax: charinfo (characters)\nExample: charinfo 🖐️😔')
    async def charinfo(self, ctx: Context, *, characters: str):
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            c = '\\`' if c == '`' else c
            return f'[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {name} **\N{EM DASH}** {c}'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.warning('Output too long to display.')
        await ctx.send(msg, suppress_embeds=True)

    @commands.command(aliases=['invite'], usage='Syntax: join\n')
    async def join(self, ctx: Context):
        """Posts my invite to allow you to invite me"""
        try:
            message = "Click on **Invite me!** button below to invite me to **your server**."
            embed = make_embed_info(ctx.author, message)

            view = InviteView(ctx)
            out = await ctx.send(embed, view=view)
            view.response = out
        except Exception as e:
            logger.error(f"Failed to send invite: {e}")
