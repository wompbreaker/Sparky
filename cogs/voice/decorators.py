from helpers import Context
from discord.ext import commands
from logging import getLogger
from .db import get_custom_voice_channels

logger = getLogger(__name__)

class NotVoiceMember(commands.CheckFailure):
	pass

class NotVoiceOwner(commands.CheckFailure):
	pass

def is_voice_owner():
	async def predicate(ctx: Context):
		user = ctx.author
		voice_channels = ctx.guild.voice_channels
		if voice_channels:
			try:
				custom_channels = await get_custom_voice_channels(ctx.guild)
			except Exception as e:
				logger.error(f"Failed to get custom voice channels: {e}")
				return False
			for voice_channel in voice_channels:
				if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
					for custom_channel in custom_channels:
						if custom_channel['channel_id'] == voice_channel.id:
							owner_id = custom_channel['owner_id']
							if user.id == owner_id:
								return True
		raise NotVoiceOwner("You don't own a **voice channel**!")
	return commands.check(predicate)

def is_voice_member():
	async def predicate(ctx: Context):
		user = ctx.author
		voice_channels = ctx.guild.voice_channels
		if voice_channels:
			try:
				custom_channels = await get_custom_voice_channels(ctx.guild)
			except Exception as e:
				logger.error(f"Failed to get custom voice channels: {e}")
				return False
			for voice_channel in voice_channels:
				if voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
					if user in voice_channel.members:
						return True
		raise NotVoiceMember("You're not connected to a **voice channel**")
	return commands.check(predicate)
