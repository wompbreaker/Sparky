async def setup(bot) -> None:
    from .voice import Voicemaster
    await bot.add_cog(Voicemaster(bot))
