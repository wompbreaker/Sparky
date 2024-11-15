async def setup(bot) -> None:
    from .mute import Mute
    await bot.add_cog(Mute(bot))
