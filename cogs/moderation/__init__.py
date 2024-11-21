from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .moderation import Moderation
    try:
        await bot.add_cog(Moderation(bot))
        log.info("Moderation cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Moderation cog: {e}")
