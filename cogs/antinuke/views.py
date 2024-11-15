from discord.ui import (
    View,
    Button,
    button
)
from discord import (
	Interaction,
	Embed,
	Color,
	ButtonStyle
)
from helpers import (
	make_embed_error,
	make_embed_warning
)

perm_list = [
    'administrator', 'ban_members', 'kick_members', 'manage_channels', 
    'manage_permissions', 'manage_emojis', 'manage_emojis_and_stickers', 
    'manage_guild', 'manage_roles', 'manage_webhooks', 'moderate_members'
]

class ConfirmView(View):

    def __init__(self, interaction: Interaction) -> None:
        super().__init__(timeout=20.0)
        self.value = None
        self.interaction: Interaction = interaction
        self.response = None
    
    @staticmethod
    def make_embed_permissions(interaction: Interaction) -> Embed:
        perm_string = ""
        for perm in perm_list:
            perm_string += f"{perm}, "        
        embed = Embed(
            title="List of permissions",
            color=Color.blurple(),
            description=f"```{perm_string[:-2]}```"
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        return embed

    async def on_timeout(self) -> None:
        if self.response.channel and self.response:
            try:
                await self.response.edit_message(view=None)
            except Exception:
                pass

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.interaction.user:
            embed = make_embed_warning(
                interaction.user, "You're not the **author** of this embed!"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @button(label="Show list", style=ButtonStyle.gray)
    async def approve(self, interaction: Interaction, button: Button):
        try:
            embed = self.make_embed_permissions(interaction)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = make_embed_error(interaction.user, f"Showing the perm list failed: {e}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
