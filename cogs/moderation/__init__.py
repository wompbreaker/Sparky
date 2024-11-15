async def setup(bot) -> None:
    from .moderation import Moderation
    await bot.add_cog(Moderation(bot))
