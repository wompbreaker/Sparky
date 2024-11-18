from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
	from .ping import Ping
	try:
		await bot.add_cog(Ping(bot))
		log.info("Ping cog is loaded")
	except Exception as e:
		log.error(f"Failed to load Ping cog: {e}")
