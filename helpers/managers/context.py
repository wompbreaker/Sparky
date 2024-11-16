from __future__ import annotations
from typing import Optional, Dict, Any, TYPE_CHECKING
from discord import Message, Embed
from discord.ext.commands import Context as DiscordContext
from discord.utils import cached_property
from ..utils.embeds import (
	make_embed_error,
	make_embed_warning,
	make_embed_success
)

if TYPE_CHECKING:
	from bot import Sparky

class Context(DiscordContext):
	flags: Dict[str, Any] = {}
	bot: Sparky
	me: Sparky

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@cached_property
	def replied_message(self) -> Optional[Message]:
		reference = self.message.reference
		if reference and isinstance(reference.resolved, Message):
			return reference.resolved
	
	async def warning(self, warn_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Sends a warning embed with the provided message
		
		Parameters
		----------
		warn_message : str
			The message to be displayed in the embed

		ephemeral : bool
			Whether the message should be ephemeral or not
			
		**kwargs : Dict[str, Any]
			Additional keyword arguments to be passed to the send method

		Returns
		-------
		Message
			The message that was sent
		"""
		return await self.warn(warn_message, ephemeral=ephemeral, **kwargs)
	
	async def error(self, error_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Send an error embed with the provided message
		
		Parameters
		----------
		error_message : str
			The message to be displayed in the embed

		ephemeral : bool
			Whether the message should be ephemeral or not
			
		**kwargs : Dict[str, Any]
			Additional keyword arguments to be passed to the send method

		Returns
		-------
		Message
			The message that was sent
		"""
		return await self.send(
			make_embed_error(self.author, error_message),
			ephemeral=ephemeral, 
			**kwargs
		)
	
	async def success(self, success_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Send a success embed with the provided message
		
		Parameters
		----------
		success_message : str
			The message to be displayed in the embed

		ephemeral : bool
			Whether the message should be ephemeral or not
			
		**kwargs : Dict[str, Any]
			Additional keyword arguments to be passed to the send method

		Returns
		-------
		Message
			The message that was sent
		"""
		return await self.send(
			make_embed_success(self.author, success_message),
			ephemeral=ephemeral, 
			**kwargs
		)
	
	async def send(self, *args, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Send a message with the provided content or embed

		Parameters
		----------
		*args
			The content or embed to be sent

		ephemeral : bool
			Whether the message should be ephemeral or not

		**kwargs : Dict[str, Any]
			Additional keyword arguments to be passed to the send method

		Returns
		-------
		Message
			The message that was sent
		"""
		if args:
			if isinstance(args[0], Embed):
				kwargs['embed'] = args[0]
			elif isinstance(args[0], str):
				kwargs['content'] = args[0]
			elif args[0] is None:
				raise ValueError("Message content cannot be None")
			else:
				raise TypeError("Invalid type for message content")
		else:
			raise ValueError("No content or embed provided")
		return await super().send(**kwargs, ephemeral=ephemeral)
	
	async def reply(self, *args, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Reply to the message that triggered the command

		Parameters
		----------
		*args
			The content or embed to be sent

		ephemeral : bool
			Whether the message should be ephemeral or not

		**kwargs : Dict[str, Any]
			Additional keyword arguments to be passed to the send method

		Returns
		-------
		Message
			The message that was sent
		"""
		if args:
			if isinstance(args[0], Embed):
				kwargs['embed'] = args[0]
			elif isinstance(args[0], str):
				kwargs['content'] = args[0]
			elif args[0] is None:
				raise ValueError("Message content cannot be None")
			else:
				raise TypeError("Invalid type for message content")
		else:
			raise ValueError("No content or embed provided")
		return await super().reply(**kwargs, ephemeral=ephemeral)
	