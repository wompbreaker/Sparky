from logging import getLogger
from typing import List

import discord
from discord.ext import commands

from bot import Sparky

log = getLogger(__name__)

class Music(commands.Cog):
	"""Music controls for your server"""
	
	def __init__(self, bot):
		self.bot: Sparky = bot

	@commands.command(
		name='queue',
		aliases=['q'],
		usage='Syntax: queue\nExample: queue',
	)
	async def queue(self, ctx: commands.Context, *, channel: discord.VoiceChannel):
		"""Queue command"""
		try:
			if ctx.voice_client is not None:
				return await ctx.voice_client.move_to(channel)
			
			await channel.connect()
		except Exception as e:
			log.exception(f"Error: {e}")

	@commands.command()
	async def stop(self, ctx):
		"""Stops and disconnects the bot from voice"""

		await ctx.voice_client.disconnect()
