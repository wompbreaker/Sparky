from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
	from .meta import Meta
	try:
		await bot.add_cog(Meta(bot))
		log.info("Meta cog is loaded")
	except Exception as e:
		log.error(f"An error occurred while adding the Meta cog: {e}")
