from logging import getLogger

log = getLogger(__name__)

async def setup(bot) -> None:
    from .fun import Fun
    try:
        await bot.add_cog(Fun(bot))
        log.info("Fun cog is loaded")
    except Exception as e:
        log.error(f"An error occurred while adding the Fun cog: {e}")
