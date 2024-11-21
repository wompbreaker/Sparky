from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .snipe import Snipe
    try:
        await bot.add_cog(Snipe(bot))
        log.info("Snipe cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Snipe cog: {e}")
