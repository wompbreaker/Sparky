from aiomysql import DictCursor
import logging
from typing import Any, Dict, List, Optional
from helpers import get_pool

log = logging.getLogger(__name__)

###############################################################################
#                                           GETTERS                                                   #
############################################################################### 

async def is_unique_tag(guild_id: int, tag: str) -> bool:
	"""Check if a guild has a unique embed tag"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM guild_embeds WHERE guild_id = %s;",
					(guild_id, tag)
				)
				result = await cur.fetchone()
				if result:
					if tag in result['embeds']:
						return False
					else:
						return True
				else:
					return False
	except Exception as e:
		log.error(f"An error occurred in {__name__} is_unique_tag: {e}")
		return False

async def get_embed_component(guild_id: int, tag: str, component: str) -> Optional[Any]:
	"""Get an embed component from the database"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM embed WHERE guild_id = %s AND tag = %s;",
					(guild_id, tag,)
				)
				result = await cur.fetchone()
				if result:
					return result[component]
				else:
					return None
	except Exception as e:
		log.error(f"An error occurred in {__name__} get_embed_component: {e}")
		return None

async def get_embed_components(guild_id: int, tag: str, *components: str):
	"""Get multiple embed components from the database"""
	try:
		component_values = []
		for component in components:
			value = await get_embed_component(guild_id, tag, component)
			if value:
				component_values.append(value)
		if component_values:
			return component_values
		else:
			return None
	except Exception as e:
		log.error(f"An error occurred in {__name__} get_embed_components: {e}")
		return None

async def get_fields(guild_id: int, tag: str) -> Optional[List[Dict]]:
	"""Get embed fields from the database"""
	try:
		fields = await get_embed_component(guild_id, tag, 'fields')
		if fields:
			return fields
		else:
			return None
	except Exception as e:
		log.error(f"An error occurred in {__name__} get_fields: {e}")

async def get_field(guild_id: int, tag: str, field_name: str) -> Optional[Dict]:
	"""Get an embed field from the database"""
	try:
		fields = await get_fields(guild_id, tag)
		if fields:
			for field in fields:
				if field['name'] == field_name:
					return field
		else:
			return None
	except Exception as e:
		log.error(f"An error occurred in {__name__} get_field: {e}")

###############################################################################
#                                           SETTERS                                                   #
############################################################################### 

async def set_embed_component(guild_id: int, tag: str, component: str, value: Any) -> bool:
	"""Set an embed component in the database"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"UPDATE embed SET {component} = %s WHERE guild_id = %s AND tag = %s;",
					(value, guild_id, tag,)
				)
				return True
	except Exception as e:
		log.error(f"An error occurred in {__name__} set_embed_component: {e}")
		return False

async def add_field(guild_id: int, tag: str, field: Dict):
	"""Add an embed field to the database"""
	try:
		fields = await get_fields(guild_id, tag)
		if fields:
			fields.append(field)
		else:
			fields = [field]
		val = await set_embed_component(guild_id, tag, 'fields', fields)
		return val
	except Exception as e:
		log.error(f"An error occurred in {__name__} add_field: {e}")
		return False

async def remove_field(guild_id: int, tag: str, field_name: str):
	"""Remove an embed field from the database"""
	try:
		fields = await get_fields(guild_id, tag)
		if fields:
			for field in fields:
				if field['name'] == field_name:
					fields.remove(field)
					val = await set_embed_component(guild_id, tag, 'fields', fields)
					return val
	except Exception as e:
		log.error(f"An error occurred in {__name__} remove_field: {e}")
		return False

async def edit_field(guild_id: int, tag: str, field_name: str, new_field: Dict):
	"""Edit an embed field in the database"""
	try:
		fields = await get_fields(guild_id, tag)
		if fields:
			for field in fields:
				if field['name'] == field_name:
					fields.remove(field)
					fields.append(new_field)
					val = await set_embed_component(guild_id, tag, 'fields', fields)
					return val
	except Exception as e:
		log.error(f"An error occurred in {__name__} edit_field: {e}")
		return False
	