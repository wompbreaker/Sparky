from logging import getLogger

logger = getLogger(__name__)

async def setup(bot):
	from .info import Info
	try:
		await bot.add_cog(Info(bot))
		logger.info("Info cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Info cog: {e}")
		