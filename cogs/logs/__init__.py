from logging import getLogger

log = getLogger(__name__)

async def setup(bot):
    from .logs import Logs
    try:
        await bot.add_cog(Logs(bot))
        log.info("Logs cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Logs cog: {e}")
        