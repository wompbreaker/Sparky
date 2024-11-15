from logging import getLogger

logger = getLogger(__name__)

async def setup(bot):
	from .antinuke import Antinuke
	try:
		await bot.add_cog(Antinuke(bot))
		logger.info("Antinuke cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Antinuke cog: {e}")
		