async def setup(bot) -> None:
    from .server import Server
    await bot.add_cog(Server(bot))
