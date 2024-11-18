import asyncio
import os
from typing import Optional, Literal

import discord
from discord.ext import commands

from bot import Sparky
import aiomysql
import logging
from pathlib import Path
from .db import init_prefix, deinit_prefix
from helpers import (
	Emojis,
	Context,
	make_embed_success,
	make_embed_loading
)

logger = logging.getLogger(__name__)

class Admin(commands.Cog):
	"""Commands for the bot owner to manage the bot"""

	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			logger.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@property
	def display_emoji(self) -> discord.PartialEmoji:
		return Emojis().get_emoji('verified_developer')

	@commands.Cog.listener()
	async def on_guild_join(self, guild: discord.Guild):
		blacklisted = False
		# check if blacklist.txt exists, if not, create it
		if not os.path.exists("blacklist.txt"):
			with open("blacklist.txt", "w") as file:
				pass
		with open("blacklist.txt", "r") as file:
			for guild_id in file:
				if guild.id == int(guild_id.strip()):
					blacklisted = True
					await guild.leave()
					logger.info(f"> {guild.name} ({guild.id}) is blacklisted. Left the guild.")
		if not blacklisted:
			await init_prefix(guild.id)

	@commands.Cog.listener()
	async def on_guild_remove(self, guild: discord.Guild):
		await deinit_prefix(guild.id)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def guilds(self, ctx: Context):
		bot_guilds = []
		for guild in self.bot.guilds:
			bot_guilds.append((guild.name, guild.id))
		logger.info(bot_guilds)
		await ctx.send(f"Bot guilds: {bot_guilds}")

	@commands.command(hidden=True)
	@commands.is_owner()
	async def syncantinuke(self, ctx: Context):
		count = 0
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					for guild in self.bot.guilds:
						await cur.execute(
							"SELECT guild_id FROM antinuke_system WHERE guild_id = %s;",
							(guild.id,)
						)
						result = await cur.fetchone()
						if result:
							pass
						else:
							await cur.execute(
								"INSERT INTO antinuke_system (guild_id) VALUES (%s);",
								(guild.id,)
							)
							count += 1
					await ctx.success(f"Finished syncing the antinuke system database table. **{count}** rows affected.")
		except Exception as e:
			await ctx.error(f"Failed to sync the antinuke system database table: {e}")

	@commands.command(aliases=['ig'], hidden=True)
	@commands.is_owner()
	async def inviteguild(self, ctx: Context, guild_id: int):
		try:
			guild = self.bot.get_guild(int(guild_id))
			await ctx.send(f"Guild name: {guild.name} ({guild.id}) \nNumber of channels: {len(guild.channels)}")
			new_channel = await guild.create_text_channel(name='invite')
			invite = await new_channel.create_invite()
			await ctx.send(f"Invite for {guild}: {invite.url}")
			await asyncio.sleep(5)
			await new_channel.delete()
		except Exception as e:
			await ctx.error(f"Failed to create invite for guild with ID {guild_id}: {e}")

	@commands.command(name='botpresence', aliases=['bp', 'bs', 'botstatus'], hidden=True)
	@commands.is_owner()
	async def change_bot_game_status(self, ctx: Context, *, new_status: str):
		try:
			if new_status is None:
				return
			game_name = new_status
			game = discord.Game(name=game_name)
			await self.bot.change_presence(status=discord.Status.idle, activity=game)
			await ctx.success(f"Successfully changed bot status to **{new_status}**")
		except Exception as e:
			await ctx.error(f"Failed to change bot status: {e}")
			
	@commands.command(hidden=True)
	@commands.is_owner()
	async def leave(self, ctx: Context, guild_id: Optional[int]):
		""" Leaves the current guild or guild with specified ID """
		try:
			if guild_id is None:
				guild = ctx.guild
			else:
				guild = self.bot.get_guild(guild_id)

			await guild.leave()
			logger.info(f"Left the guild {guild.name} ({guild.id})")
		except Exception as e:
			logger.error(f"Failed to leave the guild {guild.name} ({guild.id}): {e}")

	@commands.group(aliases=["bl"], hidden=True, invoke_without_command=True)
	@commands.is_owner()
	async def blacklist(self, ctx: Context, guild_id: Optional[int]):
		""" Leaves the current guild or guild with specified ID and blacklists it"""
		try:
			if guild_id is None:
				guild = ctx.guild
				guild_id = guild.id
			else:
				guild = self.bot.get_guild(guild_id)

			if guild:
				logger.info(f"> Left the guild {guild.name} ({guild.id})")
				try:
					if guild in self.bot.guilds:
						await guild.leave()
						await ctx.success(f"Left the guild {guild.name} ({guild.id})")
					with open("blacklist.txt", "a") as file:
						file.write(f"{str(guild_id)}\n")
					logger.info(f"> Blacklisted {guild.name}")

				except Exception as e:
					await ctx.error(f"Failed to blacklist guild with ID : {guild_id}")
			else:
				await ctx.warning("Unknown guild")
		except Exception as e:
			logger.error(f"Error in blacklist: {e}")

	@blacklist.command(hidden=True)
	@commands.is_owner()
	async def remove(self, ctx: Context, guild_id: int):
		""" Removes the current guild or guild with specified ID from the blacklist"""
		count = 0
		try:
			with open('blacklist.txt', 'r') as fr:
				lines = fr.readlines()

				with open('blacklist.txt', 'w') as fw:
					for line in lines:
						if line.strip() == str(guild_id):
							count += 1
						if line.strip('\n') != str(guild_id):
							fw.write(line)
				if count > 0:
					await ctx.success(f"Successfully removed guild with ID **{guild_id}** from the blacklist.")
				else:
					await ctx.warning(f"Server with ID **{guild_id}** wasn't blacklisted.")
		except Exception as e:
			await ctx.error(f"Failed to remove the guild with ID {guild_id} from the blacklist: {e}")
	
	@commands.command(hidden=True)
	@commands.is_owner()
	async def load(self, ctx: Context, *, extension: str):
		"""Loads a single extension with the specified extension name"""
		try:
			category = Path('cogs') / extension.lower()
			await self.bot.load_extension('.'.join(category.parts)) 
		except commands.ExtensionError as e:
			await ctx.error(f"Failed to load cog: **{extension.lower()}**: {e.__class__.__name__}: {e}")
		else:
			await ctx.success(f"Successfully loaded cog: **{extension.lower()}**.")

	@commands.group(hidden=True, invoke_without_command=True)
	@commands.is_owner()
	async def unload(self, ctx: Context, *, extension: str):
		"""Unloads a single cog with the specified extension name"""
		try:
			category = Path('cogs') / extension.lower()
			await self.bot.unload_extension('.'.join(category.parts)) 
			await ctx.success(f"Successfully unloaded cog: **{extension.lower()}**.")
		except Exception as e:
			await ctx.warning(f"Failed to unload cog: **{extension.lower()}**: {e}")

	@unload.command(name='all', hidden=True)
	@commands.is_owner()
	async def unload_all(self, ctx: Context):
		"""Reloads all loaded cogs"""
		admin_filename = "admin"
		misc_filename = "misc"
		embed_filename = "embeds"
		loaded_count = 0
		total_count = 0
		messages = []

		for category in Path('cogs').iterdir():
			if not category.is_dir():
				continue
			elif not (category / '__init__.py').is_file():
				continue
			total_count += 1

		for category in Path('cogs').iterdir():
			if not category.is_dir():
				continue
			elif not (category / '__init__.py').is_file():
				continue
			try:
				await self.bot.unload_extension('.'.join(category.parts)) 
				loaded_count += 1
				messages.append(f"Successfully unloaded **{category.name}** cog.")
			except Exception as e:
				messages.append(f"Failed to unload cog: **{category.name}** cog: {e}")
				logger.error(f"ERROR occurred while unloading {category.name}: {e}")
				continue
		messages.append(f"Successfully unloaded **{loaded_count}/{total_count}** extensions.")
		await ctx.success("\n".join(messages))

	@commands.group(hidden=True, invoke_without_command=True)
	@commands.is_owner()
	async def reload(self, ctx: Context, extension: str):
		"""Reloads a single loaded cog with the specified extension name"""
		try:
			LOADING = Emojis().get_emoji('loading')
			embed = make_embed_loading(ctx.author, f"Reloading {extension}")
			reload_message = await ctx.send(embed)
			category = Path('cogs') / extension.lower()
			await self.reload_or_load_extension('.'.join(category.parts)) 
			message = f"Successfully reloaded cog: **{extension.lower()}**."
			embed = make_embed_success(ctx.author, message)
			await reload_message.edit(embed=embed)
		except Exception as e:
			logger.exception(e)
			await ctx.error(f"Failed to reload cog: **{extension.lower()}**: {e}")

	async def reload_or_load_extension(self, path: str) -> None:
		try:
			await self.bot.reload_extension(path) 
		except commands.ExtensionNotLoaded:
			await self.bot.load_extension(path) 

	@reload.command(name='all', hidden=True)
	@commands.is_owner()
	async def reload_all(self, ctx: Context):
		"""Reloads all loaded cogs"""
		loaded_count = 0
		total_count = 0
		messages = []

		for category in Path('cogs').iterdir():
			if not category.is_dir():
				continue
			elif not (category / '__init__.py').is_file():
				continue
			total_count += 1

		embed = make_embed_loading(ctx.author, "Reloading all extensions")
		reload_message = await ctx.send(embed)
		for category in Path('cogs').iterdir():
			if not category.is_dir():
				continue
			elif not (category / '__init__.py').is_file():
				continue
			try:
				await self.bot.reload_extension('.'.join(category.parts)) 
				loaded_count += 1
				messages.append(f"Successfully reloaded **{category.name}** cog.")
			except Exception as e:
				messages.append(f"Failed to reload cog: **{category.name}** cog: {e}")
				logger.error(f"ERROR occurred while reloading {category.name}: {e}")
				continue

		messages.append(f"Successfully reloaded **{loaded_count}/{total_count}** extensions.")
		embed = make_embed_success(ctx.author, "\n".join(messages))
		await reload_message.edit(embed=embed)

	@commands.command(hidden=True)
	@commands.is_owner()
	async def listcogs(self, ctx: Context):
		"""Lists all loaded cogs"""
		await ctx.send(f"Loaded cogs: {', '.join(sorted(ctx.bot.extensions))}")

	@commands.command(hidden=True)
	@commands.is_owner()
	async def sync(self, ctx: Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
		if not guilds:
			if spec == "~":
				synced = await ctx.bot.tree.sync(guild=ctx.guild)
			elif spec == "*":
				ctx.bot.tree.copy_global_to(guild=ctx.guild)
				synced = await ctx.bot.tree.sync(guild=ctx.guild)
			elif spec == "^":
				ctx.bot.tree.clear_commands(guild=ctx.guild)
				await ctx.bot.tree.sync(guild=ctx.guild)
				synced = []
			else:
				synced = await ctx.bot.tree.sync(guild=None)

			await ctx.success(
				f"Synced **{len(synced)}** commands **{'globally' if spec is None else 'to the current guild.'}**"
			)
			return

		ret = 0
		for guild in guilds:
			try:
				await ctx.bot.tree.sync(guild=guild)
			except discord.HTTPException:
				pass
			else:
				ret += 1

		await ctx.success(f"Synced the tree to {ret}/{len(guilds)}.")

	@commands.command(hidden=True)
	@commands.is_owner()
	async def shutdown(self, ctx: Context):
		"""Shuts down the bot"""
		await ctx.warning("Shutting down...")
		await self.bot.close()

	@commands.group(
		name='sql',
		invoke_without_command=True,
		hidden=True
	)
	@commands.is_owner()
	async def sql(self, ctx: Context):
		"""Run SQL queries"""
		pass

	@sql.command(
		name='execute',
		aliases=['exec'],
		hidden=True
	)
	@commands.is_owner()
	async def sql_execute(self, ctx: Context, *, query: str):
		"""Execute a SQL query"""
		# remove the code block if it exists
		if query.startswith("```sql"):
			query = query[6:]
		if query.endswith("```"):
			query = query[:-3]
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(query)
					result = await cur.fetchall()
			await ctx.success(f"Query executed successfully with result: {result}")
		except Exception as e:
			await ctx.error(f"An error occurred: {e}")
