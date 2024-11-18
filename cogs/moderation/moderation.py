import datetime
import json
import re
import typing
from typing import Literal, Optional, Union
import aiomysql
import discord
from discord.ext import commands, tasks
import asyncio
from bot import Sparky
import logging
from helpers import (
	Emojis,
	Context,
	make_embed_error,
	make_embed_info,
	make_embed_loading,
	make_embed_success,
	make_embed_warning,
	make_embed_lockdown,
	make_embed_add,
	make_embed_remove,
	make_embed_warn,
	return_delta_and_time_dict,
	singular_plural
)
from .views import *

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
	"""Commands for moderation purposes"""

	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			self.periodically_empty_non_jailed_users.start()
			logger.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@property
	def display_emoji(self) -> discord.PartialEmoji:
		return Emojis().get_emoji('discord_employee')
	
#######################################################################################################
#                                       TASKS AND LISTENERS                                           #
#######################################################################################################
						
	def cog_unload(self) -> None:
		self.periodically_empty_non_jailed_users.cancel()

	@tasks.loop(minutes=1)
	async def periodically_empty_non_jailed_users(self):
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute(
						"DELETE FROM jailed_users WHERE is_jailed = %s;",
						(False,)
					)
					await conn.commit()
		except aiomysql.MySQLError as e:
			logger.error(f"MySQL error in {self.qualified_name} periodically_empty_non_jailed_users: {e}")
		except Exception as e:
			logger.error(f"Error in {self.qualified_name} periodically_empty_non_jailed_users: {e}")

	@periodically_empty_non_jailed_users.before_loop
	async def before_empty_non_jailed_users(self):
		await self.bot.wait_until_ready()

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					if message.guild:
						guild_id = message.guild.id
					else:
						return
					if message.author:
						author_id = message.author.id
					await cur.execute(
						"SELECT * FROM silenced_users WHERE guild_id = %s AND member_id = %s;",
						(guild_id, author_id,)
					)
					result = await cur.fetchone()
					if result:
						await message.delete()
		except Exception as e:
			logger.error(f"Error in {self.qualified_name} on_message in guild {message.guild}: {e}")

	@commands.Cog.listener()
	async def on_member_update(self, member_before: discord.Member, member_after: discord.Member):
		try:
			forcenick = await self.get_forcenick(member_after, member_after.guild)
			if isinstance(forcenick, str):
				await member_after.edit(
					nick=forcenick,
					reason="forcenick enabled for this member"
				)

			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(member_after.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jailed_role_id = result['jailed_id']
						member_has_jailed_role_before = member_before.get_role(jailed_role_id)
						member_has_jailed_role_after = member_after.get_role(jailed_role_id)

						# Check if on member update, jailed role was None before and None after OR role before and role after
						if type(member_has_jailed_role_before) == type(member_has_jailed_role_after):
							return

						is_jailed = True if member_has_jailed_role_after else False

						await cur.execute(
							"SELECT * FROM jailed_users WHERE guild_id = %s AND member_id = %s;",
							(member_after.guild.id, member_after.id,)
						)
						result = await cur.fetchone()
						if result:
							await cur.execute(
								"UPDATE jailed_users SET is_jailed = %s WHERE guild_id = %s AND member_id = %s;",
								(is_jailed, member_after.guild.id, member_after.id,)
							)
							await conn.commit()
						else:
							await cur.execute(
								"INSERT INTO jailed_users (guild_id, member_id, is_jailed) VALUES (%s, %s, %s);",
								(member_after.guild.id, member_after.id, is_jailed,)
							)
							await conn.commit()

		except Exception as e:
			logger.error(f"Error in {self.qualified_name} on_member_update: {e}")

	@commands.Cog.listener()
	async def on_member_join(self, member: discord.Member):
		try:
			forcenick = await self.get_forcenick(member, member.guild)
			if isinstance(forcenick, str):
				await member.edit(
					nick=forcenick,
					reason="forcenick enabled for this member"
				)
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(member.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jailed_role_id = result['jailed_id']
						await cur.execute(
							"SELECT * FROM jailed_users WHERE guild_id = %s AND member_id = %s;",
							(member.guild.id, member.id,)
						)
						result = await cur.fetchone()
						if result:
							member_is_jailed = result['is_jailed']
							if member_is_jailed:
								jailed_role = member.guild.get_role(jailed_role_id)
								await member.add_roles(jailed_role)
		except Exception as e:
			logger.error(f"Error in {self.qualified_name} on_member_join: {e}")

#######################################################################################################
#                                       JAIL SYSTEM COMMANDS                                          #
#######################################################################################################

	@commands.command(
		name='setup',
		aliases=['setme', 'setupjail'],
		usage='Syntax: setup',
		extras={'permissions': ['administrator']}
	)
	@commands.bot_has_guild_permissions(manage_roles=True, manage_channels=True)
	@commands.has_guild_permissions(administrator=True)
	@commands.cooldown(1, 10, commands.BucketType.guild)
	async def setup_jailed_perms(self, ctx: Context):
		"""Start process for setting up the moderation system"""

		message = "Working on **moderation setup**..."
		embed = make_embed_loading(ctx.author, message)
		loading_message = await ctx.send(embed)
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jailed_role_id = result['jailed_id']
						jail_channel_id = result['jail_channel_id']
						is_already_setup = True
					else:
						is_already_setup = False
		except Exception as e:
			message = f"An error has occurred while checking the database: {e}"
			embed = make_embed_error(ctx.author, message)
			await loading_message.edit(embed)
			return

		# Check if the server is already setup and if there are jail role and channel
		jailed_role_exists = False
		jail_channel_exists = False
		if is_already_setup:
			for role in ctx.guild.roles:
				if role.id == jailed_role_id:
					jailed_role_exists = True
			for channel in ctx.guild.channels:
				if channel.id == jail_channel_id:
					jail_channel_exists = True

		try:
			# If the server was already setup check if there is a jail role and channel in the server
			if is_already_setup is True:
				if jailed_role_exists:
					jailed_role = ctx.guild.get_role(jailed_role_id)
				else:
					jailed_role = await ctx.guild.create_role(
						name="jailed",
						color=discord.Color.default(),
						hoist=False,
						mentionable=False,
						reason=f"jailed setup role created by {ctx.author}"
					)
				if jail_channel_exists:
					jail_channel = ctx.guild.get_channel(jail_channel_id)
				else:
					jail_channel = await ctx.guild.create_text_channel(
						name="jail",
						nsfw=False,
						slowmode_delay=0
					)
			else:
				# If the server wasn't set up, create the role and the channel
				jailed_role = await ctx.guild.create_role(
					name="jailed",
					color=discord.Color.default(),
					hoist=False,
					mentionable=False,
					reason=f"jailed setup role created by {ctx.author}"
				)
				jail_channel = await ctx.guild.create_text_channel(
					name="jail",
					nsfw=False,
					slowmode_delay=0
				)

			jailed_overwrite = discord.PermissionOverwrite(view_channel=False, send_messages=False, read_message_history=False)
			jailed_perm = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

			# Define the tasks for setting permissions for each role
			for channel in ctx.guild.channels:
				if channel.id != jail_channel.id:
					await self.set_channel_perm(channel, jailed_role, jailed_overwrite)
				else:
					await self.set_channel_perm(channel, jailed_role, jailed_perm)
					default_role = ctx.guild.default_role
					if not isinstance(channel, discord.CategoryChannel):
						existing_permissions = channel.overwrites_for(default_role)
						existing_permissions.update(view_channel=False)
						await channel.set_permissions(default_role, overwrite=existing_permissions)

			# insert or update the database for the new guild
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					if is_already_setup:
						await cur.execute(
							"UPDATE jail_system SET jailed_id = %s, jail_channel_id = %s, is_jailed_setup = %s WHERE guild_id = %s;",
							(jailed_role.id, jail_channel.id, True, ctx.guild.id,)
						)
						await conn.commit()
					else:
						await cur.execute(
							"INSERT INTO jail_system (guild_id, jailed_id, jail_channel_id, is_jailed_setup) VALUES (%s, %s, %s, %s);",
							(ctx.guild.id, jailed_role.id, jail_channel.id, True,)
						)
						await conn.commit()

			message = "**Moderation system set up** has been completed. Please make sure that all of your channels and roles have been configured properly."
			embed = make_embed_success(ctx.author, message)
			await loading_message.edit(embed=embed)

		except Exception as e:
			logger.error(f"An error has occurred in {self.qualified_name} database setup_jailed_perms: {e}")
			message = "An error has occurred while setting up the **jail system**"
			embed = make_embed_error(ctx.author, message)
			await loading_message.edit(embed=embed)

	@commands.command(
			name='jail',
			usage='Syntax: jail <member>\nExample: jail anakin',
			extras={'permissions': ['manage_messages']}
			)
	@commands.bot_has_permissions(manage_roles=True)
	@commands.has_permissions(manage_messages=True)
	async def jail_member(self, ctx: Context, member: Optional[discord.Member]):
		"""Jails the mentioned user"""
		cmd_prefix = await self.bot.bot_prefix(ctx.guild)
		if member is None:
			await ctx.send_help(self.jail_member)
			return

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jailed_role_id = result['jailed_id']
						jailed_role = ctx.guild.get_role(jailed_role_id)
						jail_channel_id = result['jail_channel_id']
						jail_channel = ctx.guild.get_channel(jail_channel_id)
						jail_message = result['jail_msg']
						if not jailed_role:
							jailed_role_exists = False
						else:
							jailed_role_exists = True
						if not jail_channel:
							jail_channel_exists = False
						else:
							jail_channel_exists = True
					else:
						jailed_role_exists = False
						jail_channel_exists = False
		except Exception as e:
			logger.error(f"Error in {self.qualified_name} jail_member: {e}")
			await ctx.error(f"An error has occurred in {self.qualified_name} database jailed check: {e}")
			return

		try:
			if jailed_role_exists is False:
				await ctx.warning(f"No **jailed** role was found, please run the `{cmd_prefix}setup` command first")
				return

			if jail_channel_exists is False:
				await ctx.warning(f"No **jail channel** was found, please run the `{cmd_prefix}setup` command first")
				return

			if member == ctx.guild.me:
				await ctx.send("Nah, I'm not jailing myself")
				return

			if member == ctx.author:
				await ctx.warning("You can't **jail** yourself.")
				return

			if member == ctx.guild.owner:
				await ctx.warning("You can't **jail the owner**.")
				return

			if jailed_role >= ctx.guild.me.top_role:
				await ctx.warning("The **jailed role** is higher than my top role! Please **move it below my top role**.")
				return

			role_check = member.get_role(jailed_role.id)
			if role_check is None:
				await member.add_roles(jailed_role)
			else: 
				await ctx.warning(f"{member.mention} is already **jailed**!")
				return

			await ctx.success(f"Successfully **jailed {member}**")
			await jail_channel.send(f"{member.mention} {jail_message}")
		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} jail_member: {e}")


	@commands.group(
		name='jailmsg',
		usage='Syntax: jailmsg [subcommand] <args>\nExample: jailmsg set we calling the cops on you',
		extras={'permissions': ['manage_guild']},
		invoke_without_command=True
	)
	@commands.has_guild_permissions(manage_guild=True)
	async def jailmsg(self, ctx: Context):
		"""View the jail message for command response"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jail_msg = result['jail_msg']
						is_already_setup = True
					else:
						is_already_setup = False
					if is_already_setup:
						message = f"This guild's jail message: **{jail_msg}**"
						embed = make_embed_info(ctx.author, message)
						await ctx.send(embed)
					else:
						cmd_prefix = await self.bot.bot_prefix(ctx.guild)
						warning_message = f"**Jail system** isn't configured for this server, please run the `{cmd_prefix}setup` command first"
						await ctx.warning(warning_message)
						return
		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} database setup_jailed_perms: {e}")


	@jailmsg.command(
		name='set',
		usage='Syntax: jailmsg set <new jail message>\nExample: jailmsg set we calling the cops on you',
		extras={'permissions': ['manage_guild'], 'parameters': ['new jail message']}
	)
	@commands.has_guild_permissions(manage_guild=True)
	async def set(self, ctx: Context, *, jail_message: typing.Optional[str]):
		"""Set a custom jail message"""
		if jail_message is None:
			await ctx.send_help(self.set)
			return
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						is_already_setup = True
					else:
						is_already_setup = False
					if is_already_setup:
						await cur.execute(
							"UPDATE jail_system SET jail_msg = %s WHERE guild_id = %s;",
							(jail_message, ctx.guild.id,)
						)
						await ctx.success(f"Jail message changed to **{jail_message}**")
					else:
						cmd_prefix = await self.bot.bot_prefix(ctx.guild)
						warning_message = f"**Jail system** isn't configured for this server, please run the `{cmd_prefix}setup` command first"
						await ctx.warning(warning_message)
						return

		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} jailmsg set: {e}")


	@commands.command(\
		name='unjail',
		usage='Syntax: unjail <member>\nExample: unjail anakin',
		extras={'permissions': ['manage_messages']}
	)
	@commands.bot_has_permissions(manage_roles=True)
	@commands.has_permissions(manage_messages=True)
	async def unjail_member(self, ctx: Context, member: Optional[discord.Member]):
		"""Unjails the mentioned user"""
		if member is None:
			await ctx.send_help(self.unjail_member)
			return

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM jail_system WHERE guild_id = %s;",
						(ctx.guild.id,)
					)
					result = await cur.fetchone()
					if result:
						jailed_role_id = result['jailed_id']
						jailed_role = ctx.guild.get_role(jailed_role_id)
						if not jailed_role:
							jailed_role_exists = False
						else:
							jailed_role_exists = True
					else:
						jailed_role_exists = False

		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} database jailed check: {e}")
			return

		try:
			if jailed_role_exists is False:
				cmd_prefix = await self.bot.bot_prefix(ctx.guild)
				warning_message = f"No **jailed** role was found, please run the `{cmd_prefix}setup` command first"
				await ctx.warning(warning_message)
				return

			if jailed_role >= ctx.guild.me.top_role:
				await ctx.warning("The **jailed role** is higher than my top role! Please **move it below my top role**.")
				return

			role_check = member.get_role(jailed_role.id)
			if role_check:
				await member.remove_roles(jailed_role)
			else:
				await ctx.warning(f"{member.mention} isn't **jailed**")
				return
			await ctx.success(f"Successfully **unjailed {member}**")

		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} unjail_member: {e}")


#######################################################################################################
#                                       CHANNEL MANAGEMENT                                            #
#######################################################################################################

	@commands.command(
		name='createchannel', 
		aliases=['cc', 'cchannel'], 
		usage='Syntax: createchannel <channel type> [count]\nExample: createchannel text 5', 
		extras={'permissions': ['manage_channels']}
	)
	@commands.bot_has_guild_permissions(manage_channels=True)
	@commands.has_guild_permissions(manage_channels=True)
	async def create_channel(self, ctx: Context, channel_type: Optional[str], channel_count: typing.Optional[int] = 1):
		"""Creates a channel of specific type. Channel type can be category, forum, stage, text, or voice"""
		if channel_type is None and channel_count == 1:
			await ctx.send_help(self.create_channel)
			return

		if channel_count is not None:
			channel_count = min(max(1, channel_count), 10)

		channel_types = ['category', 'forum', 'stage', 'text', 'voice']

		if channel_type not in channel_types:
			await ctx.warning(f"**{channel_type}** is not a proper channel type.")
			return
		else:
			for batch in range(channel_count):
				coroutines = [self.create_chan(ctx, channel_type) for i in range(channel_count)]
				await asyncio.gather(*coroutines)
				await asyncio.sleep(1)
				await ctx.success(f"Successfully created {channel_count} {channel_type} channels")
				return

	async def create_chan(self, ctx: Context, channel_type: str):
		channel = ''
		try:
			if channel_type == 'category':
				channel = await ctx.guild.create_category_channel("category-channel", reason=f"{ctx.author} ({ctx.author.id}) created this channel")
			elif channel_type == 'forum':
				channel = await ctx.guild.create_forum("forum-channel", reason=f"{ctx.author} ({ctx.author.id}) created this channel")
			elif channel_type == 'stage':
				channel = await ctx.guild.create_stage_channel("stage-channel", reason=f"{ctx.author} ({ctx.author.id}) created this channel")
			elif channel_type == 'text':
				channel = await ctx.guild.create_text_channel("text-channel", reason=f"{ctx.author} ({ctx.author.id}) created this channel")
			elif channel_type == 'voice':
				channel = await ctx.guild.create_voice_channel("voice-channel", reason=f"{ctx.author} ({ctx.author.id}) created this channel")

		except Exception as e:
			await ctx.error(f"Failed to create a channel {e}")
			return

		if not channel:
			await ctx.warning("Failed to create a channel.")
			return

	@commands.group(
		name='lockdown', 
		aliases=['lock'], 
		usage='Syntax: lockdown [channel]\nExample: lockdown #general', 
		extras={'permissions': ['manage_channels']},
		invoke_without_command=True
	)
	@commands.bot_has_permissions(manage_channels=True)
	@commands.has_permissions(manage_channels=True)
	async def lock_channel(self, ctx: Context, channel: Optional[discord.abc.GuildChannel]):
		"""Lockdown a channel"""
		default_role_id = await self.get_lock_role_id(ctx.guild)
		if default_role_id is None:
			default_role = ctx.guild.default_role
		else:
			default_role = ctx.guild.get_role(default_role_id)
			if default_role is None:
				default_role = ctx.guild.default_role

		if channel is None:
			channel = ctx.channel
		try:
			if not isinstance(channel, discord.CategoryChannel):
				existing_permissions = channel.overwrites_for(default_role)
				existing_permissions.update(send_messages=False, send_messages_in_threads=False,
											create_public_threads=False, create_private_threads=False)
				await channel.set_permissions(default_role, overwrite=existing_permissions)
				await ctx.message.add_reaction("🔒")
			else:
				await ctx.warning("You can't lock a category channel")

		except Exception as e:
			logger.error(f"Error in Channel lock_channel: {e}")
			await ctx.message.add_reaction("👎")

	@lock_channel.command(
		name='role',
		usage='Syntax: lockdown role [role]\nExample: lockdown role Member',
		extras={'permissions': ['manage channels']}
	)
	@commands.has_permissions(manage_guild=True)
	async def lock_role(self, ctx: Context, role: Optional[discord.Role]):
		"""Set the default lock role"""
		try:
			if role is None:
				await self.set_lock_role_id(ctx.guild, None)
				await ctx.warning("Removed the **default lock role**")
				return

			await self.set_lock_role_id(ctx.guild, role.id)
			await ctx.success(f"{role.mention} is now set as the **default lock role**")
		except Exception as e:
			await ctx.error(f"An error occurred while setting the lock role: {e}")

	@lock_channel.command(
		name='all',
		usage='Syntax: lockdown all',
		extras={'permissions': ['manage channels']}
	)
	@commands.has_permissions(manage_channels=True)
	@commands.bot_has_permissions(manage_channels=True)
	async def lock_all_channels(self, ctx: Context):
		"""Lock all channels"""
		default_role_id = await self.get_lock_role_id(ctx.guild)
		if default_role_id is None:
			default_role = ctx.guild.default_role
		else:
			default_role = ctx.guild.get_role(default_role_id)
			if default_role is None:
				default_role = ctx.guild.default_role

		ignored_channels = await self.get_ignored_channels(ctx.guild)
		try:
			async with ctx.typing():
				for channel in ctx.guild.channels:
					if not isinstance(channel, discord.CategoryChannel) and channel not in ignored_channels:
						existing_permissions = channel.overwrites_for(default_role)
						existing_permissions.update(send_messages=False, send_messages_in_threads=False,
													create_public_threads=False, create_private_threads=False)
						await channel.set_permissions(default_role, overwrite=existing_permissions)
				cmd_prefix = await self.bot.bot_prefix(ctx.guild)
				message = f"**All channels** locked. Use `{cmd_prefix}unlock all` to remove this lockdown."
				embed = make_embed_lockdown(ctx.author, True, message)
				await ctx.send(embed)
		except Exception as e:
			logger.error(f"Error in Channel lock_all_channels: {e}")
			await ctx.message.add_reaction("👎")

	@lock_channel.group(
		name='ignore',
		usage='Syntax: lock ignore (subcommand) <args>\nExample: lockdown ignore add #announcements',
		extras={'permissions': ['manage guild']},
		invoke_without_command=True
	)
	@commands.has_permissions(manage_guild=True)
	async def lock_ignore(self, ctx: Context):
		"""Blocks a channel from being altered when using the "unlock all" command"""
		await ctx.send_help(self.lock_ignore)
		
	@lock_ignore.command(
		name='add',
		aliases=['create'],
		usage='Syntax: lock ignore add <channel>\nExample: lock ignore add #announcements',
		extras={'permissions': ['manage guild']}
	)
	@commands.has_permissions(manage_guild=True)
	async def lock_ignore_add(self, ctx: Context, channel: Optional[discord.abc.GuildChannel]):
		"""Add a channel to the ignore list"""
		if channel is None:
			await ctx.send_help(self.lock_ignore_add)
			return
		
		try:
			await self.add_ignored_channel(ctx.guild, channel.id)
			await ctx.success(f"{channel.mention} is now an **ignored channel**")
		except Exception as e:
			await ctx.error(f"An error occurred while adding the channel to the ignore list: {e}")
		
	@lock_ignore.command(
		name='remove',
		aliases=['delete', 'del'],
		usage='Syntax: lock ignore remove <channel>\nExample: lock ignore remove #announcements',
		extras={'permissions': ['manage guild']}
	)
	@commands.has_permissions(manage_guild=True)
	async def lock_ignore_remove(self, ctx: Context, channel: Optional[discord.abc.GuildChannel]):
		"""Remove a channel from the ignore list"""
		if channel is None:
			await ctx.send_help(self.lock_ignore_remove)
			return

		try:
			ignored_channels = await self.get_ignored_channels(ctx.guild)
			if channel.id not in ignored_channels:
				await ctx.warning(f"{channel.mention} is not configured as an **ignored channel**")
				return
			await self.remove_ignored_channel(ctx.guild, channel)
			await ctx.success(f"{channel.mention} is no longer an **ignored channel**")
		except Exception as e:
			await ctx.error(f"An error occurred while removing the channel from the ignore list: {e}")

	@lock_ignore.command(
		name='list',
		usage='Syntax: lock ignore list',
		extras={'permissions': ['manage guild']}
	)
	@commands.has_permissions(manage_guild=True)
	async def lock_ignore_list(self, ctx: Context):
		"""View all ignored lockdown channels"""
		try:
			ignored_channels = await self.get_ignored_channels(ctx.guild)
			if not ignored_channels:
				embed = make_embed_info(
					ctx.author, "No **channels** are being ignored during lockdowns"
				)
				await ctx.send(embed)
				return
			channels = [ctx.guild.get_channel(channel_id) for channel_id in ignored_channels]
			view = IgnoredChannelsMenu(IgnoredChannelsPageSource(channels), ctx)
			await view.start()
		except Exception as e:
			await ctx.error(f"An error occurred while listing the ignored channels: {e}")


	@commands.group(
		name='unlock',
		aliases=['unlockdown'],
		usage='Syntax: unlock [channel]\nExample: unlock #general',
		extras={'permissions': ['manage_channels']},
		invoke_without_command=True
	)
	@commands.bot_has_permissions(manage_channels=True)
	@commands.has_permissions(manage_channels=True)
	async def unlock_channel(self, ctx: Context, channel: Optional[discord.TextChannel]):
		"""Unlock a channel"""
		default_role_id = await self.get_lock_role_id(ctx.guild)
		if default_role_id is None:
			default_role = ctx.guild.default_role
		else:
			default_role = ctx.guild.get_role(default_role_id)
			if default_role is None:
				default_role = ctx.guild.default_role
		if channel is None:
			channel = ctx.channel
		try:
			if not isinstance(channel, discord.CategoryChannel):
				existing_permissions = channel.overwrites_for(default_role)
				existing_permissions.update(send_messages=None, send_messages_in_threads=None,
											create_public_threads=None, create_private_threads=None)
				await channel.set_permissions(default_role, overwrite=existing_permissions)
				await ctx.message.add_reaction("🔓")
		except Exception as e:
			logger.error(f"Error in Channel unlock_channel: {e}")
			await ctx.message.add_reaction("👎")

	@unlock_channel.command(
		name='all',
		usage='Syntax: unlock all',
		extras={'permissions': ['manage channels']}
	)
	@commands.bot_has_permissions(manage_channels=True)
	@commands.has_permissions(manage_channels=True, ban_members=True)
	async def unlock_all_channels(self, ctx: Context):
		"""Unlock all channels"""
		default_role_id = await self.get_lock_role_id(ctx.guild)
		if default_role_id is None:
			default_role = ctx.guild.default_role
		else:
			default_role = ctx.guild.get_role(default_role_id)
			if default_role is None:
				default_role = ctx.guild.default_role

		ignored_channels = await self.get_ignored_channels(ctx.guild)
		try:
			async with ctx.typing():
				for channel in ctx.guild.channels:
					if not isinstance(channel, discord.CategoryChannel) and channel.id not in ignored_channels:
						existing_permissions = channel.overwrites_for(default_role)
						existing_permissions.update(send_messages=None, send_messages_in_threads=None,
													create_public_threads=None, create_private_threads=None)
						await channel.set_permissions(default_role, overwrite=existing_permissions)

				message = f"**All channels** unlocked - check permissions if previously hidden."
				embed = make_embed_lockdown(ctx.author, False, message)
				await ctx.send(embed)
		except Exception as e:
			logger.error(f"Error in Channel unlock_all_channels: {e}")
			await ctx.error("An error occurred while unlocking all channels")
		

	@commands.command(
		name='nuke',
		aliases=['clone'],
		usage='Syntax: nuke',
		extras={'permissions': ['administrator & antinuke admin'], 'cooldown': '25'}
	)
	@commands.bot_has_permissions(manage_channels=True)
	@commands.has_permissions(administrator=True)
	@commands.cooldown(1, 25, commands.BucketType.user)
	async def nuke_channel(self, ctx: Context):
		"""Clone the current channel"""
		view = ConfirmView(ctx)
		out = await ctx.warning(
			"Are you sure you want to **nuke** this **channel**?", view=view
		)
		view.response = out

#######################################################################################################
#                                       MODERATION COMMANDS                                           #
#######################################################################################################


	@commands.command(
		name='forcenickname',
		aliases=['fn', 'forcenick', 'freezenick'],
		usage='Syntax: forcenickname <member> (new nickname)\nExample: forcenickname anakin Darth Vader',
		extras={'permissions': ['manage guild & nicknames']}
	)
	@commands.has_guild_permissions(manage_guild=True, manage_nicknames=True)
	@commands.bot_has_guild_permissions(manage_nicknames=True)
	async def force_nickname(self, ctx: Context, member: discord.Member = None, *, new_nickname: typing.Optional[str] = None):
		"""Force change a member's current nickname"""
		# display help embed if command parameters are invalid
		if member is None and new_nickname is None:
			await ctx.send_help(self.force_nickname)
			return

		if member.top_role >= ctx.guild.me.top_role and member != ctx.guild.me:
			warning_message = "I can't **forcenickname** someone who is **equal or higher** than me"
			await ctx.warning(warning_message)
			return

		if member == ctx.guild.owner:
			await ctx.warning("You can't **forcenickname** the **owner**.")
			return

		member_has_forced_nickname = None

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					# Return the forced nicknames for a member in current guild
					await cur.execute(
						"SELECT COUNT(*) AS has_forced_nickname FROM forced_nicknames WHERE guild_id = %s AND member_id = %s;",
						(ctx.guild.id, member.id,)
					)
					count_result = await cur.fetchone()
					has_forced_nickname_count = count_result['has_forced_nickname'] if count_result else 0
					if has_forced_nickname_count == 0:
						member_has_forced_nickname = False
					elif has_forced_nickname_count == 1:
						member_has_forced_nickname = True
					else:
						await cur.execute(
							"DELETE FROM forced_nicknames WHERE guild_id = %s AND member_id = %s;",
							(ctx.guild.id, member.id,)
						)
		except Exception as e:
			await ctx.error(f"An error occurred while trying to count forced_nicknames: {e}")

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					if new_nickname:
						if member_has_forced_nickname:
							# update member's nickname in database and change it
							query = "UPDATE forced_nicknames SET member_nickname = %s WHERE guild_id = %s AND member_id = %s;"
						else:
							# add member's nickname to database and change it
							query = "INSERT INTO forced_nicknames (member_nickname, guild_id, member_id) VALUES (%s, %s, %s);"
						await cur.execute(
							query,
							(new_nickname, ctx.guild.id, member.id,)
						)
						await member.edit(
							nick=new_nickname,
							reason="forcenick enabled for this member"
						)
						await ctx.success(f"Now **forcing nickname** for **{member}**")

					# if new_nickname is None, check if a member has a nick already
					elif new_nickname is None:
						if member.display_name != member.name:
							if member_has_forced_nickname is True:
								# if a member has a nick that is in the database, reset the nick and remove it from the database
								await cur.execute(
									"DELETE FROM forced_nicknames WHERE guild_id = %s AND member_id = %s;",
									(ctx.guild.id, member.id,)
								)
								# remove member's nickname
								await member.edit(
									nick=None,
									reason="locknick reset"
								)
								await ctx.success(f"No longer **forcing nickname** for **{member}**")

							else:
								# if a member has a nick that's not in a database, force the current nickname
								new_nickname = member.display_name
								await cur.execute(
									"INSERT INTO forced_nicknames (member_nickname, guild_id, member_id) VALUES (%s, %s, %s);",
									(new_nickname, ctx.guild.id, member.id,)
								)
								await ctx.success(f"Now **forcing current nickname** for **{member}**")
						else:
							# if a member doesn't have a nickname, logger.error a warning message
							await ctx.warning(f"**{member}** has no nickname set to lock!")
		except Exception as e:
			await ctx.error(f"An error occurred while trying to force a nickname: {e}")

	@commands.group(
		name='purge',
		aliases=['prune', 'c'],
		usage='Syntax: purge [user] <amount>\nExample: purge anakin 10',
		extras={'permissions': ['manage_messages'], 'information': ['Deletes 100 messages by default']},
		invoke_without_command=True
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_messages(self, ctx: Context, member: Optional[discord.Member], message_count: Optional[str] = 100):
		"""Deletes the specified amount of messages from the current channel"""
		# display help embed if command parameters are invalid
		if message_count is None and member is None:
			await ctx.send_help(self.purge_messages)
			return

		def check_member(message: discord.Message):
			return message.author == member

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if member is None:
			deleted = await ctx.channel.purge(limit=message_count+1, bulk=True)
		else:
			deleted = await ctx.channel.purge(limit=message_count+1, check=check_member, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='links',
		usage='Syntax: purge links [amount]\nExample: purge links 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']},
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_links(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages containing links"""
		try:
			message_count = min(int(message_count), 100)
		except ValueError:
			await ctx.error(f"Provided argument **{message_count}** is not a number.")
			return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=self.bot.misc_cog.check_links, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='startswith',
		usage='Syntax: purge startswith <substring> [amount]\nExample: purge startswith https 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']},
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_startswith(self, ctx: Context, substring: str, message_count: Optional[str] = 100):
		"""Purge messages that start with a specific substring"""
		def startswith_check(message: discord.Message):
			return message.content.startswith(substring)

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return
		else:
			message_count = 100

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=startswith_check, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='bots',
		usage='Syntax: purge bots [amount]\nExample: purge bots 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_bots(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages from bots in chat"""
		def is_bot(message: discord.Message):
			return message.author.bot

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:                
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return
		else:
			message_count = 100

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_bot, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='humans',
		usage='Syntax: purge humans [amount]\nExample: purge humans 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_humans(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages from humans in chat"""
		def is_human(message: discord.Message):
			return not message.author.bot

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_human, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='contains',
		usage='Syntax: purge contains <substring> [amount]\nExample: purge contains discord.gg 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_contains(self, ctx: Context, substring: str, message_count: Optional[str] = 100):
		"""Purge messages that contain a specific substring"""
		def contains(message: discord.Message):
			return substring in message.content

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return
		else:
			message_count = 100

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=contains, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='files',
		usage='Syntax: purge files [amount]\nExample: purge files 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_files(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge files/attachments from chat"""
		def is_attachment(message: discord.Message):
			if len(message.attachments) == 0:
				return False
			else:
				return True

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_attachment, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='images',
		usage='Syntax: purge images [amount]\nExample: purge images 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_images(self, ctx: Context, message_count: str = None):
		"""Purge images (including links) from chat"""

		def is_image(message: discord.Message):
			if len(message.attachments) == 0:
				return False
			for attachment in message.attachments:
				if attachment.url.endswith(('.png', '.jpeg', '.jpg', '.gif', '.webp')):
					return True
			return False

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_image, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='reactions',
		usage='Syntax: purge reactions [amount]\nExample: purge reactions 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 reactions by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_reactions(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge reactions from messages in chat"""
		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		async for message in ctx.channel.history(limit=message_count):
			await message.clear_reactions()

	@purge_messages.command(
		name='between',
		usage='Syntax: purge between <start id> <end id>\nExample: purge between 1234567890 1234567899',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages between two message IDs']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_between(self, ctx: Context, start_id: Optional[int], end_id: Optional[int]):
		"""Purge messages between two messages"""
		if start_id is None or end_id is None:
			await ctx.send_help(self.purge_between)
			return

		start_message = await ctx.channel.fetch_message(start_id)
		end_message = await ctx.channel.fetch_message(end_id)
		if start_message is None or end_message is None:
			await ctx.warning("Invalid message ID")
			return

		deleted = await ctx.channel.purge(after=start_message.created_at, before=end_message.created_at, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='endswith',
		usage='Syntax: purge endswith <substring> [amount]\nExample: purge endswith .com 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_endswith(self, ctx: Context, substring: str, message_count: Optional[str] = 100):
		"""Purge messages that end with a specific substring"""
		def endswith_check(message: discord.Message):
			return message.content.endswith(substring)

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return
		else:
			message_count = 100

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=endswith_check, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='stickers',
		usage='Syntax: purge stickers [amount]\nExample: purge stickers 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_stickers(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages containing stickers"""
		def is_sticker(message: discord.Message):
			return len(message.stickers) > 0

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_sticker, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	
	@purge_messages.command(
		name='emoji',
		usage='Syntax: purge emoji [amount]\nExample: purge emoji 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_emoji(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages containing custom emojis"""
		def is_emoji(message: discord.Message):
			custom_emoji_pattern = re.compile(r'<a?:(\w+):(\d+)>')
			return bool(custom_emoji_pattern.search(message.content))

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_emoji, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='mentions',
		usage='Syntax: purge mentions [amount]\nExample: purge mentions 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes 100 messages by default']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_mentions(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages containing mentions"""
		def has_mentions(message: discord.Message):
			return len(message.mentions) > 0

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=has_mentions, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='upto',
		usage='Syntax: purge upto <messagelink>\nExample: purge upto discordapp.com/channels/...',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages up to a message link']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_upto(self, ctx: Context, messagelink: Optional[str]):
		"""Purge messages up to a message link"""
		if messagelink is None:
			await ctx.warning("Missing a **message link** to delete messages up to.")
			return
		
		message_id = messagelink.split('/')[-1]
		try:
			message_id = int(message_id)
		except ValueError:
			await ctx.error("Invalid message link provided.")
			return
		
		message = await ctx.channel.fetch_message(message_id)
		if message is None:
			await ctx.warning("Message not found.")
			return
		
		deleted = await ctx.channel.purge(before=message.created_at, bulk=True)
		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='after',
		usage='Syntax: purge after <messagelink>\nExample: purge after discordapp.com/channels/...',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages after a message link']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_after(self, ctx: Context, messagelink: Optional[str]):
		"""Purge messages after a message link"""
		if messagelink is None:
			await ctx.warning("Missing a **message link** to delete messages after.")
			return
		
		message_id = messagelink.split('/')[-1]
		try:
			message_id = int(message_id)
		except ValueError:
			await ctx.error("Invalid message link provided.")
			return
		
		message = await ctx.channel.fetch_message(message_id)
		if message is None:
			await ctx.warning("Message not found.")
			return
		
		deleted = await ctx.channel.purge(after=message.created_at, bulk=True)
		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='before',
		usage='Syntax: purge before <messagelink>\nExample: purge before discordapp.com/channels/...',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages before a message link']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_before(self, ctx: Context, messagelink: Optional[str]):
		"""Purge messages before a message link"""
		if messagelink is None:
			await ctx.warning("Missing a **message link** to delete messages before.")
			return
		
		message_id = messagelink.split('/')[-1]
		try:
			message_id = int(message_id)
		except ValueError:
			await ctx.error("Invalid message link provided.")
			return
		
		message = await ctx.channel.fetch_message(message_id)
		if message is None:
			await ctx.warning("Message not found.")
			return
		
		deleted = await ctx.channel.purge(before=message.created_at, bulk=True)
		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='webhooks',
		usage='Syntax: purge webhooks [amount]\nExample: purge webhooks 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages by webhooks']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_webhooks(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages from webhooks in chat"""
		def is_webhook(message: discord.Message):
			return message.webhook_id is not None

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=is_webhook, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@purge_messages.command(
		name='embeds',
		usage='Syntax: purge embeds [amount]\nExample: purge embeds 10',
		extras={'permissions': ['manage messages'], 'information': ['Deletes messages with embeds']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
	async def purge_embeds(self, ctx: Context, message_count: Optional[str] = 100):
		"""Purge messages with embeds in chat"""
		def has_embed(message: discord.Message):
			return len(message.embeds) > 0

		if message_count is not None:
			try:
				message_count = min(int(message_count), 100)
			except ValueError:
				await ctx.error(f"Provided argument **{message_count}** is not a number.")
				return

		if message_count > 0:
			await ctx.message.delete()

		deleted = await ctx.channel.purge(limit=message_count, check=has_embed, bulk=True)

		if len(deleted) == 0:
			await ctx.warning("No **messages** could be deleted! (try a bigger search?)")

	@commands.group(
		name='ban',
		usage='Syntax: ban <users> [delete history] [reason]\nExample: ban anakin 3d Threatening staff',
		extras={'permissions': ['ban members'], 'information': ['Bans one or more users from the guild']},
		invoke_without_command=True
	)
	@commands.bot_has_guild_permissions(ban_members=True)
	@commands.has_guild_permissions(ban_members=True)
	async def ban_members(self, ctx: Context, members: commands.Greedy[typing.Union[discord.Member, discord.User]] = None,
						  *, delete_history: typing.Optional[str],
						  reason: typing.Optional[str] = "No reason provided"):
		"""Bans the mentioned user(s) from the guild"""
		# display help embed if command parameters are invalid
		if members is None and delete_history is None and reason == "No reason provided":
			await ctx.send_help(self.ban_members)
			return
		
		if delete_history is None:
			delete_history = await self.get_ban_history(ctx.guild)
			if delete_history is None:
				delete_history = '0s'

		date_time_dict = return_delta_and_time_dict(delete_history)
		if date_time_dict is None:
			await ctx.error("Invalid delete history provided.")
			return
		
		date_time, _, _, _, _ = date_time_dict
		now = datetime.datetime.now(datetime.timezone.utc)
		time_diff = date_time - now
		delete_seconds = time_diff.total_seconds()

		if delete_seconds <= 0 or delete_seconds > 7 * 86400:
			await ctx.error("**Delete history** must be between `0` and `7` days.")
			return
				
		banned_list = []

		for member in members:
			bot_top_role = ctx.guild.me.top_role
			author_top_role = ctx.author.top_role
			if member == ctx.guild.me:
				await ctx.send("Nah, I'm not banning myself")
				continue

			# Check if the command author is a target user
			if member == ctx.author:
				await ctx.warning("You can't **ban** yourself.")
				continue

			if member == ctx.guild.owner:
				warning_message = "You can't **ban the owner**."
				embed = make_embed_warning(ctx.author, warning_message)
				await ctx.warning("You can't **ban the owner**.")
				continue

			if isinstance(member, discord.Member):
				target_top_role = member.top_role

				# Check if the command author is higher ranked than the target user
				if author_top_role <= target_top_role and not ctx.guild.owner:
					await ctx.warning("You can't **ban** someone who is **higher** than you.")
					continue

				# Check if the bot is higher ranked than the target user
				if target_top_role >= bot_top_role:
					await ctx.warning("I can't **ban** someone who is **higher** than me.")
					continue
			try:
				await ctx.guild.ban(member, delete_message_seconds=int(delete_seconds), reason=f"{ctx.author} ({ctx.author.id}): {reason}")
				banned_list.append(member)
			except discord.NotFound:
				await ctx.error("The user with user ID **{member.id}** was not found.")
				continue
			except discord.Forbidden:
				await ctx.error("I **don't have** the permission to ban this user.")
				continue
			except discord.HTTPException as e:
				await ctx.error(f"Failed to **ban** {member.mention}: {e}")
				continue

		if len(banned_list) >= 1:
			banned_string = ""
			for target in banned_list:
				banned_string += f"{target.mention}, "

			await ctx.success(f"Successfully **banned** {banned_string[:-2]}")

	@ban_members.command(
		name='purge',
		usage='Syntax: ban purge <delete history>\nExample: ban purge 1',
		extras={'permissions': ['manage guild & ban members']}
	)
	@commands.has_guild_permissions(manage_guild=True, ban_members=True)
	async def ban_purge(self, ctx: Context, delete_history: Literal['6h', '12h', '24h', '3d', '7d', 'off']):
		"""Set default message history purge upon ban"""
		try:
			if delete_history == 'off':
				message = 'No longer clearing **message history** upon ban'
				delete_history = None
			else:
				amount_string = 'hours' if delete_history.endswith('h') else 'days'
				delete_history_number = delete_history[:-1] if delete_history is not None else 'off'
				message = f"Clearing **message history** up to `{delete_history_number} {amount_string}` upon ban"
			await self.set_ban_history(ctx.guild, delete_history)
			await ctx.success(message)       
		except Exception as e:
			await ctx.error(f"Failed to set **message history** upon ban: {e}") 

	@commands.command(
		name='unban',
		usage='Syntax: unban <user> [reason]\nExample: unban anakin he good now',
		extras={'permissions': ['ban members']}
	)
	@commands.has_guild_permissions(ban_members=True)
	@commands.bot_has_guild_permissions(ban_members=True)
	async def unban(self, ctx: Context, user: discord.User = None, *, reason: typing.Optional[str] = "No reason provided"):
		"""Unbans the mentioned user from the guild"""
		# display help embed if command parameters are invalid
		if user is None and reason == "No reason provided":
			await ctx.send_help(self.unban)
			return

		try:
			entry = await ctx.guild.fetch_ban(user)
			if isinstance(entry, discord.BanEntry):
				try:
					await ctx.guild.unban(user=user, reason=reason)
					await ctx.success(f"Successfully unbanned **{user}**")
				except discord.NotFound:
					await ctx.warning(f"Couldn't find a ban for: **{user}**")
					return
				except discord.HTTPException:
					await ctx.error(f"HTTP: Couldn't find a ban for: **{user}**")
					return
		except discord.NotFound:
			await ctx.warning(f"Couldn't find a ban for: **{user}**")
			return

	@commands.command(
		name='kick',
		usage='Syntax: kick <users> [reason]\nExample: kick anakin too much beefing',
		extras={'permissions': ['kick members'], 'information': ['Kicks one or more users from the guild']}
	)
	@commands.bot_has_guild_permissions(kick_members=True)
	@commands.has_guild_permissions(kick_members=True)
	async def kick(self, ctx: Context, members: commands.Greedy[discord.Member] = None, *,
				   reason: typing.Optional[str] = "No reason provided"):
		"""Kicks the mentioned user(s) from the guild"""
		# display help embed if command parameters are invalid
		if members is None and reason == "No reason provided":
			await ctx.send_help(self.kick)
			return

		kicked_list = []

		for target in members:
			bot_top_role = ctx.guild.me.top_role
			author_top_role = ctx.author.top_role
			# Check if the kick target is a bot itself
			if target == ctx.guild.me:
				await ctx.send("Nah, I'm not kicking myself!")
				continue

			# Check if the command author is a target user
			if target == ctx.author:
				await ctx.warning("You can't **kick** yourself.")
				continue

			if target == ctx.guild.owner:
				await ctx.warning("You can't **kick** **the owner**.")
				continue

			target_top_role = target.top_role

			# Check if the bot is higher ranked than the target user
			if target_top_role >= bot_top_role:
				await ctx.warning("I can't **kick** someone who is **higher** than me.")
				continue

			# Check if the command author is higher ranked than the target user
			if target_top_role >= author_top_role and not ctx.guild.owner:
				await ctx.warning("You can't **kick** someone who is **higher** than you.")
				continue

			try:
				await ctx.guild.kick(target, reason=f"{ctx.author} ({ctx.author.id}): {reason}")

				kicked_list.append(target)
			except discord.Forbidden:
				await ctx.warning(f"Couldn't **kick** {target}")
				continue
			except discord.HTTPException:
				await ctx.warning(f"Failed to **kick** {target}")
				continue

		if len(kicked_list) >= 1:
			kicked_string = ""
			for target in kicked_list:
				kicked_string += f"{target.mention}, "

			await ctx.success(f"Successfully kicked {kicked_string[:-2]}")

	@commands.command(
		name='timeout',
		aliases=['time'],
		usage='Syntax: timeout <users> [duration] [reason]\nExample: timeout anakin 1h30m calm down',
		extras={'permissions': ['moderate members'], 'information': ['Times out one or more users from the guild']} 
	)
	@commands.bot_has_guild_permissions(moderate_members=True)
	@commands.has_guild_permissions(moderate_members=True)
	async def timeout_member(self, ctx: Context, members: commands.Greedy[discord.Member] = None,
							 duration: typing.Optional[str] = '5m', *,
							 reason: typing.Optional[str] = "No reason provided"):
		"""Times out the mentioned user(s) for a specified duration"""
		# display help embed if command parameters are invalid
		if members is None and duration == '5m' and reason == "No reason provided":
			await ctx.send_help(self.timeout_member)
			return

		date_time, dict_keys, dict_values, dict_len, limit = return_delta_and_time_dict(duration)

		if limit is True:
			await ctx.warning("**Duration** cannot exceed **28 days**")
			return

		timeout_list = []
		for target in members:
			# Get bot's, author's and target's top role
			bot_top_role = ctx.guild.me.top_role
			author_top_role = ctx.author.top_role
			target_top_role = target.top_role

			# Check if the timeout target is a bot itself
			if target == ctx.guild.me:
				await ctx.send("Nah, I'm not putting myself on timeout!")
				continue

			# Check if the command author is a target user
			if target == ctx.author:
				await ctx.warning("You can't **timeout** yourself.")
				continue

			if target == ctx.guild.owner:
				await ctx.warning("You can't **timeout** the **owner**.")
				continue

			# Check if the bot is higher ranked than the target user
			if target_top_role >= bot_top_role:
				await ctx.warning("I can't **timeout** someone who is **higher** than me.")
				continue

			# Check if the target has admin perms
			if target.guild_permissions.administrator:
				await ctx.warning("I can't **timeout** someone who has the **Administrator** permission.")
				continue

			# Check if the command author is higher ranked than the target user
			if target_top_role >= author_top_role and not ctx.guild.owner:
				await ctx.warning("You can't **timeout** someone who is **higher** than you.")
				continue

			try:
				await target.timeout(date_time, reason=reason)
				timeout_list.append(target)
			except TypeError:
				await ctx.error("`TypeError`: The **duration** parameter is the wrong type.")
				continue
			except discord.Forbidden:
				await ctx.warning("I can't **timeout** someone who has the **Administrator** permission.")
				continue
			except discord.HTTPException:
				await ctx.error(f"HTTP: Failed to **timeout** {target}")
				continue

		if len(timeout_list) >= 1:
			timeout_string = ""
			for target in timeout_list:
				timeout_string += f"{target.mention}, "

			if dict_len == 1:
				key0 = singular_plural(dict_keys[0], dict_values[0])
				timeout_message = f"{timeout_string[:-2]} timed out for **{dict_values[0]} {key0}**."
				await ctx.success(timeout_message)
			elif dict_len == 2:
				key0 = singular_plural(dict_keys[0], dict_values[0])
				key1 = singular_plural(dict_keys[1], dict_values[1])
				timeout_message = f"{timeout_string} timed out for **{dict_values[0]} {key0} and {dict_values[1]} {key1}**"
				await ctx.success(timeout_message)
			elif dict_len == 3:
				key0 = singular_plural(dict_keys[0], dict_values[0])
				key1 = singular_plural(dict_keys[1], dict_values[1])
				key2 = singular_plural(dict_keys[2], dict_values[2])
				timeout_message = f"{timeout_string} timed out for **{dict_values[0]} {key0}, " \
								  f"{dict_values[1]} {key1} and {dict_values[2]} {key2}**."
				await ctx.success(timeout_message)

	@commands.command(
		name='untimeout',
		aliases=['untime'],
		usage='Syntax: untimeout <users> [reason]\nExample: untimeout anakin my fault',
		extras={'permissions': ['moderate members'], 'information': ['Removes timeout from one or more users']}
	)
	@commands.bot_has_guild_permissions(moderate_members=True)
	@commands.has_guild_permissions(moderate_members=True)
	async def remove_timeout(self, ctx: Context, members: commands.Greedy[discord.Member] = None, *,
							 reason: typing.Optional[str] = "No reason provided"):
		"""Removes timeout from the mentioned user(s)"""
		# check if the command author is a bot
		if ctx.author.bot:
			return

		# display help embed if command parameters are invalid
		if members is None and reason == "No reason provided":
			await ctx.send_help(self.remove_timeout)
			return

		untime_list = []
		not_timed_out_list = []

		for target in members:
			bot_top_role = ctx.guild.me.top_role
			author_top_role = ctx.author.top_role

			if isinstance(target, discord.Member):
				target_top_role = target.top_role

				if target_top_role == bot_top_role:
					await ctx.warning("I can't **remove a timeout** from a member with **equal rank** as mine")
					continue

				if target_top_role > bot_top_role:
					await ctx.warning("I can't **remove a timeout** from a member **higher** than me")
					continue

				if target_top_role > author_top_role and not ctx.guild.owner:
					await ctx.warning("You can't **remove a timeout** from a member **higher** than you")
					continue

			if target.is_timed_out():
				# target is timed out so we can remove the timeout
				try:
					await target.edit(timed_out_until=None, reason=reason)
					untime_list.append(target)
				except discord.Forbidden:
					await ctx.warning(f"Failed to **remove a timeout** from **{target}**.")
					continue
				except discord.HTTPException:
					await ctx.error(f"`HTTPException`: Failed to **remove a timeout** from **{target}**.")
					continue
			else:
				not_timed_out_list.append(target)
				continue

		if len(untime_list) >= 1:
			untime_string = ""
			for target in untime_list:
				untime_string += f"{target.mention}, "
			await ctx.success(f"Successfully **removed a timeout** from {untime_string[:-2]}")

		if len(not_timed_out_list) >= 1:
			untime_string = ""
			for target in not_timed_out_list:
				untime_string += f"{target.mention}, "
			await ctx.warning(f"{untime_string[:-2]} not timed out.")

	# Function to set channel permission
	@staticmethod
	async def set_channel_perm(channel: discord.abc.GuildChannel, role: discord.Role, overwrite: discord.PermissionOverwrite):
		try:
			if not isinstance(channel, discord.CategoryChannel):
				await channel.set_permissions(role, overwrite=overwrite)
		except Exception as e:
			logger.error(f"An error has occurred in setting {role} creation: {e}")


	@commands.command(
		name='stripstaff',
		aliases=['strip'],
		usage='Syntax: stripstaff <members>\nExample: stripstaff anakin',
		extras={'permissions': ['administrator']}
	)
	@commands.bot_has_guild_permissions(manage_roles=True)
	@commands.has_guild_permissions(administrator=True)
	async def strip_staff(self, ctx: Context, member: discord.Member = None):
		"""Strips staff permissions from the mentioned user"""
		# check if the command author is a bot
		if ctx.author.bot:
			return

		# display help embed if command parameters are invalid
		if member is None:
			await ctx.send_help(self.strip_staff)
			return

		# check if a role in member's roles has any of the following perms:
		def check_role_perms(role):
			perm_list = [
				'administrator', 'ban_members', 'deafen_members', 'kick_members', 'manage_channels',
				'manage_emojis', 'manage_emojis_and_stickers', 'manage_events', 'manage_expressions',
				'manage_guild', 'manage_messages', 'manage_nicknames', 'manage_permissions',
				'manage_roles', 'manage_threads', 'manage_webhooks', 'mention_everyone',
				'moderate_members', 'move_members', 'mute_members', 'view_audit_log', 'create_expressions'
			]
			for perm, value in role.permissions:
				if value:  # Check if permission is enabled
					if perm in perm_list:
						return True

		if member:
			if member == ctx.guild.me:
				await ctx.send("*Beep boop ~* I can't strip staff perms from myself")
				return

			if member == ctx.author:
				await ctx.warning("You can't **strip staff perms** from yourself.")
				return

			if member == ctx.guild.owner:
				await ctx.warning("You can't **strip staff perms** from **the owner**.")
				return

			if member.top_role >= ctx.author.top_role:
				await ctx.warning("You can't **strip staff perms** from a member **higher** than you.")
				return

			# If a role from member's roles has staff perms and that role is lower than bot's top role, remove that role
			removed_roles = []
			roles_fail_bot = []
			roles_fail_author = []
			for role in member.roles:
				if check_role_perms(role) and role.name != "@everyone":
					if role >= ctx.guild.me.top_role or role.is_bot_managed():
						roles_fail_bot.append(role)
						continue

					if role >= ctx.author.top_role:
						roles_fail_author.append(role)
						continue

					# try to remove the roles from that member
					try:
						await member.remove_roles(role)
						removed_roles.append(role)
					except discord.Forbidden:
						await ctx.warning("I don't have the permission to remove these roles.")
						continue
					except discord.NotFound as e:
						await ctx.warning(f"An error occurred while removing roles: {e}")
						continue

			if len(roles_fail_bot) > 0 or len(roles_fail_author) > 0:
				failed_string = ""
				for role in roles_fail_bot:
					failed_string += f"{role.mention}, "
				for role in roles_fail_author:
					failed_string += f"{role.mention}, "
				await ctx.error(f"Failed to remove {failed_string[:-2]}, user hasn't been stripped completely.")
				return

			if len(removed_roles) > 0:
				success_message = f"Successfully stripped staff perms from {member.mention}"
				embed = make_embed_remove(ctx.author, success_message)
				await ctx.send(embed)
			else:
				await ctx.warning(f"No staff perms found in {member.mention}'s roles.")
		else:
			await ctx.error("No member found.")

	@commands.group(
		name='role', 
		aliases=['r'],
		usage='Syntax: role <members> <role name>\nExample: role anakin mod',
		extras={'permissions': ['manage roles']},
		invoke_without_command=True)
	@commands.bot_has_guild_permissions(manage_roles=True)
	@commands.has_guild_permissions(manage_roles=True)
	async def assign_role(self, ctx: Context, members: commands.Greedy[discord.Member] = None, *, role_name: str = None):
		"""Assigns a role to the mentioned user(s)"""
		# check if the command author is a bot
		if ctx.author.bot:
			return

		# display help embed if command parameters are invalid
		if members is None and role_name is None:
			await ctx.send_help(self.assign_role)
			return
		if members is None:
			await ctx.warning("Missing a **role** to **add/remove to/from** member")
			return

		guild_roles = ctx.guild.roles
		try:
			role = await commands.RoleConverter().convert(ctx, role_name)
		except commands.RoleNotFound:
			roles_containing_target_name = []
			for role in guild_roles:
				if role_name.lower() in role.name.lower():
					roles_containing_target_name.append(role)
			if len(roles_containing_target_name) == 0:
				await ctx.warning(f"I was unable to find a role with the name: **{role_name}**")
				return
			target_role_name = roles_containing_target_name[0].name
			try:
				role = await commands.RoleConverter().convert(ctx, target_role_name)
			except commands.RoleNotFound:
				await ctx.warning(f"I was unable to find a role with the name: **{role_name}**")
				return
		except TypeError:
			await ctx.warning("Missing a **role** to **add/remove to/from** member")
			return

		# check if the role is in guild roles
		if role not in guild_roles:
			await ctx.warning(f"I was unable to find a role with the name: **{role}**")
			return

		# Check if the role is assignable
		if not role.is_assignable():
			await ctx.warning(f"{role.mention} role **isn't assignable**.")
			return

		# check if bot's top role is higher than target role
		if role >= ctx.guild.me.top_role:
			await ctx.warning(f"**{role}** is above my **role** - please drag mine above!")
			return

		# check if author's top role is higher than target role
		if role >= ctx.author.top_role and not ctx.guild.owner.id:
			await ctx.warning(f"{role.mention} is **too high** for you to manage")
			return

		added_list = []
		removed_list = []

		for member in members:
			role_check = member.get_role(role.id)
			# check if a member already has that role
			if role_check is None:  # means the member doesn't have that role
				try:
					if role < ctx.author.top_role or ctx.author == ctx.guild.owner:
						await member.add_roles(role)
						added_list.append(member)
					continue
				except discord.Forbidden:
					await ctx.warning(f"Forbidden to give role {role.mention} to {member.mention}")
					continue
				except discord.HTTPException:
					await ctx.error(f"HTTPException while trying to give role {role.mention} to {member.mention}")
					continue
			else:  # means the member already has that role, and it should be removed
				try:
					if role < ctx.author.top_role or ctx.author == ctx.guild.owner:
						await member.remove_roles(role)
						removed_list.append(member)
					continue
				except discord.Forbidden:
					await ctx.warning(f"Forbidden to remove role {role.mention} from {member.mention}")
					continue
				except discord.HTTPException:
					await ctx.error(f"HTTPException while trying to remove role {role.mention} from {member.mention}")
					continue

		if len(added_list) >= 1:
			added_string = f""
			for member in added_list:
				added_string += f"{member.mention}, "
			added_string = added_string[:-2]
			success_message = f"Added {role.mention} to {added_string}"
			embed = make_embed_add(ctx.author, success_message)
			await ctx.send(embed)

		if len(removed_list) >= 1:
			removed_string = f""
			for member in removed_list:
				removed_string += f"{member.mention}, "
			removed_string = removed_string[:-2]
			success_message = f"Removed {role.mention} from {removed_string}"
			embed = make_embed_remove(ctx.author, success_message)
			await ctx.send(embed)

	@assign_role.command(
		name='create',
		aliases=['make'],
		usage='Syntax: role create <role color> <role name>\nExample: role create #ff0000 staff',
		extras={'permissions': ['manage roles']}
	)
	@commands.bot_has_guild_permissions(manage_roles=True)
	@commands.has_guild_permissions(manage_roles=True)
	async def create_new_role(self, ctx: Context, role_color: Union[discord.Color | str] = None, *, role_name: str = None):
		"""Creates a role with optional color"""
		# check if the command author is a bot
		if ctx.author.bot:
			return

		# display help embed if command parameters are invalid
		if role_name is None and role_color is None:
			await ctx.send_help(self.create_new_role)
			return

		try:
			if role_color is None:
				role_color = discord.Color.default()
			if role_color == 'black':
				role_color = discord.Color(0x000001)
			created_role = await ctx.guild.create_role(name=role_name, color=role_color)
			await ctx.success(f"Successfully created {created_role.mention}")
		except Exception as e:
			await ctx.error(f"Error creating a role: {e}")

	@assign_role.command(
		name='delete',
		aliases=['del'],
		usage='Syntax: role delete <roles>\nExample: role delete staff',
		extras={'permissions': ['manage roles']}
	)
	@commands.bot_has_guild_permissions(manage_roles=True)
	@commands.has_guild_permissions(manage_roles=True)
	async def delete_role(self, ctx: Context, roles: commands.Greedy[discord.Role] = None):
		"""Deletes the mentioned role(s)"""
		# check if the command author is a bot
		if ctx.author.bot:
			return

		# display help embed if command parameters are invalid
		if roles is None:
			await ctx.send_help(self.delete_role)
			return

		for role in roles:
			if role >= ctx.guild.me.top_role:
				await ctx.warning("I can't delete a role higher than my top role.")
				return

			if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
				await ctx.warning("You can't delete a role higher than your top role.")
				return

			if role.is_bot_managed():
				await ctx.warning("I can't delete bot managed roles.")
				return

			try:
				await role.delete()
			except discord.Forbidden:
				await ctx.warning(f"I don't have proper permissions to delete {role.mention}")
				return
			except discord.HTTPException:
				await ctx.error(f"`HTTPException`: Deleting the role {role.mention} failed.")
				return
		await ctx.success("Successfully **deleted** specified roles.")


	@commands.command(
		name='silence',
		aliases=['stfu'],
		usage='Syntax: silence <member>\nExample: silence anakin',
		extras={'permissions': ['moderate members'], 'information': ["Automatically deletes user's messages"]}
	)
	@commands.has_guild_permissions(moderate_members=True)
	@commands.bot_has_permissions(manage_messages=True)
	async def _silence(self, ctx: Context, member: typing.Optional[discord.Member]):
		"""Silences the mentioned user"""
		if member is None:
			await ctx.send_help(self._silence)
			return

		if member == self.bot.user:
			await ctx.send("How do you expect me to do my job if you silence me??")
			return
		try:
			# Check the database if the member is already silenced
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM silenced_users WHERE guild_id = %s AND member_id = %s;",
						(ctx.guild.id, member.id,)
					)
					cur_result = await cur.fetchone()
					if cur_result:
						await ctx.warning(f"{member.mention} is already **silenced**")
						return
					else:
						await cur.execute(
							"INSERT INTO silenced_users (guild_id, member_id) VALUES (%s, %s);",
							(ctx.guild.id, member.id,)
						)
				await conn.commit()
			await ctx.success(f"{member.mention} is being **silenced** from now on")
		except Exception as e:
			await ctx.error(f"An error has occurred in {self.qualified_name} database silence check: {e}")
			return

	@commands.command(
		name='unsilence',
		aliases=['unstfu'],
		usage='Syntax: unsilence <member>\nExample: unsilence anakin',
		extras={'permissions': ['moderate members']}
	)
	@commands.has_guild_permissions(moderate_members=True)
	async def unsilence(self, ctx: Context, member: typing.Optional[discord.Member]):
		"""Unsilences the mentioned user"""
		if member is None:
			await ctx.send_help(self.unsilence)
			return

		if member == self.bot.user:
			await ctx.send("I was never even silenced lol")
			return

		try:
			# Check the database if the member is already silenced
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM silenced_users WHERE guild_id = %s AND member_id = %s;",
						(ctx.guild.id, member.id,)
					)
					cur_result = await cur.fetchone()
					if cur_result:
						# Delete the member from the database
						await cur.execute(
							"DELETE FROM silenced_users WHERE guild_id = %s AND member_id = %s;",
							(ctx.guild.id, member.id,)
						)
						await ctx.success(f"{member.mention} is no longer being **silenced**")
						return
					else:
						await ctx.warning(f"{member.mention} is not being **silenced**")
		except Exception as e:
			await ctx.error(f"An error has occurred: {e}")

	@commands.command(
		usage='Syntax: warn <member> [reason]\nExample: warn anakin being rude',
		extras={'permissions': ['manage messages']},
	)
	@commands.has_guild_permissions(manage_messages=True)
	async def warn(self, ctx: Context, member: discord.Member, *, reason: Optional[str]):
		"""Warns the mentioned user and private messages them the warning"""
		if reason is None:
			reason = "No reason provided"
		embed = make_embed_warn(ctx.guild, ctx.author, reason)
		dm_channel = await member.create_dm()
		await dm_channel.send(embed=embed)

#######################################################################################################
#                                       MUTE COMMANDS                                                 #
#######################################################################################################


#######################################################################################################
#                                           GETTERS                                                   #
#######################################################################################################

	async def get_forcenick(self, member: discord.Member, guild: discord.Guild) -> typing.Optional[str]:
		"""Get a forced nickname for a member in a guild"""
		async with self.bot.pool.acquire() as conn:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(
					"SELECT * FROM forced_nicknames WHERE guild_id = %s AND member_id = %s;",
					(guild.id, member.id,)
				)
				cur_result = await cur.fetchone()
				if cur_result:
					return cur_result['member_nickname']
				else:
					return None
				
	async def check_lockdown_system(self, guild: discord.Guild):
		"""Check if a guild has a lockdown system, if not, create one"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM lockdown_system WHERE guild_id = %s;",
						(guild.id,)
					)
					cur_result = await cur.fetchone()
					if not cur_result:
						await cur.execute(
							"INSERT INTO lockdown_system (guild_id) VALUES (%s);",
							(guild.id,)
						)
						await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in checking lockdown system: {e}")
				
	async def get_ignored_channels(self, guild: discord.Guild) -> typing.List[int]:
		"""Get ignored channels for a guild"""
		try:
			await self.check_lockdown_system(guild)
			ignored_channels = []
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM lockdown_system WHERE guild_id = %s;",
						(guild.id,)
					)
					cur_result = await cur.fetchone()
					if cur_result:  # JSON
						ignored_channels_json = cur_result['ignored_channels']  # JSON object
						ignored_channels = json.loads(ignored_channels_json)  # list
					return ignored_channels
		except Exception as e:
			logger.error(f"An error has occurred in getting ignored channels: {e}")
			return []
			
	async def add_ignored_channel(self, guild: discord.Guild, channel_id: int):
		"""Add an ignored channel to a guild"""
		try:
			await self.check_lockdown_system(guild)

			ignored_channels = await self.get_ignored_channels(guild)
			ignored_channels.append(channel_id)
			ignored_channels_json = json.dumps(ignored_channels)
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"UPDATE lockdown_system SET ignored_channels = %s WHERE guild_id = %s;",
						(ignored_channels_json, guild.id)
					)
					await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in adding ignored channel: {e}")

	async def remove_ignored_channel(self, guild: discord.Guild, channel_id: int):
		"""Remove an ignored channel from a guild"""
		try:
			await self.check_lockdown_system(guild)

			ignored_channels = await self.get_ignored_channels(guild)
			ignored_channels.remove(channel_id)
			ignored_channels_json = json.dumps(ignored_channels)
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"UPDATE lockdown_system SET ignored_channels = %s WHERE guild_id = %s;",
						(ignored_channels_json, guild.id)
					)
					await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in removing ignored channel: {e}")

	async def get_lock_role_id(self, guild: discord.Guild) -> typing.Optional[int]:
		"""Get a lock role for a guild"""
		try:
			await self.check_lockdown_system(guild)

			lock_role_id = None
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM lockdown_system WHERE guild_id = %s;",
						(guild.id,)
					)
					cur_result = await cur.fetchone()
					if cur_result:
						lock_role_id = cur_result['lock_role_id']
					return lock_role_id
		except Exception as e:
			logger.error(f"An error has occurred in getting lock role: {e}")
			return None
			
	async def set_lock_role_id(self, guild: discord.Guild, role_id: int):
		"""Set a lock role for a guild"""
		try:
			await self.check_lockdown_system(guild)

			# update if role exists, delete if role is None
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"UPDATE lockdown_system SET lock_role_id = %s WHERE guild_id = %s;",
						(role_id, guild.id)
					)
					await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in setting lock role: {e}")

	async def check_ban_system(self, guild: discord.Guild):
		"""Check if a guild has a ban system, if not, create one"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM ban_system WHERE guild_id = %s;",
						(guild.id,)
					)
					cur_result = await cur.fetchone()
					if not cur_result:
						await cur.execute(
							"INSERT INTO ban_system (guild_id) VALUES (%s);",
							(guild.id,)
						)
						await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in checking ban system: {e}")

	async def get_ban_history(self, guild: discord.Guild) -> typing.Optional[str]:
		"""Get a ban history for a guild"""
		try:
			await self.check_ban_system(guild)

			ban_history = None
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM ban_system WHERE guild_id = %s;",
						(guild.id,)
					)
					cur_result = await cur.fetchone()
					if cur_result:
						ban_history = cur_result['default_history']
					return ban_history
		except Exception as e:
			logger.error(f"An error has occurred in getting ban history: {e}")
			return None

	async def set_ban_history(self, guild: discord.Guild, ban_history: str):
		"""Set a ban history for a guild"""
		try:
			await self.check_ban_system(guild)

			# update if role exists, delete if role is None
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(aiomysql.DictCursor) as cur:
					await cur.execute(
						"UPDATE ban_system SET default_history = %s WHERE guild_id = %s;",
						(ban_history, guild.id)
					)
					await conn.commit()
		except Exception as e:
			logger.error(f"An error has occurred in setting ban history: {e}")
