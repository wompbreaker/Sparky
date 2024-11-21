from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .music import Music
    try:
        await bot.add_cog(Music(bot))
        log.info("Music cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Music cog: {e}")
