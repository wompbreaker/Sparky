from discord.ext import commands
from helpers import Context
from aiomysql import DictCursor

class LoggingNotInitialized(commands.CheckFailure):
	pass

class LoggingAlreadyInitialized(commands.CheckFailure):
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
					raise LoggingNotInitialized
	return commands.check(predicate)

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
					raise LoggingAlreadyInitialized
				else:
					return True
	return commands.check(predicate)
