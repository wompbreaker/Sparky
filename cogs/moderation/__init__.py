from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .moderation import Moderation
	try:
		await bot.add_cog(Moderation(bot))
		logger.info("Moderation cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Moderation cog: {e}")
