from discord.ext.commands import CheckFailure, check
from aiomysql import DictCursor

from helpers import Context, get_pool

class LoggingNotInitialized(CheckFailure):
    pass

class LoggingAlreadyInitialized(CheckFailure):
    pass

async def check_presence(guild_id: int) -> bool:
    """Check if there is a logging result in the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM logging WHERE guild_id = %s",
                (guild_id,)
            )
            result = await cur.fetchone()
        return True if result else False

def logging_initialized():
    """Check if logging is initialized."""
    async def predicate(ctx: Context) -> bool:
        result = await check_presence(ctx.guild.id)
        if result:
            return True
        else:
            raise LoggingNotInitialized(
                "Logging is **not initialized**. "
                "Please run `log setup` to initialize logging."
            )
    return check(predicate)

def logging_not_initialized():
    """Check if logging is not initialized."""
    async def predicate(ctx: Context) -> bool:
        result = await check_presence(ctx.guild.id)
        if result:
            raise LoggingAlreadyInitialized(
                "Logging is already **initialized** in this server."
            )
        else:
            return True
    return check(predicate)
