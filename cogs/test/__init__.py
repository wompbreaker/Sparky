from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .test import Test
	try:
		await bot.add_cog(Test(bot))
		logger.info("Test cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Test cog: {e}")
