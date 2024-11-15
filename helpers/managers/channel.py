from __future__ import annotations
from typing import Optional
import discord
from discord import Message, Member
from ..utils.embeds import (
	make_embed_error,
	make_embed_warning,
	make_embed_success
)

class Channel(discord.TextChannel):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	async def warn(self, member: Member, warn_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
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
		return await self.send(
			make_embed_warning(member, warn_message),
			ephemeral=ephemeral, 
			**kwargs
		)
	
	# alias for warn
	async def warning(self, member: Member, warn_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Sends a warning embed with the provided message
		Alias for :meth:`warn`
		
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
		return await self.warn(member, warn_message, ephemeral=ephemeral, **kwargs)
	
	async def error(self, member: Member, error_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
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
			make_embed_error(member, error_message),
			ephemeral=ephemeral, 
			**kwargs
		)
	
	async def success(self, member: Member, success_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
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
			make_embed_success(member, success_message),
			ephemeral=ephemeral, 
			**kwargs
		)
	
	# alias for success
	async def approve(self, member: Member, success_message: str, ephemeral=False, **kwargs) -> Optional[Message]:
		"""Send a success embed with the provided message
		Alias for :meth:`success`

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
		return await self.success(member, success_message, ephemeral=ephemeral, **kwargs)
	
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
			if isinstance(args[0], discord.Embed):
				kwargs['embed'] = args[0]
			elif isinstance(args[0], str):
				kwargs['content'] = args[0]
			else:
				raise TypeError("Invalid type for message content")
		else:
			raise TypeError("No message content provided")
		return await super().send(**kwargs, ephemeral=ephemeral)
	