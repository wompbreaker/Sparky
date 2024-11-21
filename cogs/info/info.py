import typing
import logging
from datetime import datetime
import os

import discord
from discord.ext import commands

from helpers import (
    Context, 
    Emojis,
    make_embed_warning,
    make_embed_info
)
from bot import Sparky
from .views import *

log = logging.getLogger(__name__)

class Info(commands.Cog):
    """Commands that provide information about users, servers, and roles."""
    
    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            
            log.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            log.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return Emojis().get_emoji("info")

    @commands.command(
        name='avatar', 
        aliases=['av', 'avi', 'pfp', 'ab', 'ag'],
        extras={'information': ['User ID available'], 'parameters': ['user']},
        usage='Syntax: avatar <member>\nExample: avatar anakin'
    )
    async def get_user_avatar(self, ctx: Context, user: discord.User = None):
        """Get avatar of a member or yourself"""
        if user is None:
            user = ctx.author
        if isinstance(user.avatar, discord.Asset):
            avatar_url = user.avatar.url
        else:
            avatar_url = user.default_avatar.url
        embed = discord.Embed(
            title=f"{user}'s avatar",
            url=avatar_url,
            color=user.accent_color
        )
        embed.set_image(url=avatar_url)
        await ctx.send(embed)

    @commands.command(
        name='serveravatar', 
        aliases=['sav', 'savi', 'spfp', 'serverav', 'gav', 'guildav'],
        usage='Syntax: serveravatar <member>\nExample: serveravatar anakin'
    )
    async def get_member_server_avatar(self, ctx: Context, member: discord.Member = None):
        """Get the server avatar of a member or yourself"""
        if member is None:
            member = ctx.author

        if isinstance(member.guild_avatar, discord.Asset):
            embed = discord.Embed(
                title=f"{member}'s avatar",
                url=member.guild_avatar.url,
                color=member.accent_color
            )
            embed.set_image(url=member.guild_avatar.url)
            await ctx.send(embed)
            return
        else:
            if member == ctx.author:
                message = f"You don't have a **server avatar** set."
            else:
                message = f"**{member.mention}** doesn't have a **server avatar** set."
            embed = make_embed_warning(ctx.author, message)
            await ctx.send(embed)
            return

    @commands.command(
        name='banner', 
        aliases=['ub', 'userbanner'],
        usage='Syntax: banner <member>\nExample: banner anakin',
        extras={'information': ['User ID available']}
    )
    async def user_banner(self, ctx: Context, user: discord.User = None):
        """Get the banner of a member or yourself"""
        if user is None:
            user = ctx.author

        user = await self.bot.fetch_user(user.id)

        if isinstance(user.banner, discord.Asset):
            embed = discord.Embed(
                title=f"{user}'s banner",
                url=user.banner.url,
                color=user.accent_color
            )
            embed.set_image(url=user.banner.url)

            await ctx.send(embed)
            return
        else:
            if user == ctx.author:
                message = f"You don't have a **banner** set."
            else:
                message = f"**{user.mention}** doesn't have a **banner** set."
            embed = make_embed_warning(ctx.author, message)
            await ctx.send(embed)
            return

    @commands.command(
        name='serverbanner',
        aliases=['sb', 'sbanner'],
        usage='Syntax: serverbanner <member>\nExample: serverbanner anakin'
    )
    async def server_banner(self, ctx: Context, member: typing.Optional[discord.Member]):
        """Get the server banner of a member or yourself"""
        if member is None:
            member = ctx.author

        if isinstance(member.guild_banner, discord.Asset):
            embed = discord.Embed(
                title=f"{member}'s server banner",
                url=member.guild_banner.url,
                color=member.accent_color
            )
            embed.set_image(url=member.guild_banner.url)

            await ctx.send(embed)
            return
        else:
            if member == ctx.author:
                message = f"You don't have a **server banner** set."
            else:
                message = f"**{member.mention}** doesn't have a **server banner** set."
            embed = make_embed_warning(ctx.author, message)
            await ctx.send(embed)
            return

    @commands.command(
        name='userinfo',
        aliases=['whois', 'uinfo', 'info', 'ui'],
        usage='Syntax: userinfo <member>\nExample: userinfo anakin',
        extras={'information': ['User ID available']}
    )
    async def get_user_info(self, ctx: Context, user: typing.Union[discord.Member, discord.User] = None):
        """View information about a member or yourself"""
        if user is None:
            user = ctx.author

        username = user.name
        user_id = user.id

        embed = discord.Embed(
            description=f"**{username} ({user.id})**",
            color=user.accent_color,
            timestamp=datetime.now()
        )
        if isinstance(user, discord.Member):
            embed.add_field(
                name='Dates',
                value=f'**Created**: {user.created_at.strftime("%d/%m/%Y %I:%M %p")}\n'
                      f'**Joined**: {user.joined_at.strftime("%d/%m/%Y %I:%M %p")}',
                inline=False
            )
            embed.add_field(name="Roles",
                            value=", ".join([role.mention for role in user.roles if role.name != "@everyone"]),
                            inline=False
                            )
            embed.set_footer(text=f"Join position: {user.guild.members.index(user) + 1}")
        elif isinstance(user, discord.User):
            embed.add_field(
                name='Dates',
                value=f'**Created**: {user.created_at.strftime("%d/%m/%Y %I:%M %p")}',
                inline=False
            )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        else:
            embed.set_thumbnail(url=user.default_avatar.url)

        await ctx.send(embed)

    @commands.command(
        name='serverinfo',
        aliases=['guildinfo', 'sinfo', 'si', 'ginfo'],
        usage='Syntax: serverinfo (server id)\nExample: serverinfo 1216001413696458842',
    )
    async def get_server_info(self, ctx: Context, guild_id: int = None):
        """View information about the server"""

        if guild_id is not None:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                message = f"I do not **share a server** with the server ID `{guild_id}`"
                embed = make_embed_warning(ctx.author, message)
                await ctx.send(embed)
                return
        else:
            guild = ctx.guild
            
        def get_splash():
            if guild.splash:
                return f"[Click here]({guild.splash.url})"
            else:
                return "*None*"

        def get_banner():
            if guild.banner:
                return f"[Click here]({guild.banner.url})"
            else:
                return "*None*"

        def get_icon():
            if guild.icon:
                return f"[Click here]({guild.icon.url})"
            else:
                return "*None*"

        humans = 0
        bots = 0
        boosters = 0
        async for member in guild.fetch_members():
            if not member.bot:
                humans += 1
                if member.premium_since is not None:
                    boosters += 1
            elif member.bot:
                bots += 1

        server_splash = ''

        embed = discord.Embed(
            color=discord.Color.from_rgb(33, 33, 33),
            title=guild.name,
            timestamp=datetime.now(),
            description=f"Server created on: {discord.utils.format_dt(guild.created_at, style='D')} ({discord.utils.format_dt(guild.created_at, style='R')})"
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        embed.set_thumbnail(url=guild.icon)
        embed.set_footer(text=f"Guild ID: {guild.id}")
        embed.add_field(name='Owner', value=guild.owner, inline=True)
        embed.add_field(name="Members", value=f"**Total:** {humans + bots}\n**Humans:** {humans}\n**Bots:** {bots}", inline=True)
        embed.add_field(name='Information', value=f'**Verification:** {guild.verification_level}\n'
                                                  f'**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})', inline=True)
        embed.add_field(name='Design',
                        value=f'**Splash:** {get_splash()}\n**Banner:** {get_banner()}\n**Icon:** {get_icon()}',
                        inline=True)
        embed.add_field(name=f'Channels ({len(guild.channels)})',
                        value=f'**Text:** {len(guild.text_channels)}\n'
                              f'**Voice:** {len(guild.voice_channels)}\n'
                              f'**Category:** {len(guild.categories)}',
                        inline=True)
        embed.add_field(name='Count',
                        value=f'**Roles:** {len(guild.roles)}\n'
                              f'**Emojis:** {len(guild.emojis)}\n'
                              f'**Stickers:** {len(guild.stickers)}\n'
                              f'**Boosters:** {boosters}',
                        inline=True)
        await ctx.send(embed)

    @commands.command(
        name='checkrole', 
        aliases=['roleperms'],
        usage='Syntax: checkrole <role>\nExample: checkrole Admin',
        enabled=True
    )
    async def check_role_perms(self, ctx, role: discord.Role):
        """Check the permissions of a role"""
        readable_perms = []
        perm_dict = {}
        for perm, value in role.permissions:
            if value:  # Check if permission is enabled
                readable_perms.append(perm.replace("_", " "))  # Format permission name
                perm_dict.update({perm: value})

        readable_perms_str = ", ".join(readable_perms)  # Join permissions into a string
        if len(readable_perms) > 0:
            message = f"Permissions for role {role.mention} are:\n{readable_perms_str}"
        else:
            message = f"Looks like role {role.mention} has no perms."

        embed = make_embed_info(ctx.author, message)
        await ctx.send(embed)

    @commands.command(
        name='roleinfo',
        aliases=['ri', 'rinfo'],
        usage='Syntax: roleinfo <role>\nExample: roleinfo Admin',
    )
    async def get_role_info(self, ctx: Context, role: discord.Role):
        """Get information about a role"""
        embed = discord.Embed(
            title=f"Role: {role.name}",
            color=discord.Color(0x000001)
        )
        try:
            if ctx.author.avatar:
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
            else:
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.default_avatar.url)
            embed.add_field(name="Role ID", value=f'`{role.id}`', inline=True)
            embed.add_field(name="Guild", value=f'{role.guild.name} (`{role.guild.id}`)', inline=True)
            embed.add_field(name="Role Color", value=f'`{role.color}`', inline=True)
            embed.add_field(name="Role Position", value=role.position, inline=True)
            embed.add_field(name="Role Created", value=f'{discord.utils.format_dt(role.created_at, "f")} ({discord.utils.format_dt(role.created_at, "R")})', inline=True)
            embed.add_field(name="Role Mention", value=role.mention, inline=True)
            embed.add_field(name="Role Hoisted", value=role.hoist, inline=True)
            embed.add_field(name="Role Managed", value=role.managed, inline=True)
            embed.add_field(name="Role Mentionable", value=role.mentionable, inline=True)
            embed.add_field(name="Role Members", value=f"{len(role.members)} members", inline=True)
            await ctx.send(embed)
        except Exception as e:
            log.error(f"{type(e)} - {e}")

    @commands.command(
        name='members',
        aliases=['inrole'],
        usage='Syntax: members <role>\nExample: members Admin',
    )
    async def list_members(self, ctx: Context, *, role: typing.Optional[discord.Role]):
        """View members in a role"""
        try:
            member_list = []
            if role is None:
                role = ctx.author.top_role
                if role is None:
                    message = "No **role** specified."
                    embed = make_embed_warning(ctx.author, message)
                    await ctx.send(embed)
                    return
            for member in role.members:
                member_entry = f"{member.name}"
                member_list.append(member_entry)
            try:
                pages = MemberMenu(MembersPageSource(member_list, role), ctx=ctx)
                await pages.start()
            except discord.HTTPException:
                prefix = f"{role.name}_" if role is not None else ""
                filename = f"{prefix}members.txt"
                with open(filename, 'w') as file:
                    file.write(member_list)

                with open(filename, 'rb') as file:
                    await ctx.send(file=discord.File(file, filename=filename))
                os.remove(filename)
        except Exception as e:
            log.error(f"{type(e)} - {e}")


    @commands.command(
        name='membercount',
        aliases=["mc", "serverstats", "serverstatistics"],
        usage='Syntax: membercount',
    )
    async def member_count(self, ctx: Context):
        """Vier server member count"""
        try:
            # server statistics
            # users humans bots
            embed = discord.Embed(
                color=0x000000
            )
            humans = 0
            bots = 0
            for member in ctx.guild.members:
                if not member.bot:
                    humans += 1
                elif member.bot:
                    bots += 1
            embed.add_field(name="Users", value=ctx.guild.member_count)
            embed.add_field(name="Humans", value=humans)
            embed.add_field(name="Bots", value=bots)
            embed.set_author(name=f"{ctx.guild.name} statistics", icon_url=ctx.guild.icon.url)
            await ctx.send(embed)
        except Exception as e:
            log.error(e)
