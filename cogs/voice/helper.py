import discord
from logging import getLogger
from .decorators import NotVoiceMember
from typing import Optional, List
from .db import (
	get_custom_voice_channels,
	get_custom_voice_channel,
	transfer_custom_voice_channel
)

logger = getLogger(__name__)

async def helper_lock_channel(guild: discord.Guild, member: discord.Member) -> bool:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		overwrites = discord.PermissionOverwrite(connect=False)
		try:
			await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
			return True
		except Exception as e:
			logger.error(f"Failed to lock channel: {e}")
			return False
		
async def helper_unlock_channel(guild: discord.Guild, member: discord.Member) -> bool:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		overwrites = discord.PermissionOverwrite(connect=None)
		try:
			await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
			return True
		except Exception as e:
			logger.error(f"Failed to unlock channel: {e}")
			return False
		
async def helper_ghost_channel(guild: discord.Guild, member: discord.Member) -> bool:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		overwrites = discord.PermissionOverwrite(view_channel=False, connect=False)
		try:
			await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
			return True
		except Exception as e:
			logger.error(f"Failed to ghost channel: {e}")
			return False
		
async def helper_reveal_channel(guild: discord.Guild, member: discord.Member) -> bool:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		overwrites = discord.PermissionOverwrite(view_channel=None, connect=None)
		try:
			await voice_channel.set_permissions(guild.default_role, overwrite=overwrites)
			return True
		except Exception as e:
			logger.error(f"Failed to unghost channel: {e}")
			return False

		
async def helper_claim_channel(guild: discord.Guild, member: discord.Member) -> Optional[bool]:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			custom_channels = await get_custom_voice_channels(guild)
		except Exception as e:
			logger.error(f"Failed to get custom voice channels: {e}")
			return False
		for custom_channel in custom_channels:
			if custom_channel['channel_id'] == voice_channel.id:
				owner_id = custom_channel['owner_id']
				if owner_id == member.id:
					return False  # user is already the owner
				if owner_id in [member.id for member in voice_channel.members]:
					return None  # owner is still in the voice channel
				else:
					await transfer_custom_voice_channel(voice_channel, member)
					return True
	raise NotVoiceMember("You're not connected to a **voice channel**")

async def helper_disconnect_member(guild: discord.Guild, member: discord.Member) -> Optional[List[discord.Member]]:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			voice_members = voice_channel.members
			return voice_members
		except Exception as e:
			logger.error(f"Failed to disconnect member: {e}")
			return False
	raise NotVoiceMember("You're not connected to a **voice channel**")
		
async def helper_start_activity(guild: discord.Guild, member: discord.Member) -> bool:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			await voice_channel.send("Starting a game...")
			return True
		except Exception as e:
			logger.error(f"Failed to start activity: {e}")
			return False
	raise NotVoiceMember("You're not connected to a **voice channel**")
		
async def helper_view_channel(guild: discord.Guild, member: discord.Member) -> Optional[discord.Embed]:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			custom_channel = await get_custom_voice_channel(voice_channel)
			owner_id = custom_channel['owner_id']
			owner = guild.get_member(owner_id)
			connect_permission = voice_channel.overwrites.get(guild.default_role, discord.PermissionOverwrite()).connect
			visible_permission = voice_channel.overwrites.get(guild.default_role, discord.PermissionOverwrite()).view_channel
			locked_emoji = CHECKED if connect_permission in [False, None] else DENY
			ghosted_emoji = CHECKED if visible_permission is False else DENY
			embed = discord.Embed(
				title=f"{voice_channel.name}",
				color=discord.Color(0x747f8d),
				description=f"**Owner**: {owner.name} (`{owner.id}`)\n"
							f"**Locked**: {locked_emoji}\n"
							f"**Ghosted**: {ghosted_emoji}\n"
							f"**Created**: {discord.utils.format_dt(voice_channel.created_at, 'R')}\n" 
							f"**Bitrate**: {voice_channel.bitrate // 1000} kbps\n"
							f"**Connected**: `{len(voice_channel.members)}`\n"
			)
			if member.avatar:
				avatar_url = member.avatar.url
			else:
				avatar_url = member.default_avatar.url
			embed.set_author(name=member.name, icon_url=avatar_url)
			return embed

		except Exception as e:
			logger.error(f"{type(e)} Failed to view channel: {e}")
			return None
	raise NotVoiceMember("You're not connected to a **voice channel**")
		
async def helper_increase_limit(guild: discord.Guild, member: discord.Member) -> Optional[bool]:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			await voice_channel.edit(user_limit=voice_channel.user_limit + 1)
			return True
		except discord.HTTPException as e:
			return False
		except Exception as e:
			logger.error(f"{type(e)} - Failed to increase limit: {e}")
			return None
	raise NotVoiceMember("You're not connected to a **voice channel**")
		
async def helper_decrease_limit(guild: discord.Guild, member: discord.Member) -> Optional[bool]:
	voice_channels = guild.voice_channels
	voice_channel = discord.utils.get(voice_channels, id=member.voice.channel.id)
	if voice_channel is not None:
		try:
			await voice_channel.edit(user_limit=voice_channel.user_limit - 1)
			return True
		except discord.HTTPException as e:
			return False
		except Exception as e:
			logger.error(f"{type(e)} - Failed to decrease limit: {e}")
			return None
	raise NotVoiceMember("You're not connected to a **voice channel**")
