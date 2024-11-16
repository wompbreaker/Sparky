import datetime
import io
import json
from typing import Literal
from datetime import datetime, timedelta
import aiohttp
from aiomysql import DictCursor
import discord
from discord.ext import commands, tasks
import logging
from bot import Sparky
from helpers import (
	Context,
	make_embed_index_not_found,
	make_embed_snipe,
	make_embed_snipe_not_found,
	make_embed_snipe_reaction
)

logger = logging.getLogger(__name__)

class Snipe(commands.Cog):
	"""Commands for sniping deleted and edited messages"""
	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			self.clear_old_snipes.start()

			logger.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@property
	def display_emoji(self) -> discord.PartialEmoji:
		return discord.PartialEmoji(name='\N{LEFT-POINTING MAGNIFYING GLASS}')
	
	def cog_unload(self):
		self.clear_old_snipes.cancel()

	@tasks.loop(minutes=5)
	async def clear_old_snipes(self):
		now = datetime.now()
		cutoff_time = now - timedelta(hours=2)

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				await cur.execute(
					"DELETE FROM deleted_messages WHERE deleted_at < %s;",
					(cutoff_time,)
				)
				await cur.execute(
					"DELETE FROM edited_messages WHERE edited_at < %s;",
					(cutoff_time,)
				)
				await cur.execute(
					"DELETE FROM removed_reactions WHERE removed_at < %s;",
					(cutoff_time,)
				)

	@clear_old_snipes.before_loop
	async def before_clear_old_snipes(self):
		await self.bot.wait_until_ready()  

	@commands.Cog.listener()
	async def on_message_delete(self, message: discord.Message):
		try:
			if not message.author.bot:
				message_json = await self.get_message_info(message, flag='snipe')
				async with self.bot.pool.acquire() as conn:
					async with conn.cursor() as cur:
						# Insert the deleted message into the database
						await cur.execute(
							"INSERT INTO deleted_messages (guild_id, message_channel_id, author_id, message, message_id) VALUES (%s, %s, %s, %s, %s);",
							(message.guild.id, message.channel.id, message.author.id, message_json, message.id,)
						)
		except Exception as e:
			logger.error(f"An error occurred in Snipe on_message_delete: {e}")

	@commands.Cog.listener()
	async def on_message_edit(self, original_message: discord.Message, edited_message: discord.Message):
		if not original_message.author.bot:
			original_message_json = await self.get_message_info(original_message, flag='edit')
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor() as cur:
					# Insert the deleted message into the database
					await cur.execute(
						"INSERT INTO edited_messages (guild_id, message_channel_id, author_id, message, message_id) VALUES (%s, %s, %s, %s, %s);",
						(original_message.guild.id, original_message.channel.id, original_message.author.id, original_message_json, original_message.id,)
					)

	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					await cur.execute(
						"SELECT COUNT(*) AS reaction_count FROM removed_reactions WHERE guild_id = %s AND reaction_channel_id = %s;",
						(payload.guild_id, payload.channel_id,)
					)
					count_result = await cur.fetchone()
					total_reactions = count_result['reaction_count'] if count_result else 0
					if total_reactions > 0:
						await cur.execute(
							"DELETE FROM removed_reactions WHERE guild_id = %s AND reaction_channel_id = %s;",
							(payload.guild_id, payload.channel_id,)
						)
					await cur.execute(
						"INSERT INTO removed_reactions (guild_id, reaction_channel_id, author_id, reaction, message_id) VALUES (%s, %s, %s, %s, %s);",
						(payload.guild_id, payload.channel_id, payload.user_id, payload.emoji.name, payload.message_id)
					)
		except Exception as e:
			logger.error(f"An error occurred in Snipe on_raw_reaction_remove: {e}")

	@commands.command(
		name='snipe', 
		aliases=['s'],
		usage='Syntax: snipe [index]\nExample: snipe 1',
		extras={'information': ['Results expire in 2h']}
	)
	async def snipe_deleted_message(self, ctx: Context, index: int = 0):
		"""Snipe the most recent deleted messages in the channel"""
		
		if index is not None:
			try:
				# ensure the index is a positive integer
				index = int(index)
			except ValueError:
				await ctx.error(f"Provided argument **{index}** is not a number.")
				return

		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					# Return the number of deleted messages from guild
					await cur.execute(
						"SELECT COUNT(*) AS message_count FROM deleted_messages WHERE guild_id = %s AND message_channel_id = %s;",
						(ctx.guild.id, ctx.channel.id,)
					)
					count_result = await cur.fetchone()
					total_messages = count_result['message_count'] if count_result else 0
					if total_messages > 0:
						# Calculate the offset for the nth most recent deleted message
						if index == 0:
							offset = 0
						else:
							offset = index - 1

						# Fetch the nth most recent deleted message in the guild
						await cur.execute(
							"SELECT * FROM deleted_messages WHERE guild_id = %s AND message_channel_id = %s ORDER BY deleted_at DESC LIMIT 1 OFFSET %s;",
							(ctx.guild.id, ctx.channel.id, offset,)
						)
						deleted_message = await cur.fetchone()
						if deleted_message:
							if index == 0:
								index = 1
							deleted_timestamp = deleted_message['deleted_at']
							author_id = deleted_message['author_id']
							message_author = await self.bot.fetch_user(author_id)
							sniped_message_json = deleted_message['message']
							sniped_message = json.loads(sniped_message_json)
							# await ctx.send(f'```json\n{json.dumps(sniped_message, indent=4)}```')
							
							sniped_message_content = sniped_message['content']
							sniped_message_attachments = sniped_message['attachments']
							sniped_message_reference = sniped_message['reference']
							sniped_message_sticker = sniped_message['sticker']

							if sniped_message_sticker:
								sniped_message_attachments = [sniped_message_sticker]

							embed, sniped_message_attachments = make_embed_snipe(
								author=ctx.author, 
								message_content=sniped_message_content, 
								message_attachments=sniped_message_attachments, 
								message_author=message_author, 
								deleted_timestamp=deleted_timestamp, 
								snipe_number=index, 
								total_messages=total_messages, 
								flag=1
							)

							files = []
							if sniped_message_attachments:
								for attachment in sniped_message_attachments:
									try:
										attachment_data = await self.get_data_from_url(attachment['url'])
										file = discord.File(io.BytesIO(attachment_data), attachment['filename'])
										files.append(file)
									except discord.NotFound:
										continue

							if sniped_message_reference:
								message_id = sniped_message_reference['message_id']
								try:
									message_reference = await ctx.fetch_message(message_id)
									await message_reference.reply(embed=embed, mention_author=False, files=files)
								except discord.NotFound:
									await ctx.send(embed, files=files)
							else:
								await ctx.send(embed, files=files)
						else:
							embed = make_embed_index_not_found(ctx.author, index)
							await ctx.send(embed)
					else:
						embed = make_embed_snipe_not_found(ctx.author, 1)
						await ctx.send(embed)
		except Exception as e:
			logger.error(f"An error occurred in Snipe snipe_deleted_message: {e}")
			await ctx.error(f"An error occurred: {e}")

	@commands.command(
		name='editsnipe', 
		aliases=['es', 'esnipe'],
		usage='Syntax: editsnipe [index]\nExample: editsnipe 1',
		extras={'information': ['Results expire in 2h']}
	)
	async def snipe_edited_message(self, ctx: Context, index=0):
		"""Snipe the most recent edited messages in the channel"""
		if index is not None:
			try:
				# ensure the index is a positive integer
				index = int(index)
			except ValueError:
				await ctx.error(f"Provided argument **{index}** is not a number.")
				return

		async with self.bot.pool.acquire() as conn:
			async with conn.cursor(DictCursor) as cur:
				# Return the number of edited messages from guild
				await cur.execute(
					"SELECT COUNT(*) AS message_count FROM edited_messages WHERE guild_id = %s AND message_channel_id = %s;",
					(ctx.guild.id, ctx.channel.id,)
				)
				count_result = await cur.fetchone()
				total_messages = count_result['message_count'] if count_result else 0
				if total_messages > 0:
					# Calculate the offset for the nth most recent deleted message
					if index == 0:
						offset = 0
					else:
						offset = index - 1

					# Fetch the nth most recent deleted message in the guild
					await cur.execute(
						"SELECT * FROM edited_messages WHERE guild_id = %s AND message_channel_id = %s ORDER BY edited_at DESC LIMIT 1 OFFSET %s;",
						(ctx.guild.id, ctx.channel.id, offset,)
					)
					edited_message = await cur.fetchone()
					if edited_message:
						if index == 0:
							index = 1
						edited_timestamp = edited_message['edited_at']
						author_id = edited_message['author_id']
						try:
							message_author = await self.bot.fetch_user(author_id)
						except discord.NotFound:
							logger.error(f"Couldn't find a user")
							return
						except discord.HTTPException:
							logger.error("Failed to fetch the user")
							return
						sniped_message_json = edited_message['message']
						sniped_message = json.loads(sniped_message_json)
						# await ctx.send(f'```json\n{json.dumps(sniped_message, indent=4)}```')
						
						sniped_message_content = sniped_message['content']
						sniped_message_reference = sniped_message['reference']

						embed, _ = make_embed_snipe(
							author=ctx.author, 
							message_content=sniped_message_content, 
							message_attachments=None, 
							message_author=message_author, 
							deleted_timestamp=edited_timestamp, 
							snipe_number=index, 
							total_messages=total_messages, 
							flag=2
						)

						if sniped_message_reference:
							try:
								sniped_message_id = sniped_message_reference['message_id']
								message_reference = await ctx.fetch_message(sniped_message_id)
								await message_reference.reply(embed=embed, mention_author=False)
							except discord.NotFound:
								await ctx.send(embed)
						else:
							await ctx.send(embed)
					else:
						embed = make_embed_index_not_found(ctx.author, index)
						await ctx.send(embed)
				else:
					embed = make_embed_snipe_not_found(ctx.author, 2)
					await ctx.send(embed)

	@commands.command(
		name='reactionsnipe', 
		aliases=['rs'],
		usage='Syntax: reactionsnipe',
		extras={'information': ['Results expire in 2h']}
	)
	async def snipe_reaction(self, ctx: Context):
		"""Snipe the most recent removed reactions in the channel"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					await cur.execute(
						"SELECT * FROM removed_reactions WHERE guild_id = %s AND reaction_channel_id = %s ORDER BY removed_at DESC LIMIT 1;",
						(ctx.guild.id, ctx.channel.id,)
					)
					removed_reaction = await cur.fetchone()
					if removed_reaction:
						removed_timestamp = removed_reaction['removed_at']
						author_id = removed_reaction['author_id']
						try:
							reaction_author = await self.bot.fetch_user(author_id)
						except discord.NotFound:
							logger.error(f"Couldn't find a user")
							return
						except discord.HTTPException:
							logger.error("Failed to fetch the user")
							return
						reaction_name = removed_reaction['reaction']
						message_id = removed_reaction['message_id']
						
						embed = make_embed_snipe_reaction(reaction_name, reaction_author, removed_timestamp)
						
						if message_id:
							try:
								message_reference = await ctx.fetch_message(message_id)
								await message_reference.reply(embed=embed, mention_author=False)
							except discord.NotFound:
								await ctx.send(embed)
						else:
							await ctx.send(embed)
						
					else:
						embed = make_embed_snipe_not_found(ctx.author, 3)
						await ctx.send(embed)
		except Exception as e:
			await ctx.error(f"An error occurred: {e}")

	@commands.command(
		name='clearsnipe', 
		aliases=['cs', 'clearsnipes'],
		usage='Syntax: clearsnipe',
		extras={'permissions': ['manage_messages']}
	)
	@commands.has_permissions(manage_messages=True)
	@commands.cooldown(1, 10, commands.BucketType.user)
	async def snipe_clear(self, ctx: Context):
		"""Clear all results for reactions, edits and messages"""
		try:
			async with self.bot.pool.acquire() as conn:
				async with conn.cursor(DictCursor) as cur:
					await cur.execute(
						"DELETE FROM deleted_messages WHERE guild_id = %s AND message_channel_id = %s;",
						(ctx.guild.id, ctx.channel.id,)
					)
					await cur.execute(
						"DELETE FROM edited_messages WHERE guild_id = %s AND message_channel_id = %s;",
						(ctx.guild.id, ctx.channel.id,)
					)
					await cur.execute(
						"DELETE FROM removed_reactions WHERE guild_id = %s AND reaction_channel_id = %s;",
						(ctx.guild.id, ctx.channel.id,)
					)
			await ctx.message.add_reaction("✅")
		except Exception as e:
			logger.error(f"An error occurred in Snipe snipe_clear: {e}")
			await ctx.message.add_reaction("❌")

	async def get_message_info(self, message: discord.Message, flag: Literal['snipe', 'edit']) -> str:
		attachments = message.attachments if message.attachments else None
		content = message.content if message.content else None
		if flag == 'snipe':
			reference = message.reference if message.reference else None
			message_id = reference.message_id if reference else None
		elif flag == 'edit':
			reference = message
			message_id = message.id if message else None
		sticker = message.stickers[0] if message.stickers else None

		sticker_url2 = f"https://media.discordapp.net/stickers/{sticker.id}.webp?size=1024" if sticker else None

		message_dict = {
			"content": content,
			"attachments": [{"url": attachment.url, "filename": attachment.filename, "spoiler": attachment.is_spoiler()} for attachment in attachments] if attachments else None,
			"reference": {"message_id": message_id} if reference else None,
			"sticker": {"url": sticker_url2} if sticker else None
		}

		message_json = json.dumps(message_dict)
		return message_json

	async def get_data_from_url(self, url: str) -> bytes:
		async with aiohttp.ClientSession() as session:
			async with session.get(url) as resp:
				if resp.status == 200:
					return await resp.read()
				elif resp.status == 404:
					raise discord.NotFound(resp, 'asset not found')
				elif resp.status == 403:
					raise discord.Forbidden(resp, 'cannot retrieve asset')
				else:
					raise discord.HTTPException(resp, 'failed to get asset')

		raise RuntimeError('Unreachable')
