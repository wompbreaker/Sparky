from aiomysql import DictCursor, Pool
import logging

log = logging.getLogger(__name__)

async def init_prefix(pool: Pool, guild_id: int):
	DEFAULT_PREFIX = ","
	try:
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"INSERT INTO guild_prefixes (guild_id, guild_prefix, is_set_prefix) VALUES (%s, %s, %s);",
					(guild_id, DEFAULT_PREFIX, True,)
				)
	except Exception as e:
		log.error(f"Error in init_prefix: {e}")

async def deinit_prefix(pool: Pool, guild_id: int):
	try:
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"DELETE FROM guild_prefixes WHERE guild_id = %s;",
					(guild_id,)
				)
		log.info(f"deinitialized prefix for guild with ID: {guild_id}")
	except Exception as e:
		log.error(f"Error in deinit_prefix: {e}")
		