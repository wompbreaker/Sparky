from typing import Any

from discord import Interaction, Message, Embed, ButtonStyle, HTTPException
from discord.ui import Item, View, Button, button

from bot import Sparky
from helpers import (
    Context,
    make_embed_error, 
    make_embed_warning,
    make_embed_mute
)
from .selects import *


DEFAULT_DESCRIPTION = """Use the buttons below to customize this embed. 
You can click the `Code` button to copy this embed or use `embed preview {name}` to show this embed."""

class EditFieldView(View):
    def __init__(self, ctx: Context, message: Message, embed: Embed):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot: Sparky = ctx.bot
        self.add_item(EditFieldSelect(message, embed))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item) -> None:
        embed = make_embed_error(
            interaction.user, f"An error occurred in {self.__class__.__name__}: {error}"
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
class DeleteFieldView(View):
    def __init__(self, ctx: Context, message: Message, embed: Embed):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot: Sparky = ctx.bot
        self.add_item(DeleteFieldSelect(message, embed))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item) -> None:
        embed = make_embed_error(
            interaction.user, f"An error occurred in {self.__class__.__name__}: {error}"
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
class EmbedView(View):
    def __init__(self, ctx: Context, name: str):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot: Sparky = ctx.bot
        self.name = name

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def on_error(self, interaction: Interaction, error: Exception, item: Item) -> None:
        embed = make_embed_error(
            interaction.user, f"An error occurred in {self.__class__.__name__}: {error}"
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @button(label="Edit Basic Information", style=ButtonStyle.gray)
    async def edit_basic_information(self, interaction: Interaction, button: Button) -> None:
        modal = EditEmbedModal(interaction.message)
        embed = interaction.message.embeds[0]
        modal.description.default = embed.description \
            if embed.description != DEFAULT_DESCRIPTION.format(name=self.name) else None
        await interaction.response.send_modal(modal)
        
    @button(label="Edit Author", style=ButtonStyle.gray)
    async def edit_author(self, interaction: Interaction, button: Button):
        modal = EditAuthorModal(interaction.message.embeds[0])
        await interaction.response.send_modal(modal)

    @button(label="Edit Footer", style=ButtonStyle.gray)
    async def edit_footer(self, interaction: Interaction, button: Button):
        modal = EditFooterModal(interaction.message.embeds[0])
        await interaction.response.send_modal(modal)

    @button(label="Edit Images", style=ButtonStyle.gray)
    async def edit_images(self, interaction: Interaction, button: Button):
        modal = EditImagesModal(interaction.message.embeds[0])
        await interaction.response.send_modal(modal)

    @button(label="Add Field", style=ButtonStyle.gray, row=1)
    async def add_field(self, interaction: Interaction, button: Button):
        modal = AddFieldModal()
        await interaction.response.send_modal(modal)

    @button(label="Edit Field", style=ButtonStyle.gray, row=1)
    async def edit_field(self, interaction: Interaction, button: Button):
        try:
            view = EditFieldView(self.ctx, interaction.message, interaction.message.embeds[0])
            prompt_embed = make_embed_mute(interaction.user, "Select a field to edit:")
            await interaction.response.send_message(embed=prompt_embed, view=view, ephemeral=True)
        except HTTPException as e:
            if e.code == 50035:
                error_message = "You can't **edit** an embed with **no fields**."
            else:
                error_message = f"An error occurred: {e}"
            embed = make_embed_warning(interaction.user, error_message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"{type(e)} An error occurred in EmbedView edit_field: {e}")
            embed = make_embed_error(
                interaction.user, f"An error occurred: {e}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label='Delete Field', style=ButtonStyle.gray, row=1)
    async def delete_field(self, interaction: Interaction, button: Button):
        try:
            view = DeleteFieldView(self.ctx, interaction.message, interaction.message.embeds[0])
            prompt_embed = make_embed_mute(
                interaction.user, "Select a field to delete:"
            )
            await interaction.response.send_message(prompt_embed, view=view, ephemeral=True)
        except HTTPException as e:
            if e.code == 50035:
                error_message = "You can't **delete** an embed with **no fields**."
            else:
                error_message = f"An error occurred: {e}"
            error_embed = make_embed_warning(interaction.user, error_message)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            log.error(f"{type(e)} An error occurred in delete_field: {e}")
            error_embed = make_embed_error(
                interaction.user, f"An error occurred: {e}"
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @button(label='Code', style=ButtonStyle.gray, row=1)
    async def code(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send('Code', ephemeral=True)
