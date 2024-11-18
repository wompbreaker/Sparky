import aiomysql
import discord
from discord.ext import commands
from bot import Sparky
import logging
from helpers import (
	Context,
	make_embed_info
)
from .db import check_prefix_exists

log = logging.getLogger(__name__)

class Server(commands.Cog):
	"""Commands for server management"""
	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			log.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			log.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@property
	def display_emoji(self) -> discord.PartialEmoji:
		return discord.PartialEmoji(name='\N{GEAR}')

	@commands.group(
		name="prefix",
		usage="Syntax: @Sparky#1871 prefix (subcommand) [args]\nExample: @Sparky#1871 prefix set !",
		invoke_without_command=True
	)
	async def display_prefix(self, ctx: Context):
		"""Display the server prefix"""
		try:
			prefix_exists, prefix = await check_prefix_exists(self.bot.pool, ctx.guild.id)
			
			if prefix_exists:
				embed = make_embed_info(ctx.author, f"**Server prefix**: `{prefix}`")
				await ctx.send(embed)
			else:
				prefix_message = "Your server doesn't have a **prefix set**! Set it using `@Sparky#1871 prefix add <prefix>`"
				lrm = "\u200E"  # Left-To-Right Mark character
				embed = discord.Embed(
					color=discord.Color.from_rgb(109, 161, 203),
					description=f"{lrm}{ctx.author.mention}: {prefix_message}"
				)
				await ctx.send(embed)
		except Exception as e:
			log.error(f"An error occurred in Server display_prefix: {e}")

	@display_prefix.command(
		name='set', 
		aliases=["add"],
		usage="Syntax: @Sparky#1871 prefix set (prefix)\nExample: @Sparky#1871 prefix set !",
		extras={'parameters': ['new_prefix'], 'permissions': ['administrator']}
	)
	@commands.cooldown(1, 5, commands.BucketType.guild)
	@commands.has_guild_permissions(administrator=True)
	async def set_prefix(self, ctx: Context, new_prefix: str = None):
		"""Set a command prefix for the server"""
		# display help embed if command parameters are invalid
		if new_prefix is None:
			await ctx.send_help(self.set_prefix)
			return
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"UPDATE guild_prefixes SET guild_prefix = %s, is_set_prefix = %s WHERE guild_id = %s;",
						(new_prefix, True, ctx.guild.id,)
					)
			await ctx.success(f"**Server prefix** updated to `{new_prefix}`")
		except Exception as e:
			await ctx.error(f"An error occurred: {e}")

	@display_prefix.command(
		name="remove", 
		aliases=["delete", "del", "clear"],
		usage="Syntax: @Sparky#1871 prefix remove\nExample: @Sparky#1871 prefix remove",
		extras={'permissions': ['administrator']}
	)
	@commands.has_guild_permissions(administrator=True)
	async def remove_prefix(self, ctx: Context):
		"""Remove the server prefix"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT is_set_prefix FROM guild_prefixes WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						prefix_exists = result['is_set_prefix']
						if prefix_exists:
							await cur.execute(
								"UPDATE guild_prefixes SET guild_prefix = %s, is_set_prefix = %s WHERE guild_id = %s;",
								(None, False, ctx.guild.id,)
							)
							await ctx.success(f"Your server's prefix has been **removed**. You can set a **new prefix** using `@Sparky#1871 prefix add <prefix>`")
						else:
							await ctx.warning("Your server doesn't have a **prefix set**! Set it using `@Sparky#1871 prefix add <prefix>`")
		except Exception as e:
			await ctx.error(f"An error occurred: {e}")
