import asyncio
import random
from typing import Optional, Union
from datetime import datetime

import discord
from discord.ext import commands

from bot import Sparky
import logging
from helpers import (
    Context,
    get_IP_full_info,
    generate_google_maps_link
)

logger = logging.getLogger(__name__)

class Ping(commands.Cog):
    """Commands for checking the bot's latency and uptime."""
    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{HEAVY EXCLAMATION MARK SYMBOL}')
    
    @commands.hybrid_command(
        usage="Syntax: ping",
    )
    async def ping(self, ctx: Context):
        """Check the bot's latency."""
        bot_latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            color=discord.Color.green(),
            description=f":ping_pong: Pong! Answered in: `{bot_latency} ms`"
        )
        await ctx.send(embed)

    @commands.command(aliases=['e'], usage="Syntax: emoji <emoji>Example: emoji :sparky:")
    async def emoji(self, ctx: Context, emoji: discord.Emoji):
        """Get information about a custom emoji."""
        anim = ""
        if not emoji.animated:
            emoji_string = f"<:{emoji.name}:{emoji.id}>"
        else:
            emoji_string = f"<a:{emoji.name}:{emoji.id}>"
            anim = "a"

        embed = discord.Embed(
            color=discord.Color.dark_gold(),
            description=f"Emoji name: {emoji.name}, emoji id: {emoji.id}\n"
                        f"Emoji copy string: ```<{anim}:{emoji.name}:{emoji.id}>```\n"
                        f"Emoji printed: {emoji_string}"
        )
        await ctx.send(embed)

    @commands.command(
        name='doxx',
        usage="Syntax: doxx <user> <parameter>\nExample: doxx @sparky#0001 all",
        extras={"information": ["basic", "network", "location", "all"]}
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def doxx(self, ctx: Context, target: discord.Member = None, info_type: Optional[str] = "basic"):
        """Provides network and location of a member. This command is just a joke."""
        if target is None and info_type == "basic":
            cmd_prefix = await self.bot.bot_prefix(ctx.guild)
            help_embed = discord.Embed(
                title="Command: doxx",
                description="Provides network and location of a member\n"
                            "Parameters: (b)asic, (n)etwork, (l)ocation, (a)ll\n"
                            f"```Syntax: {cmd_prefix}doxx (user) (parameter)\n"
                            f"Example: {cmd_prefix}doxx {ctx.guild.me} network\n"
                            f"Example: {cmd_prefix}doxx {ctx.author} all```",
                color=discord.Color.dark_gray()
            )
            help_embed.set_author(name="sparky help", icon_url=ctx.guild.me.display_avatar.url)
            help_embed.set_footer(
                text="Just a joke btw"
            )
            await ctx.send(help_embed)
            return

        if target.bot:
            await ctx.warning(f"No information: {target} is a bot.")
            return

        ip_address, latitude, longitude, timezone, auto_sys_number, auto_sys, is_proxy, country, country_code, state, county, city, postcode, district, suburb, street, house_number, state_code, result_type = get_IP_full_info()

        target_url = f"https://discordapp.com/users/{target.id}"

        doxx_embed = discord.Embed(
            colour=discord.Colour.red(),
            description=f"All information that could be found from {target.name}'s IP",
            timestamp=datetime.now(),
            title=f"Click to see {target}'s location",
            type="rich",
            url=generate_google_maps_link(latitude, longitude)
        )

        info_type = info_type.lower().strip()
        if info_type == "basic" or info_type == "b":
            doxx_embed.add_field(name="IP Address", value=f"{ip_address}", inline=True)
            doxx_embed.add_field(name="Country", value=f"{country} :flag_{str(country_code).lower()}:", inline=True)
            doxx_embed.add_field(name="City", value=f"{city}", inline=True)
            doxx_embed.add_field(name="Street", value=f"{street}", inline=True)
            doxx_embed.add_field(name="House number", value=f"{house_number}", inline=True)
        elif info_type == "network" or info_type == "n":
            doxx_embed.add_field(name="IP Address", value=f"{ip_address}", inline=True)
            doxx_embed.add_field(name="IP Address type", value="IPv4", inline=True)
            doxx_embed.add_field(name="IPv6 available", value="false", inline=True)
            doxx_embed.add_field(name="Private IP", value="True", inline=True)
            doxx_embed.add_field(name="ASN", value=f"{auto_sys_number}", inline=True)
            doxx_embed.add_field(name="AS", value=f"{auto_sys}", inline=True)
            doxx_embed.add_field(name="Proxy", value=f"{is_proxy}", inline=True)
            doxx_embed.add_field(name="Number of open ports", value=f"{random.randint(0, 7)}", inline=True)
        elif info_type == "location" or info_type == "l":
            doxx_embed.add_field(name="Latitude", value=f"{latitude}", inline=True)
            doxx_embed.add_field(name="Longitude", value=f"{longitude}", inline=True)
            doxx_embed.add_field(name="Country", value=f"{country} :flag_{str(country_code).lower()}:", inline=True)
            doxx_embed.add_field(name="Country code", value=f"{str(country_code).upper()}", inline=True)
            doxx_embed.add_field(name="State", value=f"{state}", inline=True)
            doxx_embed.add_field(name="State code", value=f"{state_code}", inline=True)
            doxx_embed.add_field(name="County", value=f"{county}", inline=True)
            doxx_embed.add_field(name="City", value=f"{city}", inline=True)
            doxx_embed.add_field(name="Postcode", value=f"{postcode}", inline=True)
            doxx_embed.add_field(name="District", value=f"{district}", inline=True)
            doxx_embed.add_field(name="Suburb", value=f"{suburb}", inline=True)
            doxx_embed.add_field(name="Street", value=f"{street}", inline=True)
            doxx_embed.add_field(name="House number", value=f"{house_number}", inline=True)
            doxx_embed.add_field(name="Timezone", value=f"{timezone} GMT", inline=True)
        elif info_type == "all" or info_type == "a":
            doxx_embed.add_field(name="IP Address", value=f"{ip_address}", inline=True)
            doxx_embed.add_field(name="IP Address type", value="IPv4", inline=True)
            doxx_embed.add_field(name="IPv6 available", value="false", inline=True)
            doxx_embed.add_field(name="Private IP", value="True", inline=True)
            doxx_embed.add_field(name="ASN", value=f"{auto_sys_number}", inline=True)
            doxx_embed.add_field(name="AS", value=f"{auto_sys}", inline=True)
            doxx_embed.add_field(name="Proxy", value=f"{is_proxy}", inline=True)
            doxx_embed.add_field(name="Number of open ports", value=f"{random.randint(0, 7)}", inline=True)
            doxx_embed.add_field(name="Latitude", value=f"{latitude}", inline=True)
            doxx_embed.add_field(name="Longitude", value=f"{longitude}", inline=True)
            doxx_embed.add_field(name="Country", value=f"{country} :flag_{str(country_code).lower()}:", inline=True)
            doxx_embed.add_field(name="Country code", value=f"{str(country_code).upper()}", inline=True)
            doxx_embed.add_field(name="State", value=f"{state}", inline=True)
            doxx_embed.add_field(name="State code", value=f"{state_code}", inline=True)
            doxx_embed.add_field(name="County", value=f"{county}", inline=True)
            doxx_embed.add_field(name="City", value=f"{city}", inline=True)
            doxx_embed.add_field(name="Postcode", value=f"{postcode}", inline=True)
            doxx_embed.add_field(name="District", value=f"{district}", inline=True)
            doxx_embed.add_field(name="Suburb", value=f"{suburb}", inline=True)
            doxx_embed.add_field(name="Street", value=f"{street}", inline=True)
            doxx_embed.add_field(name="House number", value=f"{house_number}", inline=True)
            doxx_embed.add_field(name="Timezone", value=f"{timezone} GMT", inline=True)
        else:
            await ctx.warning(f"Invalid info type requested.")
            return

        doxx_embed.set_author(
            name=f"{target}",
            url=target_url,
            icon_url=target.display_avatar.url
        )
        doxx_embed.set_footer(text="This is just a prank btw",
                              icon_url=ctx.author.display_avatar.url)

        await ctx.send(doxx_embed)

    @commands.command(
        name='massping', 
        aliases=['spamping'],
        usage="Syntax: massping <member> [custom message]\nExample: massping @anakin hi friend",
        extras={"information": ["manage_messages"]}
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def mass_ping(self, ctx: Context, member: Union[discord.Member, str] = None, *, ping_message: str = None):
        """Ping the specified member 5 times."""
        if member is None and ping_message is None:
            await ctx.send_help(self.mass_ping)
            return

        if ping_message is None:
            ping_message = "> Sorry for the ping :skull::skull::sob::sweat_smile:"

        await ctx.message.delete()

        if member != '@everyone':
            if isinstance(member, discord.Member):
                for i in range(5):
                    await ctx.send(member.mention)
                await ctx.send(f"> {ping_message}")
            else:
                await ctx.send("Something went wrong...")
        else:
            await asyncio.sleep(0.5)
            await ctx.send("Let's not mention everyone :sob:")
