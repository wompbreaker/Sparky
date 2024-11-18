from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
	from .mute import Mute
	try:
		await bot.add_cog(Mute(bot))
		log.info("Mute cog is loaded")
	except Exception as e:
		log.error(f"Failed to load Mute cog: {e}")
		