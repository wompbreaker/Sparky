from typing import List, Tuple
import re
import discord
from discord.ext import commands
from bot import Sparky
import logging
from helpers import (
	Context,
	make_embed_cooldown
)

logger = logging.getLogger(__name__)

class Error(commands.Cog):
	def __init__(self, bot: Sparky):
		try:
			self.bot: Sparky = bot
			logger.info(f"{self.qualified_name} initialized successfully!")
		except Exception as e:
			logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

	@commands.Cog.listener()
	async def on_command_error(self, ctx: Context, error: commands.CommandError) -> None:
		error_type = type(error).__name__
		cog = ctx.cog.qualified_name if ctx.cog else "No cog"

		# DiscordException -> CommandError -> CommandInvokeError
		if isinstance(error, commands.CommandInvokeError):
			previous_error = error.original  # ExtensionError
			if isinstance(previous_error, commands.ExtensionError):
				# DiscordException -> ExtensionError -> ExtensionAlreadyLoaded
				if isinstance(previous_error, commands.ExtensionAlreadyLoaded):
					error_message = f"Extension [{previous_error.name}] is already loaded"
					logger.error(error_message)

				# DiscordException -> ExtensionError -> ExtensionNotLoaded
				elif isinstance(previous_error, commands.ExtensionNotLoaded):
					error_message = f"Extension [{previous_error.name}] is not loaded"
					logger.error(error_message)

				# DiscordException -> ExtensionError -> NoEntryPointError
				elif isinstance(previous_error, commands.NoEntryPointError):
					error_message = f"Extension [{previous_error.name}] doesn't have a `setup` entry point function"
					logger.error(error_message)

				# DiscordException -> ExtensionError -> ExtensionFailed
				elif isinstance(previous_error, commands.ExtensionFailed):
					error_message = f"Extension [{previous_error.name}]: {previous_error.original}"
					logger.error(error_message)

				# DiscordException -> ExtensionError -> ExtensionNotFound
				elif isinstance(previous_error, commands.ExtensionNotFound):
					error_message = f"Extension [{previous_error.name}] not found"
					logger.error(error_message)

				else:
					error_message = "Unknown Extension error"
					logger.error(error_message)
		elif isinstance(error, commands.UserInputError):
			if isinstance(error, commands.BadArgument):
				# DiscordException -> CommandError -> UserInputError -> BadArgument -> MessageNotFound
				if isinstance(error, commands.MessageNotFound):
					warning_message = "Invalid **message link** provided"
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> MemberNotFound
				elif isinstance(error, commands.MemberNotFound):
					warning_message = f"I was unable to find a member with the name: **{ctx.current_argument}**"
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> GuildNotFound
				elif isinstance(error, commands.GuildNotFound):
					warning_message = f"I was unable to find a guild with the name: **{ctx.current_argument}**"
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> UserNotFound
				elif isinstance(error, commands.UserNotFound):
					warning_message = f"I was unable to find a user with the name: **{ctx.current_argument}**"
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> ChannelNotFound
				elif isinstance(error, commands.ChannelNotFound):
					warning_message = "Could not convert **channel** into `Text Channel, Voice Channel, or Category Channel`"
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> ChannelNotReadable
				elif isinstance(error, commands.ChannelNotReadable):
					warning_message = "Could not **read messages** from the specified **channel**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> BadColourArgument
				elif isinstance(error, commands.BadColourArgument):
					warning_message = f"Color **{ctx.current_argument}** is not valid."
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> RoleNotFound
				elif isinstance(error, commands.RoleNotFound):
					warning_message = f"I was unable to find a role with the name: **{ctx.current_argument}**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> ChannelNotReadable
				elif isinstance(error, commands.BadInviteArgument):
					warning_message = f"{ctx.current_argument} is either an **invalid** or an **expired** invite"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> EmojiNotFound
				elif isinstance(error, commands.EmojiNotFound):
					warning_message = f"I was unable to find an emoji with the name: **{ctx.current_argument}**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> GuildStickerNotFound
				elif isinstance(error, commands.GuildStickerNotFound):
					warning_message = f"I was unable to find a sticker with the name: **{ctx.current_argument}**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> ScheduledEventNotFound
				elif isinstance(error, commands.ScheduledEventNotFound):
					warning_message = f"I was unable to find an event with the name: **{ctx.current_argument}**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> PartialEmojiConversionFailure
				elif isinstance(error, commands.PartialEmojiConversionFailure):
					warning_message = f"Provided **emoji** does not match the correct format"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> BadBoolArgument
				elif isinstance(error, commands.BadBoolArgument):
					warning_message = f"Boolean argument **{ctx.current_argument}** isn't convertible"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> RangeError
				elif isinstance(error, commands.RangeError):
					warning_message = f"**{ctx.current_argument}** is out of valid **range**"
					
					await ctx.warning(warning_message)

				# DiscordException -> CommandError -> UserInputError -> BadArgument -> ThreadNotFound
				elif isinstance(error, commands.ThreadNotFound):
					warning_message = f"I was unable to find a thread with the name: **{ctx.current_argument}**"
					
					await ctx.warning(warning_message)
				elif isinstance(error, commands.FlagError):
					await ctx.warning(str(error))
				else:
					await ctx.warning(str(error).replace('"', '**'))

			# DiscordException -> CommandError -> UserInputError -> BadUnionArgument
			if isinstance(error, commands.BadUnionArgument):
				def camel_case_split(identifier: str) -> str:
					return ' '.join([word for word in re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', identifier)])
				
				def list_converters(converters: List[Tuple[type, ...]]) -> str:
					# separate converters with commas and add 'or' before the last converter
					converters = ', '.join([f"{camel_case_split(converter.__qualname__)}" for converter in converters])
					if len(converters) > 1:
						converters = converters.rsplit(', ', 1)
						converters = ' or '.join(converters)
					return converters
				
				param = error.param
				converters = error.converters
				warning_message = f"Could not convert **{param.name.replace('_', ' ')}** into `{list_converters(converters)}`"
				await ctx.warning(warning_message)

			# DiscordException -> CommandError -> UserInputError -> BadLiteralArgument
			if isinstance(error, commands.BadLiteralArgument):
				literals = ', '.join([f"`{literal}`" for literal in error.literals])
				if len(error.literals) > 1:
					literals = literals.rsplit(', ', 1)
					literals = ' or '.join(literals)
				warning_message = f"**Option** must be one of the following: {literals}."
				await ctx.warning(warning_message)  
			else:
				error_message = f"Error in cog {cog}: {error_type}: {error}"
				logger.error(error_message)
		elif isinstance(error, commands.CommandNotFound):
			pass

		# DiscordException -> CommandError -> CheckFailure
		elif isinstance(error, commands.CheckFailure):
			# DiscordException -> CommandError -> CheckFailure -> BotMissingPermissions
			if isinstance(error, commands.BotMissingPermissions):
				permission_list = f""
				for perm in error.missing_permissions:
					perm: str = perm.replace('_', ' ')
					permission_list += f"`{perm}`, "
				permission_list = permission_list[:-2]
				warning_message = f"I don't have the {permission_list} permissions."
				if len(error.missing_permissions) == 1:
					warning_message = warning_message[:-2] + "."
				await ctx.warning(warning_message)

			# DiscordException -> CommandError -> CheckFailure -> MissingPermissions
			elif isinstance(error, commands.MissingPermissions):
				permission_list = f""
				for perm in error.missing_permissions:
					perm: str = perm.replace('_', ' ')
					permission_list += f"`{perm}`, "
				permission_list = permission_list[:-2]
				warning_message = f"You don't have the {permission_list} permissions."
				if len(error.missing_permissions) == 1:
					warning_message = warning_message[:-2] + "."
				await ctx.warning(warning_message)

			# DiscordException -> CommandError -> CheckFailure -> NotOwner
			elif isinstance(error, commands.NotOwner):
				await ctx.warning("You must be the **bot owner** to run this command.")
			else:
				from cogs.voice.voice import NotVoiceMember, NotVoiceOwner
				logger.info(f"Error in cog {cog}: {error_type}: {error}")
				if isinstance(error, NotVoiceMember):
					await ctx.warning(str(error))
					return
				elif isinstance(error, NotVoiceOwner):
					await ctx.warning(str(error))
					return
		# DiscordException -> CommandError -> CommandOnCooldown
		elif isinstance(error, commands.CommandOnCooldown):
			cooldown_message = f"Please wait **{error.retry_after:.2f}** seconds before using this command again."
			embed = make_embed_cooldown(ctx.author, cooldown_message)
			await ctx.send(embed=embed)
			logger.error(cooldown_message)       
		else:
			error_message = f"Error in cog {cog}: {error_type}: {error}"
			logger.error(error_message)

		if isinstance(error, discord.HTTPException):
			if isinstance(error, discord.Forbidden):
				error_message = f"Forbidden: I'm not allowed to execute this command"
				logger.error(error_message)
			else:
				error_message = f"Error in cog [{cog}]: {error.response}"
				logger.error(error_message)
