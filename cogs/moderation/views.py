from logging import getLogger

from discord.ext.menus import ListPageSource, PageSource
from discord.abc import GuildChannel
from discord.ui import View, Button, button
from discord import (
	ButtonStyle,
	Embed,
	Colour,
	Message,
	Interaction
)

from helpers import (
	make_embed_error,
	make_embed_warning,
	Context,
	SparkyPages
)

log = getLogger(__name__)

__all__ = (
	"IgnoredChannelsPageSource",
	"IgnoredChannelsMenu",
	"ConfirmView"
)

class IgnoredChannelsPageSource(ListPageSource):
	def __init__(self, entries: list[GuildChannel]):
		super().__init__(entries=entries, per_page=10)
		self.title: str = 'Ignored Lockdown Channels'
		self.description: str = f''

	async def format_page(self, menu: SparkyPages, channels: list[GuildChannel]):
		embed = Embed(title=self.title, colour=Colour(0xFFFFFF))
		channel_entries = ''
		for channel in channels:
			channel_entry = f"`{menu.current_page*10 + channels.index(channel) + 1}` {channel.mention} (`{channel.id}`)"
			channel_entries += channel_entry + "\n"

		embed.description = channel_entries
		author = menu.ctx.author
		embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

		maximum = self.get_max_pages()

		if maximum > 1:
			embed.set_footer(text=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} channels)')
		return embed

class IgnoredChannelsMenu(SparkyPages):
	def __init__(self, source: PageSource, ctx: Context):
		super().__init__(source, ctx=ctx, compact='compact')

class ConfirmView(View):
	response: Message

	def __init__(self, ctx: Context):
		super().__init__(timeout=20.0)
		self.ctx: Context = ctx

	async def on_timeout(self) -> None:
		if self.response.channel and self.response:
			try:
				await self.response.edit(view=None)
			except Exception:
				pass

	async def interaction_check(self, interaction: Interaction) -> bool:
		if interaction.user != self.ctx.author:
			embed = make_embed_warning(
				interaction.user, "You're not the **author** of this embed!"
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return False
		return True

	@button(label="Approve", style=ButtonStyle.green)
	async def approve(self, interaction: Interaction, button: Button):
		new_name = interaction.channel.name
		nuke_reason = f"Channel clone requested by {self.ctx.message.author} ({self.ctx.message.author.id})"

		try:
			new_channel = await interaction.channel.clone(name=new_name, reason=nuke_reason)
			await new_channel.move(after=interaction.channel)
			await new_channel.send("first")
			await interaction.channel.delete()
		except Exception as e:
			message = f"Moving the channel failed: {e}"
			embed = make_embed_error(self.ctx.message.author, message)
			await interaction.channel.send(embed=embed)

	@button(label="Decline", style=ButtonStyle.red)
	async def decline(self, interaction: Interaction, button: Button):
		try:
			await interaction.message.delete()
		except Exception as e:
			embed = make_embed_error(
				interaction.user, f"Deleting the message failed: {e}"
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
			log.error(f"Deleting the message failed: {e}")
