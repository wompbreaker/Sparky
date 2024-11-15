async def setup(bot) -> None:
    from .misc import Misc
    await bot.add_cog(Misc(bot))
