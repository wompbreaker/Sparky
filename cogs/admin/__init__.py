from logging import getLogger

logger = getLogger(__name__)

async def setup(bot):
	from .admin import Admin
	try:
		await bot.add_cog(Admin(bot))
		logger.info("Admin cog is loaded")
	except Exception as e:
		logger.error(f"Failed to load Admin cog: {e}")
		