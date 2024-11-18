import json
from logging import getLogger
from typing import Any, Dict, List, Optional, Union
from aiomysql import DictCursor
from discord import (
	Guild,
	Member,
	utils,
	TextChannel
)
from helpers import get_pool

log = getLogger(__name__)

async def get_log_property(guild_id: int, property: str) -> Optional[Union[Dict, List]]:
	"""Get log property for a specific guild"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"SELECT {property} FROM logging WHERE guild_id = %s",
					(guild_id,)
				)
				result = await cur.fetchone()
				if result:
					return result[property]
				else:
					return None
	except Exception as e:
		log.error(f"ERROR: Failed to get log property: {e}")
		return None
	
async def get_event_channels(guild_id: int, event: str) -> Union[List[int], Dict[str, List[int]]]:
	"""Get event channels for a specific guild"""
	channel_list = []
	try:
		channels = await get_log_property(guild_id, 'channels')
		if channels is not None:
			if event == 'all':
				channels = json.loads(channels)
				return channels
			if event in channels:
				channels = json.loads(channels)
				channel_list = channels[event]
		return channel_list
	except Exception as e:
		log.error(f"ERROR: Failed to get event channels: {e}")
		return []
	
async def check_duplicate_channel(guild_id: int, channel_id: int, event: str) -> bool:
	"""Check if channel is already being logged"""
	channel_ids = await get_event_channels(guild_id, event)
	if channel_id in channel_ids:
		return True
	else:
		return False
			
async def get_ignored_channels(guild: Guild) -> Optional[List[TextChannel]]:
	"""Get ignored channels for a specific guild"""
	channel_list = []
	try:
		ignored_channels = await get_log_property(guild.id, 'ignored_channels')
		if ignored_channels is not None:
			ignored_channels = json.loads(ignored_channels)
			channel_list = [utils.get(guild.channels, id=channel_id) for channel_id in ignored_channels]
		return channel_list
	except Exception as e:
		log.error(f"ERROR: Failed to get ignored channels: {e}")
		return []
	
async def get_ignored_members(guild: Guild) -> Optional[List[Member]]:
	"""Get ignored members for a specific guild"""
	member_list = []
	try:
		ignored_members = await get_log_property(guild.id, 'ignored_members')
		if ignored_members is not None:
			ignored_members = json.loads(ignored_members)
			member_list = [guild.get_member(member_id) for member_id in ignored_members]
		return member_list				
	except Exception as e:
		log.error(f"ERROR: Failed to get ignored members: {e}")
		return []

#######################################################################################################
#                                           SETTERS                                                   #
#######################################################################################################

async def setup_logging(guild_id: int) -> bool:
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute(
					"INSERT INTO logging (guild_id) VALUES (%s);",
					(guild_id,)
				)
				return True
	except Exception as e:
		log.error(f"ERROR: Failed to setup logging: {e}")
		return False

async def reset_logging(guild_id: int) -> bool:
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor() as cur:
				await cur.execute(
					"DELETE FROM logging WHERE guild_id = %s;",
					(guild_id,)
				)
				return True
	except Exception as e:
		log.error(f"ERROR: Failed to reset logging: {e}")
		return False

async def set_log_property(guild_id: int, property: str, value: Any) -> bool:
	"""Set log property for a specific guild"""
	try:
		val = await get_log_property(guild_id, property)
		pool = await get_pool()
		if val is None:
			async with pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute(
						f"INSERT INTO logging (guild_id, {property}) VALUES (%s, %s);",
						(guild_id, value,)
					)
					return True
		else:
			async with pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute(
						f"UPDATE logging SET {property} = %s WHERE guild_id = %s;",
						(value, guild_id,)
					)
					return True
	except Exception as e:
		log.error(f"ERROR: Failed to set log property: {e}")
		return False
	
async def set_event_channel(guild_id: int, channel_id: int, event: str) -> bool:
	"""Set event channel for a specific guild"""
	try:
		if event == 'all':
			return await add_channel_for_all_events(guild_id, channel_id)
		channel_ids = await get_event_channels(guild_id, event)
		if channel_id not in channel_ids:
			channel_ids.append(channel_id)
			await set_log_property(guild_id, 'channels', json.dumps(channel_ids))
			return True
		else:
			return False
	except Exception as e:
		log.error(f"ERROR: Failed to set event channel: {e}")
		return False
	
async def add_channel_for_all_events(guild_id: int, channel_id: int) -> bool:
	"""Add channel for all events"""
	try:
		channels: Dict[str, List[int]] = await get_event_channels(guild_id, 'all')
		for event in channels:
			if channel_id not in channels[event]:
				channels[event].append(channel_id)
		await set_log_property(guild_id, 'channels', json.dumps(channels))
		return True
	except Exception as e:
		log.error(f"ERROR: Failed to add channel for all events: {e}")
		return False
	