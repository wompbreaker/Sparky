from logging import getLogger

log = getLogger(__name__)

async def setup(bot):
    from .admin import Admin
    try:
        await bot.add_cog(Admin(bot))
        log.info("Admin cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Admin cog: {e}")
        