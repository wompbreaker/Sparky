from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .misc import Misc
    try:
        await bot.add_cog(Misc(bot))
        log.info("Misc cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Misc cog: {e}")
