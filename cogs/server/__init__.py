from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .server import Server
    try:
        await bot.add_cog(Server(bot))
        log.info("Server cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Server cog: {e}")
