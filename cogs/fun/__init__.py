from logging import getLogger

logger = getLogger(__name__)

async def setup(bot) -> None:
    from .fun import Fun
    try:
        await bot.add_cog(Fun(bot))
        logger.info("Fun cog is loaded")
    except Exception as e:
        logger.error(f"An error occurred while adding the Fun cog: {e}")
