from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
	from .server import Server
	try:
		await bot.add_cog(Server(bot))
		logger.info("Server cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Server cog: {e}")
