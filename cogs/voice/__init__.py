from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
	from .voice import Voicemaster
	try:
		await bot.add_cog(Voicemaster(bot))
		log.info("Voicemaster cog is loaded")
	except Exception as e:
		log.error(f"Failed to load Voicemaster cog: {e}")
