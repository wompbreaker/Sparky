from discord.ui import Modal, TextInput
from discord import Interaction, TextStyle, Message, Color, Embed
from bot import Sparky
from datetime import datetime
import logging
from helpers import make_embed_error

log = logging.getLogger(__name__)

class EditEmbedModal(Modal, title="Edit Basic Information"):
    embed_title = TextInput(
        label='Title', 
        placeholder="Enter a title", 
        required=False,
        style=TextStyle.short,
        custom_id='embed_title'
    )
    description = TextInput(
        label='Description', 
        placeholder="Enter a description", 
        required=False,
        style=TextStyle.paragraph,
        max_length=4000,
        custom_id='embed_description'
    )
    hex_code = TextInput(
        label="Hex Code", 
        placeholder='#747f8d', 
        required=False,
        style=TextStyle.short,
        max_length=8,
        custom_id='embed_color'
    )
    message_content = TextInput(
        label="Message Content", 
        placeholder="Message content that will appear outside of the embed", 
        required=False,
        style=TextStyle.short,
        max_length=2000,
        custom_id='embed_message_content'
    )

    def __init__(self, message: Message) -> None:
        super().__init__(timeout=None)
        self.embed = message.embeds[0]
        self.message = message
        self.set_defaults()
        
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        self.interaction = interaction

        if self.embed_title.value:
            self.embed.title = self.embed_title.value
        else:
            self.embed.title = None

        if self.description.value:
            self.embed.description = self.description.value
        else:
            self.embed.description = None

        if self.hex_code.value:
            try:
                self.embed.color = int(self.hex_code.value.replace('#', '').replace('0x', ''), 16)
            except ValueError:
                self.embed.color = Color(0x747f8d)
        else:
            self.embed.color = Color(0x747f8d)

        self.message.content = self.message_content.value
        
        await interaction.message.edit(embed=self.embed, content=self.message.content)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        embed = make_embed_error(interaction.user, f"An error occurred in EditEmbedModal: {error}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def set_defaults(self):
        if self.embed.title:
            self.embed_title.default = self.embed.title
        if self.embed.color != Color(0x747f8d):
            self.hex_code.default = str(self.embed.color)
        if self.message.content:
            self.message_content.default = self.message.content

class EditAuthorModal(Modal, title="Edit Author"):
    author_text = TextInput(
        label="Author Text", 
        placeholder="Enter an author text", 
        max_length=256,

        required=False
    )
    author_url = TextInput(
        label="Author URL", 
        placeholder='https://example.com', 
        required=False
    )
    author_image_url = TextInput(
        label="Author Image URL", 
        placeholder='https://i.imgur.com/WtZYZNL.png', 
        required=False
    )

    def __init__(self, embed: Embed) -> None:
        super().__init__(timeout=None)
        self.embed = embed
        self.set_defaults()
        
    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        author_name = self.author_text.value if self.author_text.value else None
        author_url = self.author_url.value if self.author_url.value else None
        author_icon = self.author_image_url.value if self.author_image_url.value else None
        embed.set_author(name=author_name, url=author_url, icon_url=author_icon)
        await interaction.message.edit(embed=embed)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"An error occurred in EditAuthorModal: {error}", ephemeral=True)

    def set_defaults(self):
        if self.embed.author:
            if self.embed.author.name and self.embed.author.name != "embed creation":
                self.author_text.default = self.embed.author.name 
            self.author_url.default = self.embed.author.url
            self.author_image_url.default = self.embed.author.icon_url

class EditFooterModal(Modal, title="Edit Footer"):
    footer_text = TextInput(
        label="Footer Text", 
        placeholder='Enter an Footer text', 
        required=False
    )
    footer_image_url = TextInput(
        label="Footer Image URL", 
        placeholder='https://i.imgur.com/WtZYZNL.png', 
        required=False
    )
    footer_timestamp = TextInput(
        label="Timestamp (yes or no)", 
        placeholder='yes', 
        required=False
    )

    def __init__(self, embed: Embed) -> None:
        super().__init__(timeout=None)
        self.embed = embed
        self.set_defaults()
        
    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        footer_text = self.footer_text.value if self.footer_text.value else None
        footer_icon = self.footer_image_url.value if self.footer_image_url.value else None
        footer_timestamp = self.footer_timestamp.value if self.footer_timestamp.value else 'yes'
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        if footer_timestamp.lower() == 'yes':
            embed.timestamp = datetime.now()
        else:
            embed.timestamp = None
        await interaction.message.edit(embed=embed)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"An error occurred in EditFooterModal: {error}", ephemeral=True)

    def set_defaults(self):
        if self.embed.footer:
            self.footer_text.default = self.embed.footer.text
            self.footer_image_url.default = self.embed.footer.icon_url
            self.footer_timestamp.default = 'yes' if self.embed.timestamp else 'no'

class EditImagesModal(Modal, title="Edit Images"):
    image_url = TextInput(
        label='Image', 
        placeholder='https://i.imgur.com/WtZYZNL.png', 
        required=False
    )
    thumbnail_url = TextInput(
        label='Thumbnail', 
        placeholder='https://i.imgur.com/WtZYZNL.png', 
        required=False
    )

    def __init__(self, embed: Embed) -> None:
        super().__init__(timeout=None)
        self.embed = embed
        self.set_defaults()
        
    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        image_url = self.image_url.value if self.image_url.value else None
        thumbnail_url = self.thumbnail_url.value if self.thumbnail_url.value else None
        embed.set_image(url=image_url)
        embed.set_thumbnail(url=thumbnail_url)
        await interaction.message.edit(embed=embed)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"An error occurred in EditImagesModal: {error}", ephemeral=True)

    def set_defaults(self):
        if self.embed.image:
            self.image_url.default = self.embed.image.url
        if self.embed.thumbnail:
            self.thumbnail_url.default = self.embed.thumbnail.url

class AddFieldModal(Modal, title="Add Field"):
    field_name = TextInput(
        label="Field Name", 
        placeholder="Rule #1", 
        required=False
    )
    field_value = TextInput(
        label="Field Value", 
        placeholder="Follow Discord's ToS", 
        required=False
    )
    field_index = TextInput(
        label="Field Index", 
        placeholder="1", 
        required=False
    )
    field_inline = TextInput(
        label="Inline (yes or no)", 
        placeholder="yes", 
        required=False
    )

    def __init__(self) -> None:
        super().__init__(timeout=None)
        
    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        field_name = self.field_name.value if self.field_name.value else ''
        field_value = self.field_value.value if self.field_value.value else ''
        field_index = self.field_index.value if self.field_index.value else len(embed.fields)
        field_inline = self.field_inline.value if self.field_inline.value else 'yes'
        inline = True if field_inline.lower() == 'yes' else False
        embed.insert_field_at(index=int(field_index), name=field_name, value=field_value, inline=inline)
        await interaction.message.edit(embed=embed)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"An error occurred in AddFieldModal: {error}", ephemeral=True)

class EditFieldModal(Modal):
    new_field_name = TextInput(
        label="New Field Name", 
        placeholder="Rule #2", 
        required=False
    )
    field_value = TextInput(
        label="Field Value", 
        placeholder="", 
        required=False
    )
    field_index = TextInput(
        label="Field Index", 
        placeholder="1", 
        required=False
    )
    field_inline = TextInput(
        label="Inline (yes or no)", 
        placeholder="yes", 
        required=False
    )

    def __init__(self, message: Message, embed: Embed, old_name: str) -> None:
        super().__init__(timeout=None, title=f"Edit Field {old_name}")
        self.message = message
        self.embed = embed
        self.old_field_name = old_name
        
    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction
        await interaction.response.defer()
        new_field_name = self.new_field_name.value if self.new_field_name.value else ''
        field_value = self.field_value.value if self.field_value.value else ''
        field_index = self.field_index.value if self.field_index.value else len(self.embed.fields)
        field_inline = self.field_inline.value if self.field_inline.value else 'yes'
        inline = True if field_inline.lower() == 'yes' else False
        for i, field in enumerate(self.embed.fields):
            if field.name == self.old_field_name:
                self.embed.set_field_at(i, name=new_field_name, value=field_value, inline=inline)
                break
        await self.message.edit(embed=self.embed)
        self.stop()

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"An error occurred in EditFieldModal: {error}", ephemeral=True)
