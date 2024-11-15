from logging import getLogger

logger = getLogger(__name__)

async def setup(bot):
	from .logs import Logs
	try:
		await bot.add_cog(Logs(bot))
		logger.info("Logs cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Logs cog: {e}")
		