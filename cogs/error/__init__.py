async def setup(bot) -> None:
    from .error import Error
    await bot.add_cog(Error(bot))
