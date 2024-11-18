from logging import getLogger

logger = getLogger(__name__)


async def setup(bot) -> None:
	from .meta import Meta
	try:
		await bot.add_cog(Meta(bot))
		logger.info("Meta cog is loaded")
	except Exception as e:
		logger.error(f"An error occurred while adding the Meta cog: {e}")
