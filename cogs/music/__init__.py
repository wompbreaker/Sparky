from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .music import Music
	try:
		await bot.add_cog(Music(bot))
		logger.info("Music cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Music cog: {e}")
