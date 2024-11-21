from logging import getLogger

log = getLogger(__name__)

async def setup(bot):
    from .info import Info
    try:
        await bot.add_cog(Info(bot))
        log.info("Info cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Info cog: {e}")
        