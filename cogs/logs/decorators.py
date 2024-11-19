from discord.ext.commands import CheckFailure, check
from aiomysql import DictCursor

from helpers import Context

class LoggingNotInitialized(CheckFailure):
	pass

class LoggingAlreadyInitialized(CheckFailure):
	pass

def logging_initialized():
	"""Check if logging is initialized"""
	async def predicate(ctx: Context) -> bool:
		async with ctx.bot.pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM logging WHERE guild_id = %s",
					(ctx.guild.id,)
				)
				result = await cur.fetchone()
		if result:
			return True
		else:
			raise LoggingNotInitialized("Logging is **not initialized**. Please run `log setup` to initialize logging.")
	return check(predicate)

def logging_not_initialized():
	"""Check if logging is not initialized"""
	async def predicate(ctx: Context) -> bool:
		async with ctx.bot.pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM logging WHERE guild_id = %s",
					(ctx.guild.id,)
				)
				result = await cur.fetchone()
		if result:
			raise LoggingAlreadyInitialized("Logging is already **initialized** in this server.")
		else:
			return True
	return check(predicate)
