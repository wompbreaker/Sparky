async def setup(bot) -> None:
    from .info import Info
    await bot.add_cog(Info(bot))
