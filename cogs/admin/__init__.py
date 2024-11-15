async def setup(bot) -> None:
    from .admin import Admin
    await bot.add_cog(Admin(bot))
