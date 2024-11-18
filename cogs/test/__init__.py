from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
	from .test import Test
	try:
		await bot.add_cog(Test(bot))
		log.info("Test cog is loaded")
	except Exception as e:
		log.error(f"Failed to load Test cog: {e}")
