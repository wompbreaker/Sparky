import json
from aiomysql import DictCursor
from discord import (
	Guild,
	Member,
	VoiceChannel,
	Role,
)
from typing import (
	Dict,
	List,
	Optional,
	Tuple,
)
from helpers import get_pool
from logging import getLogger

log = getLogger(__name__)

__all__ = (
	'get_voicemaster_settings',
	'get_voicemaster_setting',
	'get_category_channel_ids',
	'get_custom_voice_channels',
	'get_users_voice_channel',
	'get_custom_voice_channel',
	'get_custom_voice_channel_role',
	'initialize_voicemaster',
	'reset_voicemaster_settings',
	'set_voicemaster_setting',
	'init_category_channel_ids',
	'set_category_channel_id',
	'insert_custom_voice_channel',
	'delete_custom_voice_channel',
	'set_custom_voice_channel_role',
	'transfer_custom_voice_channel',
)

#######################################################################################################
#                                           GETTERS                                                   #
#######################################################################################################
async def get_voicemaster_settings(
	guild: Guild
) -> Optional[Tuple[int, dict, bool, int, str, str, int]]:
	"""Get Voicemaster settings for the guild from the database"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM voicemaster_system WHERE guild_id = %s;",
					(guild.id,)
				)
				result = await cur.fetchone()
				if result:
					category_channel_ids = result['category_channel_ids']
					interface_channel_id = result['interface_channel_id']
					voice_channel_id = result['voice_channel_id']
					is_setup = result['is_setup']
					default_role_id = result['default_role_id']
					default_name = result['default_name']
					default_region = result['default_region']
					default_bitrate = result['default_bitrate']
					return (
						category_channel_ids,
						interface_channel_id, 
						voice_channel_id, 
						is_setup, 
						default_role_id, 
						default_name, 
						default_region, 
						default_bitrate
					)
				return None
	except Exception as e:
		log.error(f"Failed to get Voicemaster settings: {e}")
		raise e
	
async def get_voicemaster_setting(guild: Guild, setting: str):
	"""Get Voicemaster setting from the database"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"SELECT * FROM voicemaster_system WHERE guild_id = %s;",
					(guild.id,)
				)
				result = await cur.fetchone()
				return result[setting] if result else None
	except Exception as e:
		log.error(f"Failed to get Voicemaster setting: {e}")
		raise e
	
async def get_category_channel_ids(guild: Guild) -> Optional[Tuple[int]]:
	"""Get category channel id for the guild"""
	try:
		try:
			category_channel_ids = await get_voicemaster_setting(guild, "category_channel_ids")
		except Exception as e:
			log.error(f"Failed to get category channel id: {e}")
			raise e
		if category_channel_ids is not None:
			category_channel_ids = json.loads(category_channel_ids)
			return category_channel_ids['custom_id'], category_channel_ids['default_id']
		return None
	except Exception as e:
		log.error(f"Failed to get category channel id: {e}")
		raise e

async def get_custom_voice_channels(guild: Guild) -> List[Dict]:
	"""Get custom voice channels from the database"""
	try:
		custom_channels_json = await get_voicemaster_setting(guild, "custom_channels")
		log.info(f"custom_channels_json: {custom_channels_json}")
		custom_channels: List[Dict] = json.loads(custom_channels_json)
		log.info(f"custom_channels: {custom_channels}")
		return custom_channels
	except Exception as e:
		log.error(f"Failed to get custom voice channels: {e}")
		raise e

async def get_users_voice_channel(user: Member) -> Optional[VoiceChannel]:
	"""Get the voice channel of the user"""
	try:
		voice_channels = user.guild.voice_channels
		try:
			custom_channels = await get_custom_voice_channels(user.guild)
		except Exception as e:
			log.error(f"Failed to get custom voice channels: {e}")
			raise e
		for voice_channel in voice_channels:
			if user in voice_channel.members and voice_channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
				return voice_channel
		return None
	except Exception as e:
		log.error(f"Failed to get user's voice channel: {e}")
		raise e
	
async def get_custom_voice_channel(channel: VoiceChannel) -> Optional[Dict]:
	"""Get a custom voice channel from the database"""
	try:
		try:
			custom_channels = await get_custom_voice_channels(channel.guild)
		except Exception as e:
			log.error(f"Failed to get custom voice channels: {e}")
			raise e
		for custom_channel in custom_channels:
			if custom_channel['channel_id'] == channel.id:
				return custom_channel
		return None
	except Exception as e:
		log.error(f"Failed to get custom voice channel: {e}")
		raise e
	
async def get_custom_voice_channel_role(channel: VoiceChannel) -> Optional[Role]:
	"""Get the role of a custom voice channel"""
	try:
		try:
			custom_channel = await get_custom_voice_channel(channel)
		except Exception as e:
			log.error(f"Failed to get custom voice channel: {e}")
			raise e
		if custom_channel is not None:
			role_id = custom_channel['role_id']
			role = channel.guild.get_role(role_id)
			return role
		return None
	except Exception as e:
		log.error(f"Failed to get custom voice channel role: {e}")
		raise e
	
#######################################################################################################
#                                           SETTERS                                                   #
#######################################################################################################

async def initialize_voicemaster(guild: Guild):
	"""Initialize Voicemaster database settings for the guild"""
	try:
		try:
			result = await get_voicemaster_settings(guild)
		except Exception as e:
			log.error(f"Failed to get Voicemaster settings: {e}")
			return False
		if result is None:
			pool = await get_pool()
			async with pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					await cur.execute(
						"INSERT INTO voicemaster_system "
						"(guild_id, category_channel_ids, interface_channel_id, voice_channel_id, is_setup, "
						"default_role_id, default_name, default_region, default_bitrate, custom_channels) "
						"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
						(guild.id, '[]', None, None, True, None, "{user.name}'s channel", None, 96000, '[]')
					)
					return True
		return False
	except Exception as e:
		log.error(f"Failed to initialize Voicemaster: {e}")
		return False

async def reset_voicemaster_settings(guild: Guild) -> bool:
	"""Reset Voicemaster settings for the guild in the database"""
	try:
		try:
			result = await get_voicemaster_settings(guild)
		except Exception as e:
			log.error(f"Failed to get Voicemaster settings: {e}")
			return False
		if result is not None:
			pool = await get_pool()
			async with pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					await cur.execute(
						"UPDATE voicemaster_system SET "
						"category_channel_ids = %s, interface_channel_id = %s, voice_channel_id = %s, "
						"is_setup = %s, default_role_id = %s, default_name = %s, default_region = %s, "
						"default_bitrate = %s, custom_channels = %s WHERE guild_id = %s;",
						('[]', None, None, False, None, "{user.name}'s channel", None, 96000, '[]', guild.id)
					)
			return True
		return False
	except Exception as e:
		log.error(f"Failed to reset Voicemaster settings: {e}")
		return False
	
async def set_voicemaster_setting(
	guild: Guild, setting: str, value: int
) -> bool:
	"""Set Voicemaster setting in the database"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"UPDATE voicemaster_system SET {setting} = %s WHERE guild_id = %s;",
					(value, guild.id,)
				)
				return True
	except Exception as e:
		log.error(f"Failed to set Voicemaster setting: {e}")
		return False
	
async def init_category_channel_ids(guild: Guild, default_id: int) -> bool:
	"""Initialize category channel ids for the guild"""
	try:
		category_channel_ids = json.dumps({"default_id": default_id, "custom_id": None})
		try:
			val = await set_voicemaster_setting(guild, "category_channel_ids", category_channel_ids)
		except Exception as e:
			log.error(f"Failed to set category channel ids: {e}")
			return False
		if val:
			log.info(f"Initialized category channel ids: {category_channel_ids}")
			return True
		log.error("Failed to initialize category channel ids")
		return False
	except Exception as e:
		log.error(f"Failed to initialize category channel ids: {e}")
		return False
	
async def set_category_channel_id(guild: Guild, category_id: int) -> bool:
	"""Set category channel id for the guild"""
	try:
		try:
			category_channel_ids = await get_voicemaster_setting(guild, "category_channel_ids")
		except Exception as e:
			log.error(f"Failed to get category channel ids: {e}")
			return False
		if category_channel_ids is not None:
			category_channel_ids = json.loads(category_channel_ids)
			category_channel_ids['custom_id'] = category_id
			category_channel_ids = json.dumps(category_channel_ids)
			val = await set_voicemaster_setting(guild, "category_channel_ids", category_channel_ids)
			return val
		return False
	except Exception as e:
		log.error(f"Failed to set category channel id: {e}")
		return False
	
async def insert_custom_voice_channel(
	channel: VoiceChannel, member: Member
) -> bool:
	"""Insert a custom voice channel into the database"""
	try:
		try:
			default_role_id = await get_voicemaster_setting(channel.guild, "default_role_id")
		except Exception as e:
			log.error(f"Failed to get default role: {e}")
			return False
		try:
			custom_channels_json = await get_voicemaster_setting(channel.guild, "custom_channels")
		except Exception as e:
			log.error(f"Failed to get custom channels: {e}")
			return False
		custom_channels: List[Dict] = json.loads(custom_channels_json)
		custom_channels.append(
			{
				"channel_id": channel.id,
				"owner_id": member.id,
				"role_id": default_role_id
			}
		)
		custom_channels_json = json.dumps(custom_channels)
		val = await set_voicemaster_setting(channel.guild, "custom_channels", custom_channels_json)
		return val
	except Exception as e:
		log.error(f"Failed to insert voice channel: {e}")
		return False
	
async def delete_custom_voice_channel(channel: VoiceChannel) -> bool:
	"""Delete a custom voice channel from the database"""
	try:
		try:
			custom_channels = await get_custom_voice_channels(channel.guild)
		except Exception as e:
			log.error(f"Failed to get custom voice channels: {e}")
			return False
		for custom_channel in custom_channels:
			if custom_channel['channel_id'] == channel.id:
				custom_channels.remove(custom_channel)
				custom_channels_json = json.dumps(custom_channels)
				await set_voicemaster_setting(channel.guild, "custom_channels", custom_channels_json)
				return True
		return False
	except Exception as e:
		log.error(f"Failed to delete custom voice channel: {e}")
		return False
	
async def set_custom_voice_channel_role(channel: VoiceChannel, role_id: int) -> bool:
	"""Set the role of a custom voice channel"""
	try:
		try:
			custom_channels = await get_custom_voice_channels(channel.guild)
		except Exception as e:
			log.error(f"Failed to get custom voice channels: {e}")
			return False
		for custom_channel in custom_channels:
			if custom_channel['channel_id'] == channel.id:
				custom_channel['role_id'] = role_id
				custom_channels_json = json.dumps(custom_channels)
				val = await set_voicemaster_setting(channel.guild, "custom_channels", custom_channels_json)
				return val
		return False
	except Exception as e:
		log.error(f"Failed to set custom voice channel role: {e}")
		return False
	
async def transfer_custom_voice_channel(
	channel: VoiceChannel, new_owner: Member
) -> bool:
	"""Transfer ownership of a custom voice channel"""
	try:
		try:
			custom_channels = await get_custom_voice_channels(channel.guild)
		except Exception as e:
			log.error(f"Failed to get custom voice channels: {e}")
			return False
		for custom_channel in custom_channels:
			if custom_channel['channel_id'] == channel.id:
				custom_channel['owner_id'] = new_owner.id
				custom_channels_json = json.dumps(custom_channels)
				val = await set_voicemaster_setting(channel.guild, "custom_channels", custom_channels_json)
				return val
		return False
	except Exception as e:
		log.error(f"Failed to transfer custom voice channel: {e}")
		return False
