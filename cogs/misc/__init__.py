from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .misc import Misc
	try:
		bot.add_cog(Misc(bot))
		logger.info("Misc cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Misc cog: {e}")
