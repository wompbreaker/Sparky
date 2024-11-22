# This file includes parts of code from https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/meta.py
# Original code by [Rapptz]
# Modifications by [wompbreaker]
# This file is licensed under the Mozilla Public License 2.0
# See the LICENSE file for more details

from __future__ import annotations
from logging import getLogger
from collections.abc import Coroutine
import inspect
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union
)

from discord import (
    ButtonStyle,
    Interaction,
    Message,
    utils,
    Permissions,
    Embed,
    Colour,
    HTTPException
)
from discord.ui import (
    Button,
    View,
    Select
)
from discord.ext.menus import (
    ListPageSource,
    PageSource
)
from discord.ext.commands import (
    Cog,
    Command,
    Group,
    CommandError,
    CommandInvokeError,
    CooldownMapping,
    BucketType,
    HelpCommand
)

from helpers import (
    Context,
    SparkyPages,
    Emojis,
    make_embed_warning,
    make_embed_error
)

if TYPE_CHECKING:
    from bot import Sparky

log = getLogger(__name__)

WARNING = Emojis().get_emoji('warning')
COOLDOWN = Emojis().get_emoji('cooldown')
CANCEL = Emojis().get_stripped_emoji('cancel')
VOICE = Emojis().get_emoji('voice')

class CancelButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.red, emoji=CANCEL)

    async def callback(self, interaction: Interaction):
        try:
            await interaction.message.delete()
        except Exception as e:
            log.error(f"Deleting the message failed: {e}")

class InviteView(View):
    response: Message

    def __init__(self, ctx: Context):
        try:
            super().__init__(timeout=20.0)
            self.ctx: Context = ctx
            self.bot: Sparky = ctx.bot
            self.perms = Permissions.none()
            self.perms.administrator = True
            self.url = utils.oauth_url(self.bot.client_id, permissions=self.perms)
            self.add_item(Button(label="Invite me!", url=self.url, style=ButtonStyle.link))
            self.add_item(CancelButton())
        except Exception as e:
            log.error(f"Failed to initialize InviteView: {e}")

    async def on_timeout(self) -> None:
        if self.response.channel and self.response:
            try:
                await self.response.edit(view=None)
            except Exception as e:
                log.error(f"Failed to clear view on timeout: {e}")

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

class MenuGroupHelpPageSource(ListPageSource):
    def __init__(self, group: Union[Group, Cog], entries: List[Command], *, prefix: str):
        super().__init__(entries=entries, per_page=6)
        self.group: Union[Group, Cog] = group
        self.prefix: str = prefix
        self.title: str = f'{self.group.qualified_name} Commands'
        self.description: str = self.group.description

    async def format_page(self, menu: SparkyPages, commands: List[Command]):
        embed = Embed(title=self.title, description=self.description, colour=Colour(0xA8B9CD))

        for command in commands:
            signature = f'{command.qualified_name} {command.description}'
            embed.add_field(name=signature, value=command.short_doc or 'No help given...', inline=False)

        author = menu.ctx.author
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

        maximum = self.get_max_pages()

        if maximum > 1:
            embed.set_footer(text=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)')
        return embed

class GroupHelpPageSource(ListPageSource):
    def __init__(self, group: Union[Group, Cog], entries: List[Command], *, prefix: str):
        super().__init__(entries=entries, per_page=1)
        self.group: Union[Group, Cog] = group
        self.prefix: str = prefix
        self.title: str = f'Group command: {self.group.qualified_name}'
        self.description: str = self.group.description

    async def format_page(self, menu: SparkyPages, command: Command):
        if isinstance(command, Group):
            self.title = f'Group command: {command.qualified_name}'
        else:
            self.title = f'Command: {command.qualified_name}'
        embed = Embed(
            title=self.title, 
            description=self.description, 
            colour=Colour.light_gray()
        )
        author = menu.ctx.author
        
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

        maximum = len(self.entries)
        entry = 'entry' if maximum == 1 else 'entries'
        embed.set_footer(text=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} {entry}) ∙ Module: {self.group.cog_name.lower()}')

        if not command.hidden:
            permissions: List[str] = command.extras.get('permissions', [])
            information: List[str] = command.extras.get('information', {})
            parameters: List[str] = command.extras.get('parameters', [])
            info = '\N{SPIRAL NOTE PAD}'

            if command.cooldown:
                friendly_cooldown = f'{round(command.cooldown.per)} seconds'
                friendly_cooldown = f'{COOLDOWN} {friendly_cooldown}'
            else:
                friendly_cooldown = None

            if permissions:
                friendly_permissions = ', '.join(perm.replace('_', ' ').title() for perm in permissions)
                friendly_permissions = f'{WARNING} {friendly_permissions}'
            else:
                friendly_permissions = None

            if information:
                friendly_information = ', '.join(info_type for info_type in information)
                friendly_information = f'{info} {friendly_information}'
            else:
                friendly_information = None

            if parameters:
                friendly_parameters = ', '.join(param.replace('_', ' ') for param in parameters)
            elif command.clean_params:
                friendly_parameters = ', '.join(param.replace('_', ' ') for param in command.clean_params)
            else:
                friendly_parameters = None

            information = ''
            if friendly_cooldown:
                information += f'{friendly_cooldown}\n'
            if friendly_permissions:
                information += f'{friendly_permissions}\n'
            if friendly_information:
                information += f'{friendly_information}\n'

            embed.title = f'Command: {command.qualified_name}'
            embed.description = command.short_doc or 'No help given...'
            embed.add_field(name='Aliases', value=', '.join(command.aliases) if command.aliases else 'n/a', inline=True)
            embed.add_field(name='Parameters', value=f'{friendly_parameters}' if friendly_parameters else 'n/a', inline=True)
            embed.add_field(name='Information', value=f'{information}' if information != '' else 'n/a', inline=True)
            embed.add_field(name='Usage', value=f'```{command.usage}```' if command.usage else 'n/a', inline=False)

        return embed

class HelpSelectMenu(Select['HelpMenu']):
    def __init__(self, entries: Dict[Cog, List[Command]], bot: Sparky):
        super().__init__(
            placeholder='Select a category...',
            min_values=1,
            max_values=1,
            row=0,
        )
        self.commands: Dict[Cog, List[Command]] = entries
        self.bot: Sparky = bot
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Index',
            emoji='\N{WAVING HAND SIGN}',
            value='__index',
            description='The help page showing how to use the bot.',
        )
        for cog, commands in self.commands.items():
            if not commands:
                continue
            description = cog.description.split('\n', 1)[0] or None
            emoji = getattr(cog, 'display_emoji', None)
            self.add_option(label=cog.qualified_name, value=cog.qualified_name, description=description, emoji=emoji)

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        value = self.values[0]
        if value == '__index':
            await self.view.rebind(FrontPageSource(), interaction)
        else:
            cog = self.bot.get_cog(value)
            if cog is None:
                embed = make_embed_error(interaction.user, 'Somehow this category does not exist?')
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            cog_commands = []
            for command in cog.walk_commands():
                if not command.hidden:
                    cog_commands.append(command)
            if not cog_commands:
                embed = make_embed_warning(interaction.user, 'This category has no commands for you')
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            source = MenuGroupHelpPageSource(cog, cog_commands, prefix=self.view.ctx.clean_prefix)
            await self.view.rebind(source, interaction)


class FrontPageSource(PageSource):
    def is_paginating(self) -> bool:
        # This forces the buttons to appear even in the front page
        return True

    def get_max_pages(self) -> Optional[int]:
        # There's only one actual page in the front page
        # However we need at least 2 to show all the buttons
        return 2

    async def get_page(self, page_number: int) -> Any:
        # The front page is a dummy
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page: Any):
        embed = Embed(title='Bot Help', colour=Colour(0xA8B9CD))
        embed.description = inspect.cleandoc(
            f"""
            Hello! Welcome to the help page.

            Use "{menu.ctx.clean_prefix}help command" for more info on a command.
            Use "{menu.ctx.clean_prefix}help category" for more info on a category.
            """
        )

        embed.add_field(
            name='Support Server',
            value='For more help, consider joining the official server over at https://discord.gg/8MTyyEUsJb',
            inline=False,
        )

        entries = (
            ('<argument>', 'This means the argument is __**required**__.'),
            ('[argument]', 'This means the argument is __**optional**__.'),
        )

        embed.add_field(name='How do I use this bot?', value='Reading the bot signature is pretty simple.')

        for name, value in entries:
            embed.add_field(name=name, value=value, inline=False)

        embed.add_field(name='Note', value='__**You do not type in the brackets!**__', inline=False)

        return embed

class HelpMenu(SparkyPages):
    def __init__(self, source: PageSource, ctx: Context):
        super().__init__(source, ctx=ctx, compact='compact')

    def add_categories(self, commands: Dict[Cog, List[Command]]) -> None:
        self.clear_items()
        self.add_item(HelpSelectMenu(commands, self.ctx.bot))
        self.fill_items()

    async def rebind(self, source: PageSource, interaction: Interaction) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(HelpCommand):
    context: Context

    def __init__(self):
        super().__init__(
            command_attrs={
                'cooldown': CooldownMapping.from_cooldown(1, 3.0, BucketType.member),
                'help': 'Shows help about the bot, a command, or a category',
                'usage': 'Syntax: help [command|category]\nExample: help ping',
            },
            show_hidden=False
        )

    async def on_help_command_error(self, ctx: Context, error: CommandError):
        if isinstance(error, CommandInvokeError):
            # Ignore missing permission errors
            if isinstance(error.original, HTTPException) and error.original.code == 50013:
                return

            await ctx.error(f'An error occurred: {str(error)}')

    async def send_error_message(self, error: str) -> Coroutine[Any, Any, None]:
        embed = make_embed_warning(self.context.author, error)
        await self.context.send(embed)
                        
    def command_not_found(self, string: str):
        return f'Command `{string}` does **not** exist.'
    
    def subcommand_not_found(self, command: Command[Any, Callable[..., Any], Any], string: str):
        return f'Command `{command.qualified_name} {string}` does **not** exist.'

    async def send_bot_help(self, mapping):

        def key(command: Command) -> str:
            cog: Cog = command.cog
            return cog.qualified_name if cog else '\U0010ffff'

        entries: List[Command] = await self.filter_commands(self.context.bot.commands, sort=True, key=key)

        all_commands: Dict[Cog, List[Command]] = {}
        for name, children in itertools.groupby(entries, key=key):
            if name == '\U0010ffff':
                continue

            cog = self.context.bot.get_cog(name)
            assert cog is not None
            all_commands[cog] = sorted(children, key=lambda c: c.qualified_name)

        menu = HelpMenu(FrontPageSource(), ctx=self.context)
        menu.add_categories(all_commands)
        await menu.start()

    async def send_cog_help(self, cog: Cog):
        await self.send_bot_help(cog)

    async def send_command_help(self, command: Command):
        if command.hidden:
            return
        
        embed = Embed(
            colour=Colour.light_gray()
        )
        author = self.context.author
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
        embed.set_footer(text=f'Page 1/1 (1 entry) ∙ Module: {command.cog_name.lower()}')

        if not command.hidden:
            permissions: List[str] = command.extras.get('permissions', [])
            information: Dict[str, Any] = command.extras.get('information', {})
            parameters: List[str] = command.extras.get('parameters', [])
            info = '\N{SPIRAL NOTE PAD}'

            if command.cooldown:
                friendly_cooldown = f'{round(command.cooldown.per)} seconds'
                friendly_cooldown = f'{COOLDOWN} {friendly_cooldown}'
            else:
                friendly_cooldown = None

            if permissions:
                friendly_permissions = ', '.join(perm.replace('_', ' ').title() for perm in permissions)
                friendly_permissions = f'{WARNING} {friendly_permissions}'
            else:
                friendly_permissions = None

            if information:
                friendly_information = ', '.join(info_type for info_type in information)
                friendly_information = f'{info} {friendly_information}'
            else:
                friendly_information = None

            if parameters:
                friendly_parameters = ', '.join(param.replace('_', ' ') for param in parameters)
            elif command.clean_params:
                friendly_parameters = ', '.join(param.replace('_', ' ') for param in command.clean_params)
            else:
                friendly_parameters = None

            information = ''
            if friendly_cooldown:
                information += f'{friendly_cooldown}\n'
            if friendly_permissions:
                information += f'{friendly_permissions}\n'
            if friendly_information:
                information += f'{friendly_information}\n'

            embed.title = f'Command: {command.qualified_name}'
            embed.description = command.short_doc or 'No help given...'
            embed.add_field(name='Aliases', value=', '.join(command.aliases) if command.aliases else 'n/a', inline=True)
            embed.add_field(name='Parameters', value=f'{friendly_parameters}' if friendly_parameters else 'n/a', inline=True)
            embed.add_field(name='Information', value=f'{information}' if information != '' else 'n/a', inline=True)
            embed.add_field(name='Usage', value=f'```{command.usage}```' if command.usage else 'n/a', inline=False)

        await self.context.send(embed)

    async def send_group_help(self, group: Group):
        all_commands = [group]
        for command in group.walk_commands():
            if command.hidden:
                continue
            all_commands.append(command)
        entries = all_commands
        if len(entries) == 0:
            return
        if len(entries) == 1:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        menu = HelpMenu(source, ctx=self.context)
        await menu.start()
