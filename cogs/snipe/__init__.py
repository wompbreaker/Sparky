from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .snipe import Snipe
	try:
		await bot.add_cog(Snipe(bot))
		logger.info("Snipe cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Snipe cog: {e}")
