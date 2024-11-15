from __future__ import annotations
import re
import aiohttp
import discord
from discord.ext import commands
import json
import logging
from typing import TYPE_CHECKING
from .view import *
from helpers import Context, Emojis

if TYPE_CHECKING:
    from bot import Sparky

logger = logging.getLogger(__name__)
  
class Fun(commands.Cog):
    """Commands for fun and entertainment"""

    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return Emojis().get_emoji('glowing_star')

    @commands.command(
        name='steal',
        usage='Syntax: steal (message link)\nExample: steal ...discordapp.com/channels/...',
    )
    async def steal_emoji_or_sticker(self, ctx: Context, message_link: str = None):
        """Steal emojis or stickers from a message"""
        custom_emoji_pattern = r"<(a?):([a-zA-Z0-9_]+):(\d+)>"
        try:
            # Check if a user replied to a message
            if ctx.message.reference is not None:
                original_message = ctx.message.reference.cached_message
                # first check if a message contains a sticker and then check for emojis if no stickers were found
                if original_message is None:
                    original_message_id = ctx.message.reference.message_id
                    original_message = await ctx.channel.fetch_message(original_message_id)
                sticker_list = original_message.stickers

                if len(sticker_list) > 0:
                    # we get the sticker by finding the only sticker in the message sticker list
                    sticker = sticker_list[0]
                    await self.steal_sticker(ctx, sticker)
                    return

                # Regular expression to match custom emojis (static and animated)
                message_content = original_message.content

                if len(re.findall(custom_emoji_pattern, message_content)) == 0:
                    await ctx.warning("No **stickers or emojis found** in the referenced message.")
                    return
                else:
                    await self.steal_emojis(ctx, message_content)
                return
            else:
                # Check for the last 100 messages if no message link is provided. Check for both stickers and emojis
                async for message in ctx.channel.history(limit=100):
                    if len(message.stickers) > 0:
                        sticker = message.stickers[0]
                        await self.steal_sticker(ctx, sticker)
                        return
                    if len(re.findall(custom_emoji_pattern, message.content)) > 0:
                        await self.steal_emojis(ctx, message.content)
                        return

            await ctx.warning("Please reply to a message with this command to get emojis/stickers.")

        except Exception as e:
            logger.error(f"Exception in Fun steal_emoji_or_sticker: {e}")
            await ctx.send("An error occurred while processing the sticker.")

    @commands.command(
        name='steal',
        usage='Syntax: steal (message link)\nExample: steal ...discordapp.com/channels/...',
    )
    async def steal_emoji_or_sticker(self, ctx: Context, message_link: str = None):
        """Steal emojis or stickers from a message"""
        custom_emoji_pattern = r"<(a?):([a-zA-Z0-9_]+):(\d+)>"
        try:
            # Check if a user replied to a message
            if ctx.message.reference is not None:
                original_message = ctx.message.reference.cached_message
                # first check if a message contains a sticker and then check for emojis if no stickers were found
                if original_message is None:
                    original_message_id = ctx.message.reference.message_id
                    original_message = await ctx.channel.fetch_message(original_message_id)
                sticker_list = original_message.stickers

                if len(sticker_list) > 0:
                    # we get the sticker by finding the only sticker in the message sticker list
                    sticker = sticker_list[0]
                    await self.steal_sticker(ctx, sticker)
                    return

                # Regular expression to match custom emojis (static and animated)
                message_content = original_message.content

                if len(re.findall(custom_emoji_pattern, message_content)) == 0:
                    await ctx.warning("No **stickers or emojis found** in the referenced message.")
                    return
                else:
                    await self.steal_emojis(ctx, message_content)
                return
            else:
                # Check for the last 100 messages if no message link is provided. Check for both stickers and emojis
                async for message in ctx.channel.history(limit=100):
                    if len(message.stickers) > 0:
                        sticker = message.stickers[0]
                        await self.steal_sticker(ctx, sticker)
                        return
                    if len(re.findall(custom_emoji_pattern, message.content)) > 0:
                        await self.steal_emojis(ctx, message.content)
                        return

            await ctx.warning("Please reply to a message with this command to get emojis/stickers.")

        except Exception as e:
            logger.error(f"Exception in Fun steal_emoji_or_sticker: {e}")
            await ctx.send("An error occurred while processing the sticker.")

    @commands.command(
        name='steal',
        usage='Syntax: steal (message link)\nExample: steal ...discordapp.com/channels/...',
    )
    async def steal_emoji_or_sticker(self, ctx: Context, message_link: str = None):
        """Steal emojis or stickers from a message"""
        custom_emoji_pattern = r"<(a?):([a-zA-Z0-9_]+):(\d+)>"
        try:
            # Check if a user replied to a message
            if ctx.message.reference is not None:
                original_message = ctx.message.reference.cached_message
                # first check if a message contains a sticker and then check for emojis if no stickers were found
                if original_message is None:
                    original_message_id = ctx.message.reference.message_id
                    original_message = await ctx.channel.fetch_message(original_message_id)
                sticker_list = original_message.stickers

                if len(sticker_list) > 0:
                    # we get the sticker by finding the only sticker in the message sticker list
                    sticker = sticker_list[0]
                    await self.steal_sticker(ctx, sticker)
                    return

                # Regular expression to match custom emojis (static and animated)
                message_content = original_message.content

                if len(re.findall(custom_emoji_pattern, message_content)) == 0:
                    await ctx.warning("No **stickers or emojis found** in the referenced message.")
                    return
                else:
                    await self.steal_emojis(ctx, message_content)
                return
            else:
                # Check for the last 100 messages if no message link is provided. Check for both stickers and emojis
                async for message in ctx.channel.history(limit=100):
                    if len(message.stickers) > 0:
                        sticker = message.stickers[0]
                        await self.steal_sticker(ctx, sticker)
                        return
                    if len(re.findall(custom_emoji_pattern, message.content)) > 0:
                        await self.steal_emojis(ctx, message.content)
                        return
            await ctx.warning("Please reply to a message with this command to get emojis/stickers.")

        except Exception as e:
            logger.error(f"Exception in Fun steal_emoji_or_sticker: {e}")
            await ctx.error("An error occurred while processing the sticker.")

    async def steal_sticker(self, ctx: Context, sticker_item: discord.StickerItem):
        sticker = await sticker_item.fetch()
        # Ignore Standard discord stickers
        if isinstance(sticker, discord.StandardSticker):
            await ctx.warning("Couldn't **turn a standard Discord sticker** into an image.")
            return

        sticker_id = sticker.id
        sticker_name = sticker.name
        # Check if it's possible to get sticker guild name
        sticker_guild_name = sticker.guild.name if sticker.guild else "Unknown"
        sticker_url = f"https://cdn.discordapp.com/stickers/{sticker_id}.{sticker.format.file_extension}"
        sticker_url1 = f"https://media.discordapp.net/stickers/{sticker_id}.{sticker.format.file_extension}"
        sticker_url2 = f"https://media.discordapp.net/stickers/{sticker_id}.webp?size=1024"

        async with aiohttp.ClientSession() as session:
            async with session.get(sticker_url1) as resp:
                if resp.status == 200:
                    data = await resp.read()

        embed = discord.Embed(
            color=discord.Color.light_gray(),
            title=sticker_name
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        embed.add_field(name="Sticker ID", value=f"`{sticker_id}`", inline=True)
        embed.add_field(name="Guild", value=sticker_guild_name, inline=True)
        embed.add_field(name="Image URL", value=f"[**Click here to open the image**]({sticker_url2})", inline=False)
        embed.set_image(url=sticker_url2)
        if sticker.format in [discord.StickerFormatType.gif, discord.StickerFormatType.apng]:
            embed.set_footer(text="Animated stickers might appear frozen.\nThey're not, open the link and they'll appear animated.")
        
        view = BaseStealView(ctx=ctx, data=data, sticker=sticker, message_content="")
        if not ctx.author.guild_permissions.manage_emojis_and_stickers:
            view.remove_item(view.children[1])
        out = await ctx.send(embed, view=view)
        view.response = out

    async def steal_emojis(self, ctx: Context, message_content: str):
        # Regular expression to match custom emojis (animated, emoji name, emoji id)
        custom_emoji_pattern = r"<(a?):([a-zA-Z0-9_]+):(\d+)>"
        custom_emoji_pattern = re.compile(custom_emoji_pattern)
        # Find all emojis in the message content
        matches = custom_emoji_pattern.findall(message_content)
        if not matches:
            await ctx.warning("No **emojis found** in the referenced message.")
            return

        # Get all emojis from the message content
        emojis = []
        for match in matches:
            animated = bool(match[0])
            emoji_name = match[1]
            emoji_id = int(match[2])
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}"

            emojis.append((emoji_name, emoji_id, emoji_url))
        # Create a json file with all emojis in format emoji_name: emoji_url
        with open("emojis.json", "w") as file:
            json.dump({emoji[0]: emoji[2] for emoji in emojis}, file)

        source = StealPageSource(emojis)
        view = StealMenu(source, ctx=ctx)
        await view.start()

async def setup(bot: Sparky):
    try:
        await bot.add_cog(Fun(bot))
    except Exception as e:
        logger.error(f"ERROR: Failed to setup Fun: {e}")
