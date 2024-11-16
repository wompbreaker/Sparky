from typing import Optional, List, Tuple, Literal
from aiomysql import DictCursor
import logging
import json
from helpers import get_pool

logger = logging.getLogger(__name__)

__all__ = (
	'init_antinuke_system',
	'deinit_antinuke_system',
	'get_antinuke_setting',
	'get_antinuke_admins',
	'is_antinuke_admin',
	'get_whitelist',
	'is_whitelisted',
	'get_botadd_settings',
	'get_vanity_settings',
	'get_antinuke_parameters',
	'get_permissions_settings',
	'set_antinuke_setting',
	'set_antinuke_parameters',
	'set_permissions_settings',
	'set_vanity_settings'
)

#######################################################################################################
#                                           INITIALIZATION                                            #
#######################################################################################################

async def init_antinuke_system(guild_id: int) -> bool:
	"""Initialize the Antinuke system for a guild
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	bool
		True if the system was initialized successfully, False otherwise
	"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"INSERT INTO antinuke_system (guild_id) VALUES (%s) ON DUPLICATE KEY UPDATE guild_id = guild_id;",
					(guild_id,)
				)
				return True
	except Exception as e:
		logger.error(f"Failed to initialize Antinuke system: {e}")
		return False
	
async def deinit_antinuke_system(guild_id: int) -> bool:
	"""Deinitialize the Antinuke system for a guild
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	bool
		True if the system was deinitialized successfully, False otherwise
	"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"DELETE FROM antinuke_system WHERE guild_id = %s;",
					(guild_id,)
				)
				return True
	except Exception as e:
		logger.error(f"Failed to deinitialize Antinuke system: {e}")
		return False

#######################################################################################################
#                                           GETTERS                                                   #
#######################################################################################################

async def get_antinuke_setting(
	guild_id: int, 
	setting: str
) -> Optional[str]:
	"""Get Antinuke setting from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	setting: str
		The setting to get from the database

	Returns
	-------
	Optional[str]
		The setting value
	"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"SELECT * FROM antinuke_system WHERE guild_id = %s;",
					(guild_id,)
				)
				result = await cur.fetchone()
				return result[setting] if result else None
	except Exception as e:
		logger.error(f"Failed to get Antinuke setting: {e}")
		raise e
	
async def get_antinuke_admins(
	guild_id: int
) -> Optional[List[int]]:
	"""Get Antinuke admins from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	List[int]
		A list of Antinuke admin IDs
	"""
	try:
		admins_json = await get_antinuke_setting(guild_id, 'admins')
	except Exception as e:
		logger.error(f"Failed to get Antinuke admins: {e}")
		raise e
	
	if admins_json is not None:
		return json.loads(admins_json)
	return []

async def is_antinuke_admin(
	guild_id: int, 
	user_id: int
) -> bool:
	"""Check if a user is an Antinuke admin
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	user_id: int
		The user ID

	Returns
	-------
	bool
		True if the user is an Antinuke admin, False otherwise
	"""
	admins = await get_antinuke_admins(guild_id)
	if str(user_id) in admins:
		return True
	return False
	
async def get_whitelist(
	guild_id: int
) -> Optional[List[int]]:
	"""Get whitelisted members from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	List[int]
		A list of whitelisted members
	"""
	try:
		whitelist_json = await get_antinuke_setting(guild_id, 'whitelist')
	except Exception as e:
		logger.error(f"Failed to get Antinuke whitelist: {e}")
		raise e
	if whitelist_json is not None:
		return json.loads(whitelist_json)
	return []

async def is_whitelisted(
	guild_id: int, 
	user_id: int
) -> bool:
	"""Check if a user is whitelisted
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	user_id: int
		The user ID

	Returns
	-------
	bool
		True if the user is whitelisted, False otherwise
	"""
	whitelist = await get_whitelist(guild_id)
	if str(user_id) in whitelist:
		return True
	return False

async def get_botadd_settings(
	guild_id: int
) -> bool:
	"""Get botadd settings from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	bool
		True if botadd is enabled, False otherwise
	"""
	try:
		botadd = await get_antinuke_setting(guild_id, 'botadd')
		return True if botadd == 1 else False
	except Exception as e:
		logger.error(f"Failed to get botadd settings: {e}")
		raise e

async def get_vanity_settings(
	guild_id: int
) -> Tuple[bool, int]:
	"""Get vanity settings from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	Tuple[bool, int]
		enabled, punishment
	"""
	try:
		vanity_json = await get_antinuke_setting(guild_id, 'vanity')
		vanity = json.loads(vanity_json)
		enabled = True if vanity['enabled'] == 1 else False
		punishment = vanity['punishment']
		return enabled, punishment
	except Exception as e:
		logger.error(f"Failed to get vanity settings: {e}")
		raise e
	
async def get_antinuke_parameters(
	guild_id: int, 
	setting: Literal['webhook', 'channel', 'emoji', 'ban', 'kick', 'role']
) -> Tuple[bool, int, int]:
	"""Get Antinuke settings from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	setting: str
		The setting to get

	Returns
	-------
	Tuple[bool, int, int]
		enabled, threshold, punishment
	"""
	try:
		result = await get_antinuke_setting(guild_id, setting)
		result = json.loads(result)
		enabled = True if result['enabled'] == 1 else False
		punishment = result['punishment']
		threshold = result['threshold']
		return enabled, threshold, punishment
	except Exception as e:
		logger.error(f"Failed to get Antinuke settings: {e}")
		raise e
	
	
async def get_permissions_settings(
	guild_id: int
) -> Tuple[bool, List[str], List[str], int]:
	"""Get permissions settings from the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	Returns
	-------
	Tuple[bool, List[str], List[str], int]
		enabled, grant, remove, punishment
	"""
	try:
		permissions_json = await get_antinuke_setting(guild_id, 'perms')
		permissions = json.loads(permissions_json)
		enabled = True if permissions['enabled'] == 1 else False
		grant = permissions['grant']
		remove = permissions['remove']
		punishment = permissions['punishment']
		return enabled, grant, remove, punishment
	except Exception as e:
		logger.error(f"Failed to get permissions settings: {e}")
		raise e
	
#######################################################################################################
#                                           SETTERS                                                   #
#######################################################################################################

async def set_antinuke_setting(
	guild_id: int, 
	setting: str, 
	value: str
) -> bool:
	"""Set Antinuke setting in the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	setting: str
		The setting to set in the database

	value: str
		The value to set for the setting

	Returns
	-------
	bool
		True if the setting was set successfully, False otherwise
	"""
	try:
		pool = await get_pool()
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					f"UPDATE antinuke_system SET {setting} = %s WHERE guild_id = %s;",
					(value, guild_id,)
				)
				return True
	except Exception as e:
		logger.error(f"Failed to set Antinuke setting: {e}")
		return False
	
async def set_antinuke_parameters(
	guild_id: int, 
	setting: Literal['webhook', 'channel', 'emoji', 'ban', 'kick', 'role'], 
	enabled: Optional[bool] = None, 
	threshold: Optional[int] = None, 
	punishment: Optional[int] = None
) -> bool:
	"""Set Antinuke settings in the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	setting: str
		The setting to set in the database

	enabled: Optional[bool]
		The value to set for the enabled setting

	threshold: Optional[int]
		The value to set for the threshold setting

	punishment: Optional[int]
		The value to set for the punishment setting

	Returns
	-------
	bool
		True if the setting was set successfully, False otherwise
	"""
	try:
		current_settings = await get_antinuke_setting(guild_id, setting)
		current_settings = json.loads(current_settings)
		
		if enabled is not None:
			current_settings['enabled'] = 1 if enabled else 0
		if threshold is not None:
			current_settings['threshold'] = threshold
		if punishment is not None:
			current_settings['punishment'] = punishment
		
		value = json.dumps(current_settings)
		return await set_antinuke_setting(guild_id, setting, value)
	except Exception as e:
		logger.error(f"Failed to set Antinuke settings: {e}")
		return False
	
async def set_permissions_settings(
	guild_id: int, 
	enabled: bool, 
	grant: List[str], 
	remove: List[str], 
	punishment: int
) -> bool:
	"""Set permissions settings in the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	enabled: bool
		The value to set for the enabled setting

	grant: List[str]
		The permission to watch for granting

	remove: List[str]
		The permission to watch for removal

	punishment: int
		The punishment to apply

	Returns
	-------
	bool
		True if the setting was set successfully, False otherwise
	"""
	try:
		# get current settings
		current_settings = await get_permissions_settings(guild_id)
		if current_settings is None:
			return False
		current_settings = json.loads(current_settings)

		current_grants: List[str] = current_settings['grant']
		current_removes: List[str] = current_settings['remove']

		# check if the permissions are already in the list and set new values
		for perm in grant:
			if perm not in current_grants:
				current_grants.append(perm)
			else:
				current_grants.remove(perm)
		for perm in remove:
			if perm not in current_removes:
				current_removes.append(perm)
			else:
				current_removes.remove(perm)

		value = {
			'enabled': 1 if enabled else 0,
			'grant': current_grants,
			'remove': current_removes,
			'punishment': punishment
		}
		value = json.dumps(value)
		return await set_antinuke_setting(guild_id, 'permissions', value)
	except Exception as e:
		logger.error(f"Failed to set permissions settings: {e}")
		return False
	
async def set_vanity_settings(
	guild_id: int, 
	enabled: bool, 
	punishment: int
) -> bool:
	"""Set vanity settings in the database
	
	Parameters
	-----------
	guild_id: int
		The guild ID

	enabled: bool
		The value to set for the enabled setting

	punishment: int
		The punishment to apply

	Returns
	-------
	bool
		True if the setting was set successfully, False otherwise
	"""
	try:
		value = {
			'enabled': 1 if enabled else 0,
			'punishment': punishment
		}
		value = json.dumps(value)
		return await set_antinuke_setting(guild_id, 'vanity', value)
	except Exception as e:
		logger.error(f"Failed to set vanity settings: {e}")
		return False
	