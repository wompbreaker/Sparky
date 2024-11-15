from discord.ui import Select
from discord import Interaction, Message, Embed, SelectOption
import logging
from .modals import *
from helpers import make_embed_error

logger = logging.getLogger(__name__)

class EditFieldSelect(Select):
	def __init__(self, message: Message, embed: Embed):
		try:
			self.embed: Embed = embed
			self.message: Message = message
			options = [SelectOption(
				label=field.name, value=str(i)
			) for i, field in enumerate(embed.fields)]
			super().__init__(options=options, min_values=1, max_values=1)
		except Exception as e:
			logger.error(f"An error occurred in EditFieldSelect init: {e}")

	async def callback(self, interaction: Interaction):
		index = int(self.values[0])
		field = self.embed.fields[index]
		modal = EditFieldModal(self.message, self.embed, field.name)
		modal.field_value.default = field.value
		modal.field_index.default = str(index)
		modal.field_inline.default = 'yes' if field.inline else 'no'
		await interaction.response.send_modal(modal)

	async def on_error(self, interaction: Interaction, error: Exception) -> None:
		embed = make_embed_error(
			interaction.user, f"An error occurred in EditFieldSelect: {error}"
		)
		await interaction.response.send_message(embed=embed, ephemeral=True)

class DeleteFieldSelect(Select):
	def __init__(self, message: Message, embed: Embed):
		self.embed: Embed = embed
		self.message: Message = message
		options = [SelectOption(
			label=field.name, value=str(i)
		) for i, field in enumerate(embed.fields)]
		super().__init__(options=options, min_values=1, max_values=1)

	async def callback(self, interaction: Interaction):
		await interaction.response.defer()
		index = int(self.values[0])
		self.embed.remove_field(index)
		await self.message.edit(embed=self.embed)

	async def on_error(self, interaction: Interaction, error: Exception) -> None:
		embed = make_embed_error(
			interaction.user, f"An error occurred in DeleteFieldSelect: {error}"
		)
		await interaction.response.send_message(embed=embed, ephemeral=True)