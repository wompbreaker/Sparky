from logging import getLogger

log = getLogger(__name__)

async def setup(bot):
    from .antinuke import Antinuke
    try:
        await bot.add_cog(Antinuke(bot))
        log.info("Antinuke cog is loaded")
    except Exception as e:
        log.error(f"Failed to load Antinuke cog: {e}")
        