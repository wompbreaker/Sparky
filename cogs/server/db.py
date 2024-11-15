from aiomysql import DictCursor, Pool
import logging

logger = logging.getLogger(__name__)

async def check_prefix_exists(pool: Pool, guild_id: int) -> bool:
	try:
		async with pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM guild_prefixes WHERE guild_id = %s;",
					(guild_id,)
				)
				result = await cur.fetchone()
				if result:
					return result['is_set_prefix'], result['guild_prefix']
				return False, None
	except Exception as e:
		logger.error(f"An error occurred in Server display_prefix: {e}")
		return False, None