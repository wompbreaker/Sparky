async def setup(bot) -> None:
    from .ping import Ping
    await bot.add_cog(Ping(bot))
