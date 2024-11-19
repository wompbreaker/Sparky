from logging import getLogger
from typing import Optional

import discord
from discord.ext import commands

from bot import Sparky
from helpers import Context, Emojis
from .views import EmbedView

log = getLogger(__name__)

DEFAULT_AUTHOR_TEXT = "embed creation"
DEFAULT_DESCRIPTION = ("Use the buttons below to customize this embed. "
					   "You can click the `Code` button to copy this embed or "
					   "use `embed preview {name}` to show this embed.")
DEFAULT_COLOR = discord.Color(0x747f8d)

class Misc(commands.Cog):
	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			log.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			log.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@property
	def display_emoji(self) -> discord.PartialEmoji:
		return Emojis().get_emoji("misc")	

###############################################################################
#                                           COMMANDS                                                  #
###############################################################################

	@commands.group(
		name='embed',
		usage="Syntax: embed [subcommand] <args>\nExample: embed create welcome",
		extras={'permissions': ['Manage Messages']},
		invoke_without_command=True
	)
	@commands.has_guild_permissions(manage_messages=True)
	async def embed_group(self, ctx: Context):
		"""Manage and create new embeds easily"""
		await ctx.send_help(ctx.command)
	
	@embed_group.command(
		name='create',
		usage="Syntax: embed create <name>\nExample: embed create welcome",
		extras={'permissions': ['Manage Messages']}
	)
	async def create_embed(self, ctx: Context, name: Optional[str]):
		"""Manage and create new embeds easily"""
		try:
			if not name:
				await ctx.send_help(ctx.command)
				return
			embed = discord.Embed(
				description=f"{DEFAULT_DESCRIPTION.format(name=name)}",
				color=DEFAULT_COLOR
			)
			embed.set_author(name=DEFAULT_AUTHOR_TEXT)
			view = EmbedView(ctx, name)
			await ctx.send(embed, view=view)
		except Exception as e:
			log.error(f"An error occurred in {self.qualified_name}: {e}")
			await ctx.error(f"An error occurred in create_embed: {e}")

	@embed_group.command(
		name='preview',
		usage="Syntax: embed preview <name>\nExample: embed preview welcome",
		extras={'permissions': ['Manage Messages']}
	)
	@commands.has_guild_permissions(manage_messages=True)
	async def preview_embed(self, ctx: Context, name: Optional[str]):
		"""Preview an embed"""
		try:
			if not name:
				await ctx.send_help(ctx.command)
				return
			embed = discord.Embed(
				description="This is a preview of the embed you created.",
				color=discord.Color(0x747f8d)
			)
			embed.set_author(name="embed preview")
			await ctx.send(embed)
		except Exception as e:
			log.error(f"An error occurred in {self.qualified_name}: {e}")
			await ctx.error(f"An error occurred: {e}")
