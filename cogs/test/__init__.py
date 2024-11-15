async def setup(bot) -> None:
    from .test import Test
    await bot.add_cog(Test(bot))
