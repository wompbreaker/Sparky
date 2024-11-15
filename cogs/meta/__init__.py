async def setup(bot) -> None:
    from .meta import Meta
    await bot.add_cog(Meta(bot))
