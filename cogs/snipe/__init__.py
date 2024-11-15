async def setup(bot) -> None:
    from .snipe import Snipe
    await bot.add_cog(Snipe(bot))
