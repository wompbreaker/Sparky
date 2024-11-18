from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .ping import Ping
	try:
		await bot.add_cog(Ping(bot))
		logger.info("Ping cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Ping cog: {e}")
