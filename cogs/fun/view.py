from typing import Optional, List, Tuple
import logging
from io import BytesIO

from aiohttp import ClientSession
from discord.ext.menus import PageSource, ListPageSource
from discord import (
	Embed, 
	Message, 
	File, 
	Color, 
	Interaction, 
	ButtonStyle, 
	Button, 
	GuildSticker
)
from discord.ui import (
	View, 
	Item, 
	button,
	Button
)

from helpers import (
	Emojis,
	Context,
	SparkyPages,
	make_embed_error,
	make_embed_warning,
	make_embed_success
)

log = logging.getLogger(__name__)

SCISSORS = Emojis().get_stripped_emoji('scissors')
DENY = Emojis().get_stripped_emoji('cancel')

class BaseStealView(View):
	response: Message

	def __init__(
		self, 
		ctx: Context, 
		data: Optional[bytes], 
		sticker: Optional[GuildSticker], 
		message_content: Optional[str]
	) -> None:
		super().__init__(timeout=60.0)
		self.value = None
		self.ctx: Context = ctx
		self.data: Optional[bytes] = data
		self.sticker: Optional[GuildSticker] = sticker
		self.message_content: Optional[str] = message_content

	async def on_error(self, interaction: Interaction, error: Exception, item: Item) -> None:
		embed = make_embed_error(
			interaction.user,
			f"An error has occurred: {error.with_traceback(tb=Exception.__traceback__)}"
		)
		await interaction.response.send_message(embed=embed, ephemeral=True)

	async def on_timeout(self) -> None:
		if self.response.channel and self.response:
			try:
				await self.response.edit(view=None)
			except Exception:
				pass

	async def interaction_check(self, interaction: Interaction) -> bool:
		if interaction.user != self.ctx.author:
			embed = make_embed_warning(
				interaction.user,
				"You're not the **author** of this embed!"
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return False
		return True

	@button(emoji=DENY, style=ButtonStyle.red)
	async def cancel(self, interaction: Interaction, button: Button):
		try:
			await interaction.message.delete()
		except Exception as e:
			embed = make_embed_error(
				interaction.user,
				f"An error has occurred: {e}"
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
			log.error(f"Exception in Fun, cancel method: {e}")

	@button(emoji=SCISSORS, style=ButtonStyle.gray)
	async def crop(self, interaction: Interaction, button: Button):
		try:
			if not interaction.user.guild_permissions.manage_emojis_and_stickers:
				embed = make_embed_warning(
					interaction.user,
					f"You don't have the `create expressions` permission."
				)
				await interaction.response.send_message(embed=embed, ephemeral=True)
				return
			if len(self.data) > 512 * 1024:
				await interaction.response.send_message(
					content="File size is too big to be added to this guild",
					ephemeral=True
				)
				return

			guild = interaction.guild
			is_verified_guild: bool = True if "VERIFIED" in guild.features else False
			is_partnered_guild: bool = True if "PARTNERED" in guild.features else False

			lottie_eligible: bool = True if is_partnered_guild or is_verified_guild else False
			if not lottie_eligible and self.sticker.format.file_extension == 'json':
				embed = make_embed_warning(
					interaction.user,
					"This server can't add **lottie** files as a sticker.",
				)
				await interaction.response.send_message(embed=embed, ephemeral=True)
				return
			if len(guild.stickers) >= guild.sticker_limit:
				embed = make_embed_warning(
					interaction.user,
					f"Couldn't add a sticker, server is at its **sticker limit**. "
				)
				await interaction.response.send_message(embed=embed, ephemeral=True)
				return
			file = File(
				BytesIO(self.data),
				filename=f"{self.sticker.name}.{self.sticker.format.file_extension}"
			)
			await guild.create_sticker(
				name=self.sticker.name,
				emoji=":robot:",
				file=file,
				description=f"Sticker created by {interaction.user.name} by steal command",
				reason=f"Sticker created by {interaction.user.name} by steal command"
			)
			message = "Successfully created a sticker!"
			embed = make_embed_success(
				interaction.user,
				"Successfully created a sticker!"
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
		except Exception as e:
			log.error(f"Exception in Fun, steal_emoji_or_sticker, crop_callback: {e}")
			embed = make_embed_warning(
				interaction.user,
				"Failed to create sticker."
			)
			await interaction.response.send_message(embed=embed, ephemeral=True)
			return

class StealPageSource(ListPageSource):
	def __init__(self, entries: List[Tuple[str, str, str]]):
		super().__init__(entries, per_page=1)

	async def format_page(self, menu: SparkyPages, entry: Tuple[str, str, str]):
		emoji_name, emoji_id, emoji_url = entry
		embed = Embed(
			title=emoji_name,
			color=Color.light_gray()
		)
		if menu.ctx.author.avatar:
			embed.set_author(name=menu.ctx.author.display_name, icon_url=menu.ctx.author.avatar.url)
		else:
			embed.set_author(name=menu.ctx.author.display_name, icon_url=menu.ctx.author.default_avatar.url)
		embed.add_field(name="Emoji ID", value=f"`{emoji_id}`", inline=True)
		guild = menu.ctx.guild
		if guild:
			# check if the emoji is from a guild
			emoji = guild.get_emoji(int(emoji_id))
			embed.add_field(name="Guild", value=guild.name if emoji else "Unknown", inline=True)
		else:
			embed.add_field(name="Guild", value="Unknown", inline=True)
		embed.add_field(name="Image URL", value=f"[**Click here to open the image**]({emoji_url})", inline=False)
		embed.set_image(url=emoji_url)

		maximum = len(self.entries)
		entry = 'entry' if maximum == 1 else 'entries'
		embed.set_footer(text=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} {entry})")
		
		# get data from image url
		async with ClientSession() as session:
			async with session.get(emoji_url) as resp:
				if resp.status == 200:
					menu.data = await resp.read()
		menu.emoji_name = emoji_name
		return embed
	
class StealMenu(SparkyPages):
	def __init__(self, source: PageSource, ctx: Context):
		super().__init__(source, ctx=ctx, compact='steal')
  