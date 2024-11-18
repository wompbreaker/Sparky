from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .mute import Mute
	try:
		await bot.add_cog(Mute(bot))
		logger.info("Mute cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Mute cog: {e}")
		