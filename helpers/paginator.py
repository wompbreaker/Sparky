# This file includes parts of code from https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py
# Original code by Rapptz
# Modifications by wompbreaker
# This file is licensed under the Mozilla Public License 2.0 (MPL 2.0)
# See the LICENSE file for more details

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Literal, TYPE_CHECKING
from .utils.emojis import Emojis
from .managers.context import Context
from .utils.embeds import (
    make_embed_success, 
    make_embed_warning, 
    make_embed_error
)
from discord.ext.menus import PageSource
from discord import (
    ButtonStyle,
    Guild,
    Interaction,
    Message,
    Embed,
    utils as discord_utils
)
from discord.ui import (
    Modal, 
    TextInput, 
    Button, 
    View,
    Item,
    button
)

if TYPE_CHECKING:
    from bot import Sparky

log = logging.getLogger(__name__)

RIGHT = Emojis().get_stripped_emoji("right")
LEFT = Emojis().get_stripped_emoji("left")
CANCEL = Emojis().get_stripped_emoji("cancel")
SKIP = Emojis().get_stripped_emoji("skip_to_page")
SCISSORS = Emojis().get_stripped_emoji("scissors")

__all__ = (
    'NumberedPageModal',
    'SparkyPages'
)

class NumberedPageModal(Modal, title='Go to page'):
    page = TextInput(label='Page', placeholder='Enter a number', min_length=1)

    def __init__(self, max_pages: Optional[int]) -> None:
        super().__init__()
        if max_pages is not None:
            as_string = str(max_pages)
            self.page.placeholder = f"Enter a number between 1 and {as_string}"
            self.page.max_length = len(as_string)

    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        self.stop()

class SparkyPages(View):
    def __init__(
        self,
        source: PageSource,
        *,
        ctx: Context,
        check_embeds: bool = True,
        data: Optional[bytes] = None,
        message_content: Optional[str] = None,
        compact: Literal['compact', 'full', 'steal'] = 'compact'
    ):
        super().__init__()
        self.source: PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx: Context = ctx
        self.message: Optional[Message] = None
        self.current_page: int = 0
        self.compact: Literal['compact', 'full', 'steal'] = compact
        self.data: Optional[bytes] = data
        self.message_content: Optional[str] = message_content
        self.emoji_name: Optional[str] = None
        self.bot: Sparky = ctx.bot
        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:

        if self.compact == 'full':
            self.numbered_page.row = 1
            self.stop_pages.row = 1

        if self.source.is_paginating():
            # full setup
            if self.compact == 'full':
                max_pages = self.source.get_max_pages()
                use_last_and_first = max_pages is not None and max_pages >= 2 and self.compact == 'full'
                if use_last_and_first:
                    self.add_item(self.go_to_first_page)
                self.add_item(self.go_to_previous_page)
                self.add_item(self.go_to_current_page)
                self.add_item(self.go_to_next_page)
                if use_last_and_first:
                    self.add_item(self.go_to_last_page)
                self.add_item(self.numbered_page)
                self.add_item(self.stop_pages)

            # compact setup
            elif self.compact == 'compact':
                self.add_item(self.go_to_previous_page)
                self.add_item(self.go_to_next_page)
                self.add_item(self.numbered_page)
                self.add_item(self.stop_pages)

            # steal setup
            elif self.compact == 'steal':
                max_pages = self.source.get_max_pages()
                use_arrows = max_pages is not None and max_pages >= 2
                if use_arrows:
                    self.add_item(self.go_to_previous_page)
                    self.add_item(self.go_to_next_page)
                self.add_item(self.stop_pages)
                if self.ctx.author.guild_permissions.manage_emojis_and_stickers:
                    self.add_item(self.crop)
            else:
                raise ValueError("Invalid compact type")
        else:
            if self.compact == 'steal':
                max_pages = self.source.get_max_pages()
                use_arrows = max_pages is not None and max_pages >= 2
                if use_arrows:
                    self.add_item(self.go_to_previous_page)
                    self.add_item(self.go_to_next_page)
                self.add_item(self.stop_pages)
                if self.ctx.author.guild_permissions.manage_emojis_and_stickers:
                    self.add_item(self.crop)
            else:
                raise ValueError("Invalid compact type")

    async def _get_kwargs_from_page(self, page: int) -> Dict[str, Any]:
        value = await discord_utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {'content': value, 'embed': None}
        elif isinstance(value, Embed):
            return {'embed': value, 'content': None}
        else:
            return {}

    async def show_page(self, interaction: Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:
        self.go_to_first_page.disabled = page_number == 0
        if self.compact == 'compact':
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = max_pages is None or (page_number + 1) >= max_pages
            self.go_to_next_page.disabled = max_pages is not None and (page_number + 1) >= max_pages
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
            if page_number == 0:
                self.go_to_previous_page.disabled = True

    async def show_checked_page(
        self, interaction: Interaction, page_number: int
    ) -> None:
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            pass

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author and interaction.user.id \
            not in (self.ctx.bot.owner_id, self.ctx.author.id):
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(self, interaction: Interaction, error: Exception, item: Item) -> None:
        if interaction.response.is_done():
            embed = make_embed_error(
                interaction.user, f"An error occurred in {self.__class__.__name__}: {error}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = make_embed_error(
                interaction.user, f"An error occurred in {self.__class__.__name__}: {error}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def start(self, *, content: Optional[str] = None, ephemeral: bool = False) -> None:
        if self.check_embeds and not self.ctx.channel.permissions_for(self.ctx.me).embed_links:  # type: ignore
            await self.ctx.warning('Bot does not have embed links permission in this channel.', ephemeral=True)
            return

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if content:
            kwargs.setdefault('content', content)

        self._update_labels(0)
        if 'embed' in kwargs:
            args = (kwargs.pop('embed'),)
        elif 'content' in kwargs:
            args = (kwargs.pop('content'),)
        else:
            args = ()

        self.message = await self.ctx.send(*args, **kwargs, ephemeral=ephemeral, view=self)

    @button(label='≪', style=ButtonStyle.grey)
    async def go_to_first_page(self, interaction: Interaction, button: Button):
        """go to the first page"""
        await self.show_page(interaction, 0)

    @button(emoji=LEFT, style=ButtonStyle.blurple)
    async def go_to_previous_page(self, interaction: Interaction, button: Button):
        """go to the previous page"""
        await self.show_checked_page(interaction, self.current_page - 1)

    @button(label='Current', style=ButtonStyle.grey, disabled=True)
    async def go_to_current_page(self, interaction: Interaction, button: Button):
        pass

    @button(emoji=RIGHT, style=ButtonStyle.blurple)
    async def go_to_next_page(self, interaction: Interaction, button: Button):
        """go to the next page"""
        await self.show_checked_page(interaction, self.current_page + 1)

    @button(label='≫', style=ButtonStyle.grey)
    async def go_to_last_page(self, interaction: Interaction, button: Button):
        """go to the last page"""
        await self.show_page(interaction, self.source.get_max_pages() - 1)  # type: ignore

    @button(emoji=SKIP, style=ButtonStyle.grey)
    async def numbered_page(self, interaction: Interaction, button: Button):
        """lets you type a page number to go to"""
        if self.message is None:
            return

        modal = NumberedPageModal(self.source.get_max_pages())
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()

        if timed_out:
            embed = make_embed_warning(
                interaction.user, "Took too long"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        elif self.is_finished():
            embed = make_embed_warning(
                interaction.user, "The session has ended"
            )
            await modal.interaction.response.send_message(embed=embed, ephemeral=True)
            return

        value = str(modal.page.value)
        if not value.isdigit():
            embed = make_embed_warning(
                interaction.user, "Expected a **number** not {value!r}"
            )
            await modal.interaction.response.send_message(embed=embed, ephemeral=True)
            return

        value = int(value)
        await self.show_checked_page(modal.interaction, value - 1)
        if not modal.interaction.response.is_done():
            error = modal.page.placeholder.replace('Enter', 'Expected')  # type: ignore # Can't be None
            embed = make_embed_warning(interaction.user, error)
            await modal.interaction.response.send_message(embed=embed, ephemeral=True)

    @button(emoji=CANCEL, style=ButtonStyle.red)
    async def stop_pages(self, interaction: Interaction, button: Button):
        """stops the pagination session."""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    @button(emoji=SCISSORS, style=ButtonStyle.gray)
    async def crop(self, interaction: Interaction, button: Button):
        """Crops the message to the current page."""
        try:
            
            if not interaction.user.guild_permissions.manage_emojis_and_stickers:
                embed = make_embed_warning(
                    interaction.user, "You don't have the `manage emojis` permission."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            if len(self.data) > 512 * 1024:
                embed = make_embed_error(
                    interaction.user, "File size is too big to be added to this guild"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            guild: Guild = interaction.guild
            if len(guild.emojis) >= guild.emoji_limit:
                embed = make_embed_warning(
                    interaction.user, "The guild has reached the **emoji limit**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # add the emoji to the guild
            try:
                await guild.create_custom_emoji(name=self.emoji_name, image=self.data)
            except Exception as e:
                embed = make_embed_error(
                    interaction.user, f"Failed to create emoji: {e}"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            else:
                embed = make_embed_success(
                    interaction.user, f"Emoji **{self.emoji_name}** created successfully!"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.exception(f"Exception in Fun, crop method: {e}")
            embed = make_embed_error(
                interaction.user, "An unknown error occurred, sorry"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
