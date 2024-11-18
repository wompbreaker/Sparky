from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .voice import Voicemaster
	try:
		await bot.add_cog(Voicemaster(bot))
		logger.info("Voicemaster cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Voicemaster cog: {e}")
