import json

import discord
from discord.ext import commands
from discord import app_commands
from bot import Sparky
from discord.app_commands import Choice, Group
from typing import Optional, List
import aiomysql
from helpers import (
    Emojis,
    Context,
    make_embed_error, 
    make_embed_warning, 
    make_embed_success,
    make_embed_warn
)
import logging
from .decorators import *
from .helper import *
from .views import ConfirmView
from .db import *

logger = logging.getLogger(__name__)

perm_list = [
    'administrator', 'ban_members', 'kick_members', 'manage_channels', 
    'manage_permissions', 'manage_emojis', 'manage_emojis_and_stickers', 
    'manage_guild', 'manage_roles', 'manage_webhooks', 'moderate_members'
]

WARNING = Emojis().get_emoji('warning')

class Antinuke(commands.Cog):
    """Antinuke to protect your server"""

    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return Emojis().get_emoji('shield')

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, AntinukeFailure):
            embed = make_embed_warning(
                interaction.user, "You must be an **antinuke admin** to run this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        if isinstance(error, NotGuildOwner):
            embed = make_embed_warning(
                interaction.user, "You must be a **server owner** to run this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    #######################################################################################################
    #                                          LISTENERS                                                  #
    #######################################################################################################

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT guild_id FROM antinuke_system WHERE guild_id = %s;",
                        (guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        return
                    else:
                        await cur.execute(
                            "INSERT INTO antinuke_system (guild_id) VALUES (%s);",
                            (guild.id,)
                        )
        except Exception as e:
            logger.error(f"{type(e)} error in on_guild_join: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        try:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT guild_id FROM antinuke_system WHERE guild_id = %s;",
                        (guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        await cur.execute(
                            "DELETE FROM antinuke_system WHERE guild_id = %s;",
                            (guild.id,)
                        )
        except Exception as e:
            logger.error(f"{type(e)} error in on_guild_remove: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            botadd_enabled = await get_botadd_settings(member.guild.id)
            if botadd_enabled and member.bot:
                # Check if the bot is whitelisted
                whitelisted = await is_whitelisted(member.id)
                if not whitelisted:
                    await member.kick(reason="Botadd antinuke enabled")
        except Exception as e:
            logger.error(f"{type(e)} error in on_member_join: {e}")

    @commands.Cog.listener()
    async def on_guild_update(self, guild_before: discord.Guild, guild_after: discord.Guild):
        try:
            if guild_before.vanity_url != guild_after.vanity_url:
                async for entry in guild_after.audit_logs(action=discord.AuditLogAction.guild_update, limit=3):
                    moderator = entry.user
                enabled, punishment = await get_vanity_settings(guild_after.id)
                is_whitelisted = await is_whitelisted(moderator.id)
                if is_whitelisted:
                    return
                if enabled:
                    await self.punish_moderator(moderator, punishment, "changing the server vanity")
                    embed = self.make_embed_vanity_alert(moderator, guild_before, guild_before.vanity_url, guild_after.vanity_url)
                    antinuke_admins = await get_antinuke_admins(guild_after.id)
                    owner_dm = await guild_after.owner.create_dm()
                    try:
                        await owner_dm.send(embed=embed)
                    except Exception as e:
                        logger.error(f"{type(e)} error: Failed to DM {guild_after.owner.name}. {e}")

                    for admin in antinuke_admins:
                        if int(admin) == guild_after.owner.id:
                            continue
                        admin_user = await self.bot.fetch_user(int(admin))
                        dm_channel = await admin_user.create_dm()
                        try:
                            await dm_channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"{type(e)} error: Failed to DM {admin_user.name}. {e}")
                            continue
        except Exception as e:
            logger.error(f"{type(e)} error: {e}")

    async def unavailable(self, interaction: discord.Interaction):
        message = "This command is currently unavailable"
        embed = make_embed_warning(interaction.user, message)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    #######################################################################################################
    #                                       HELP COMMANDS                                                 #
    #######################################################################################################

    @commands.group(
            name='antinuke',
            aliases=['an'],
            invoke_without_command=True,
            usage='Syntax: /antinuke (subcommand) <args>\nExample: /antinuke ban on --do ban',
            extras={'permissions': ['Server Owner']}
    )
    async def antinuke(self, ctx: Context):
        """Antinuke to protect your server. Run as a slash command."""
        await ctx.send_help(self.antinuke)

    @antinuke.command(
        name='admin',
        usage='Syntax: /antinuke admin (member)',
        extras={'permissions': ['Server Owner'], 'parameters': ['member']}
    )
    async def antinuke_admin(self, ctx: Context):
        """Give a user permissions to edit antinuke settings. Run as a slash command."""
        await ctx.send_help(self.antinuke_admin)

    @antinuke.command(
        name='ban',
        usage='Syntax: /antinuke ban (on or off) <params>\nExample: /antinuke ban on --do ban',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_ban(self, ctx: Context):
        """Prevent mass member ban. Run as a slash command."""
        await ctx.send_help(self.antinuke_ban)

    @antinuke.command(
        name='config',
        aliases=['configuration', 'settings'],
        usage='Syntax: /antinuke config',
        extras={'permissions': ['Server Owner']}
    )
    async def antinuke_config(self, ctx: Context):
        """View server configuration for Antinuke. Run as a slash command."""
        await ctx.send_help(self.antinuke_config)

    @antinuke.command(
        name='permissions',
        aliases=['perms'],
        usage='Syntax: /antinuke permissions (grant or remove) (permission name)\nExample: /antinuke permissions grant administrator',
        extras={'permissions': ['Server Owner'], 'parameters': ['typee', 'permission', 'flags']}
    )
    async def antinuke_permissions(self, ctx: Context):
        """Watch dangerous permissions being granted or removed. Run as a slash command."""
        await ctx.send_help(self.antinuke_permissions)

    @antinuke.command(
        name='webhook',
        usage='Syntax: /antinuke webhook (on or off) <params>\nExample: /antinuke webhook on --do ban --threshold 3',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_webhook(self, ctx: Context):
        """Prevent mass webhook creation. Run as a slash command."""
        await ctx.send_help(self.antinuke_webhook)

    @antinuke.command(
        name='whitelist',
        usage='Syntax: /antinuke whitelist (member or bot id)\nExample: /antinuke whitelist 1224358430404513792',
        extras={'permissions': ['Server Owner'], 'parameters': ['member']}
    )
    async def antinuke_whitelist(self, ctx: Context):
        """Whitelist a member from triggering antinuke or a bot to join. Run as a slash command."""
        await ctx.send_help(self.antinuke_whitelist)

    @antinuke.command(
        name='botadd',
        usage='Syntax: /antinuke botadd (on or off)\nExample: /antinuke botadd on',
        extras={'permissions': ['Server Owner'], 'parameters': ['status']}
    )
    async def antinuke_botadd(self, ctx: Context):
        """Prevent new bots from joining the server. Run as a slash command."""
        await ctx.send_help(self.antinuke_botadd)

    @antinuke.command(
        name='vanity',
        aliases=['vanityurl'],
        usage='Syntax: /antinuke vanity (on or off) <params>\nExample: /antinuke vanity on --do ban',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_vanity(self, ctx: Context):
        """Punish users who change the server vanity URL. Run as a slash command."""
        await ctx.send_help(self.antinuke_vanity)

    @antinuke.command(
        name='channel',
        usage='Syntax: /antinuke channel (on or off) <params>\nExample: /antinuke channel on --do ban --threshold 5',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_channel(self, ctx: Context):
        """Prevent mass channel creation or deletion. Run as a slash command."""
        await ctx.send_help(self.antinuke_channel)

    @antinuke.command(
        name='list',
        usage='Syntax: /antinuke list',
        extras={'permissions': ['Server Owner']}
    )
    async def antinuke_list(self, ctx: Context):
        """View all enabled modules along with whitelisted members and bots. Run as a slash command."""
        await ctx.send_help(self.antinuke_list)

    @antinuke.command(
        name='emoji',
        usage='Syntax: /antinuke emoji (on or off) <params>\nExample: /antinuke emoji on --do kick --threshold 5',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_emoji(self, ctx: Context):
        """Prevent mass emoji deletion. Run as a slash command."""
        await ctx.send_help(self.antinuke_emoji)

    @antinuke.command(
        name='admins',
        usage='Syntax: /antinuke admins',
        extras={'permissions': ['manage guild']}
    )
    async def antinuke_admins(self, ctx: Context):
        """View antinuke admins for the server. Run as a slash command."""
        await ctx.send_help(self.antinuke_admins)

    @antinuke.command(
        name='kick',
        usage='Syntax: /antinuke kick (on or off) <params>\nExample: /antinuke kick on --do stripstaff --threshold 3',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_kick(self, ctx: Context):
        """Prevent mass member kick. Run as a slash command."""
        await ctx.send_help(self.antinuke_kick)

    @antinuke.command(
        name='role',
        usage='Syntax: /antinuke role (on or off) <params>\nExample: /antinuke role on --do ban --threshold 3',
        extras={'permissions': ['Server Owner'], 'parameters': ['status', 'parameters']}
    )
    async def antinuke_role(self, ctx: Context):
        """Prevent mass role deletion. Run as a slash command."""
        await ctx.send_help(self.antinuke_role)

    #######################################################################################################
    #                                           COMMANDS                                                  #
    #######################################################################################################
    antinuke_group = Group(name='antinuke', description='Antinuke settings for a server')

    @antinuke_group.command(name='botadd', description='Enable or disable adding bots to your guild')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ])
    @is_antinuke_admin()
    @commands.guild_only()
    async def botadd(self, interaction: discord.Interaction, option: Choice[int]):
        """Enables/disables the bot add antinuke option"""
        try:
            enabled = await get_botadd_settings(interaction.guild.id)
            if enabled is None:
                await interaction.response.send_message("get botadd settings is none")
                return
            
            if enabled is option.value:
                if option.value:
                    opt_str = "enabled"
                else:
                    opt_str = "disabled"
                message = f"**Botadd** antinuke has been **{opt_str}** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
            
            val = await set_antinuke_setting(interaction.guild.id, 'botadd', option.value)
            if val:
                if option.value:
                    opt_str = "Enabled"
                else:
                    opt_str = "Disabled"
                message = f"{opt_str} **botadd** antinuke module"
                embed = make_embed_success(interaction.user, message)
                await interaction.response.send_message(embed=embed)
            else:
                message = f"Failed to update botadd antinuke module"
                embed = make_embed_error(interaction.user, message)
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"{type(e)} error in antinunke botadd: {e}")
            message = f"An error occurred: **{e}**"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    @antinuke_group.command(name='admin')
    @is_guild_owner()
    @commands.guild_only()
    async def admin(self, interaction: discord.Interaction, member: discord.Member):
        """Give a user permissions to edit antinuke settings"""
        antinuke_admins = await get_antinuke_admins(interaction.guild.id)
        is_admin = await self.is_antinuke_admin(interaction.guild.id, member.id)

        if is_admin and str(member.id) in antinuke_admins:
            antinuke_admins.remove(str(member.id))
            message = f"**{member}** is no longer an **antinuke admin**."
        else:
            antinuke_admins.append(str(member.id))
            message = f"**{member}** is now an **antinuke admin** and can edit **antinuke settings**."
        val = await set_antinuke_setting(interaction.guild.id, 'admins', json.dumps(antinuke_admins))
        if val:
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update antinuke admins"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='webhook')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def webhook(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass webhook creation"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'webhook')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke webhook: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        
        if ret is None:
            message = "Failed to get antinuke parameters"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        else:
            enabled_db, threshold_db, punishment_db = ret
        changed = False
        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **webhook** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Webhook** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Webhook antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **webhook** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **webhook** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'webhook', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update webhook antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='channel')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def channel(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass channel create and delete"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'channel')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke channel: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        if ret is not None:
            enabled_db, threshold_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **channel** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Channel** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Channel antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **channel** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **channel** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'channel', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update channel antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='vanity')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=0)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def vanity(self, interaction: discord.Interaction, option: Choice[int], punishment: Optional[Choice[int]]):
        """Punish users that change the server vanity"""

        try:
            ret = await get_vanity_settings(interaction.guild.id)
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke vanity: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        if ret is not None:
            enabled_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **vanity** antinuke module. Punishment is set to **{get_punishment(new_punishment)}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Vanity** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Vanity antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **vanity** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **vanity** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_punishment = punishment_db

        val = await set_vanity_settings(interaction.guild.id, option.value, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update vanity antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='admins')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def admins(self, interaction: discord.Interaction):
        """View all antinuke admins"""
        try:
            antinuke_admins = await get_antinuke_admins(interaction.guild.id)
            embed = await self.make_embed_antinuke_admins(interaction.user, antinuke_admins)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke admins: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='emoji')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def emoji(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass emoji delete"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'emoji')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke emoji: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        if ret is None:
            await interaction.response.send_message("get emoji settings is none")
            return
        enabled_db, threshold_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **emoji** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Emoji** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Emoji antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **emoji** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **emoji** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'emoji', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update emoji antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    # not done
    @antinuke_group.command(name='permissions')
    @app_commands.choices(action=[
        Choice(name='grant', value=True),
        Choice(name='remove', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    async def permissions(self, interaction: discord.Interaction, action: Choice[int], permission: str, punishment: Optional[Choice[int]]):
        """Watch dangerous permissions being granted or removed"""

        try:
            if permission not in perm_list:
                view = ConfirmView(interaction)
                embed = make_embed_warning(
                    interaction.user, "You passed an **invalid permission name**, please click the button below to see a full list of permissions."
                )
                out = await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                view.response = out
                return
            
            ret = await get_permissions_settings(interaction.guild.id)
            if ret is None:
                await interaction.response.send_message("get perms settings is none")
                return
            _, _, _, perms_grant, perms_remove, punishment_db = ret
            new_punishment = punishment_db
            state = ""

            if action.name == 'grant':
                if permission in perms_grant:
                    perms_grant.remove(permission)
                else:
                    perms_grant.append(permission)
                state = "granting"
            else:
                if permission in perms_remove:
                    perms_grant.remove(permission)
                else:
                    perms_grant.append(permission)
                state = "removal"

            if punishment is not None:
                new_punishment = punishment.value
            
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "UPDATE antinuke_system SET perms_grant = %s, perms_remove = %s, perms_pun = %s WHERE guild_id = %s;",
                        (json.dumps(perms_grant), json.dumps(perms_remove), new_punishment, interaction.guild.id)
                    )
                    await conn.commit()
            message = f"Now monitoring **{state} of** permission `{permission}`. Members **manually** giving out roles to others will be punished with `{get_punishment(new_punishment)}`"
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"{type(e)} error in antinuke permissions: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    # not done
    @antinuke_group.command(name='list')
    @is_antinuke_admin()
    async def list(self, interaction: discord.Interaction):
        """View all enabled modules along with whitelisted members & bots"""

        await interaction.response.defer()
        try:
            vanity_enabled, vanity_punishment = await get_vanity_settings(interaction.guild.id)
            botadd_enabled = await get_botadd_settings(interaction.guild.id)
            await interaction.followup.send(f"Botadd enabled: **{botadd_enabled}**\nVanity settings: enabled **{vanity_enabled}**, punishment: **{get_punishment(vanity_punishment)}**")
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke list: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.followup.send(embed=embed)

    @antinuke_group.command(name='ban')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def ban(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass member ban"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'ban')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke ban: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        if ret is None:
            await interaction.response.send_message("get ban settings is none")
            return
        enabled_db, threshold_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **ban** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Ban** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Ban antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **ban** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **ban** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'ban', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update ban antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='kick')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def kick(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass member kick"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'kick')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke kick: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        if ret is None:
            await interaction.response.send_message("get kick settings is none")
            return
        enabled_db, threshold_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **kick** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Kick** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Kick antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **kick** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **kick** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'kick', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update kick antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='role')
    @app_commands.choices(option=[
        Choice(name='on', value=True),
        Choice(name='off', value=False)
    ],
        punishment=[
            Choice(name='stripstaff', value=0),
            Choice(name='kick', value=1),
            Choice(name='ban', value=2),
        ]
    )
    @is_antinuke_admin()
    @commands.guild_only()
    async def role(self, interaction: discord.Interaction, option: Choice[int], threshold: Optional[int], punishment: Optional[Choice[int]]):
        """Prevent mass role delete"""

        try:
            ret = await get_antinuke_parameters(interaction.guild.id, 'role')
        except Exception as e:
            logger.error(f"{type(e)} error in antinuke role: {e}")
            message = f"{type(e)} Error: {e} "
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)
            return
        
        if ret is None:
            await interaction.response.send_message("get role settings is none")
            return
        enabled_db, threshold_db, punishment_db = ret
        changed = False

        if enabled_db is option.value:
            if enabled_db is True:
                if threshold is not None:
                    if threshold != threshold_db:
                        new_threshold = threshold
                        changed = True
                    else:
                        new_threshold = threshold_db
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    if punishment.value != punishment_db:
                        new_punishment = punishment.value
                        changed = True
                    else:
                        new_punishment = punishment_db
                else:
                    new_punishment = punishment_db
                if changed:
                    message = f"Updated **role** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                    embed = make_embed_success(interaction.user, message)
                else:
                    message = "**Role** antinuke has been **enabled** already"
                    embed = make_embed_warning(interaction.user, message)
                    await interaction.response.send_message(embed=embed)
                    return

                if changed is False:
                    await interaction.response.send_message(embed=embed)
                    return

            elif enabled_db is False:
                message = "Role antinuke has been **disabled** already"
                embed = make_embed_warning(interaction.user, message)
                await interaction.response.send_message(embed=embed)
                return
        else:
            if option.value is True:
                if threshold is not None:
                    new_threshold = threshold
                else:
                    new_threshold = threshold_db
                if punishment is not None:
                    new_punishment = punishment.value
                else:
                    new_punishment = punishment_db
                message = f"Updated **role** antinuke module.\nPunishment is set to **{get_punishment(new_punishment)}** and threshold is set to **{new_threshold}**"
                embed = make_embed_success(interaction.user, message)
            else:
                message = "Disabled **role** antinuke module"
                embed = make_embed_success(interaction.user, message)
                new_threshold = threshold_db
                new_punishment = punishment_db

        val = await set_antinuke_parameters(interaction.guild.id, 'role', option.value, new_threshold, new_punishment)
        if val:
            await interaction.response.send_message(embed=embed)
        else:
            message = f"Failed to update role antinuke module"
            embed = make_embed_error(interaction.user, message)
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='config')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def config(self, interaction: discord.Interaction):
        """View server configuration for Antinuke"""
        role_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'role')
        webhook_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'webhook')
        emoji_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'emoji')
        vanity_enabled, _ = await get_vanity_settings(interaction.guild.id)
        channel_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'channel')
        kick_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'kick')
        ban_enabled, _, _ = await get_antinuke_parameters(interaction.guild.id, 'ban')
        admins = await get_antinuke_admins(interaction.guild.id)
        admin_count = len(admins)
        whitelisted_humans, whitelisted_bots = [], []
        module_count = 5
        _, grant, remove, _  = await get_permissions_settings(interaction.guild.id)
        grant_len = len(grant)
        remove_len = len(remove)
        botadd_enabled = await get_botadd_settings(interaction.guild.id)
        
        def checked(value: bool) -> str:
            check = Emojis().get_emoji('approve')
            deny = Emojis().get_emoji('deny')
            return check if value else deny

        try:
            embed = discord.Embed(
                color=discord.Color.light_gray(),
                title="Settings",
                description="Antinuke is **enabled** in this server"
            )
            embed.add_field(
                name="Modules",
                value=f"**Role Deletion: {checked(role_enabled)}\nWebhook creation: {checked(webhook_enabled)}\n"
                      f"Emoji Deletion: {checked(emoji_enabled)}\nVanity Protection: {checked(vanity_enabled)}\n"
                      f"Channel Creation/Deletion: {checked(channel_enabled)}\nMass Member Kick: {checked(kick_enabled)}\nMass Member Ban: {checked(ban_enabled)}**"
            )
            embed.add_field(
                name="General",
                value=f"**Super Admins:** {admin_count}\n**Whitelisted Bots:** {whitelisted_bots}\n**Whitelisted Members:** {whitelisted_humans}\n"
                      f"**Protection Modules:** {module_count} enabled\n**Watch Permission Grant:** {grant_len}/{len(perm_list)} perms\n"
                      f"**Watch Permission Remove:** {remove_len}/{len(perm_list)} perms\n**Deny Bot Joins (botadd):** {checked(botadd_enabled)}"
            )
            embed.set_author(name=f"{interaction.user}", icon_url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Failed to get antinuke configuration: {e}")
            embed = make_embed_error(interaction.user, f"Failed to get antinuke configuration.")
            await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name='whitelist')
    @is_antinuke_admin()
    @commands.guild_only()
    async def whitelist(self, interaction: discord.Interaction, user: discord.User):
        """Whitelist a member from triggering antinuke or a bot to join"""
        try:
            is_whitelisted = await is_whitelisted(interaction.guild.id, user.id)
        except Exception as e:
            logger.error(f"Error in whitelist: {e}")
            embed = make_embed_error(interaction.user, f"Error in whitelist: {e}")
            await interaction.response.send_message(embed=embed)
            return
        whitelist = await get_whitelist(interaction.guild.id)
        if is_whitelisted and str(user.id) in whitelist:
            whitelist.remove(str(user.id))
            if user.bot:
                message = f"**{user}** is no longer whitelisted to join"
            else:
                message = f"**{user}** is no longer **whitelisted**."
        else:
            whitelist.append(str(user.id))
            if user.bot:
                message = f"**{user}** is now whitelisted and can join"
            else:
                message = f"**{user}** is now whitelisted and will not trigger **antinuke**"
        val = await set_antinuke_setting(interaction.guild.id, 'whitelist', json.dumps(whitelist))
        if val:
            embed = make_embed_success(interaction.user, message)
            await interaction.response.send_message(embed=embed)
        else:
            embed = make_embed_error(interaction.user, "Failed to whitelist user")
            await interaction.response.send_message(embed=embed)
 
    @staticmethod
    def make_embed_vanity_alert(member: discord.Member, guild: discord.Guild, vanity_before: str, vanity_after: str) -> discord.Embed:
        embed = discord.Embed(
            color=discord.Color.red(),
            description=f"Your server's vanity URL was changed in **{guild.name}**\n**{member}** changed `{vanity_before}` to `{vanity_after}`"
        )
        embed.set_footer(text="Note that bots do not have the ability to change vanities!")
        return embed

    async def make_embed_antinuke_admins(self, author: discord.Member, admins: List[str]) -> discord.Embed:
        admins_str = f""
        count = 0
        if len(admins) == 0:
            admins_str += "No antinuke admins."
        else:
            for admin in admins:
                count += 1
                user = await self.bot.fetch_user(int(admin))
                admins_str += f"`{count}` {user.mention}\n"
        embed = discord.Embed(
            description=admins_str,
            color=0x000001,
            title="Antinuke admins"
        )
        embed.set_author(name=author, icon_url=author.display_avatar.url)
        return embed 

    async def punish_moderator(self, member: discord.Member, punishment: int, reason: str):
        punishment = get_punishment(int(punishment))
        whitelisted = await is_whitelisted(member.guild, member)
        if whitelisted or member == member.guild.me or member == member.guild.owner:
            return
        if punishment == 'none':
            pass
        if punishment == "warn":
            await self.warn(member, member.guild, member.guild.me, reason)
        if punishment == "jail":
            await self.jail_member(member, reason)
        if punishment == "kick":
            try:
                await member.kick(reason=f"Kicked for {reason}")
            except Exception as e:
                logger.error(f"{type(e)} error in punish_moderator kick: {e}")
        if punishment == "ban":
            try:
                await member.ban(reason=f"Banned for {reason}")
            except Exception as e:
                logger.error(f"{type(e)} error in punish_moderator ban: {e}")
        if punishment == "stripstaff":
            await self.strip_staff(member)

    async def warn(self, member: discord.Member, guild: discord.Guild, moderator: discord.Member, reason: str):
        embed = make_embed_warn(guild, moderator, reason)
        dm_channel = await member.create_dm()
        try:
            await dm_channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error(f"Error in warn: {e}")

    async def strip_staff(self, member: discord.Member | discord.User):
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
            removed_roles = []
            roles_fail_bot = []
            for role in member.roles:
                if check_role_perms(role) and role.name != "@everyone":
                    if role >= member.guild.me.top_role or role.is_bot_managed():
                        roles_fail_bot.append(role)
                        continue

                    try:
                        await member.remove_roles(role)
                        removed_roles.append(role)
                    except (discord.Forbidden, discord.NotFound):
                        continue

    async def jail_member(self, member: discord.Member, reason):
        try:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM jail_system WHERE guild_id = %s;",
                        (member.guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        jailed_role_id = result['jailed_id']
                        jailed_role = member.guild.get_role(jailed_role_id)
                        jail_channel_id = result['jail_channel_id']
                        jail_channel = member.guild.get_channel(jail_channel_id)
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
            return

        try:
            if jailed_role_exists is False:
                warning_message = f"No **jailed** role was found, please run the `setup` command first"
                logger.error(warning_message)
                return

            if jail_channel_exists is False:
                warning_message = f"No **jail channel** was found, please run the `setup` command first"
                logger.error(warning_message)
                return

            if jailed_role >= member.guild.me.top_role:
                message = "The **jailed role** is higher than my top role! Please **move it below my top role**."
                logger.error(message)
                return

            # Try to jail a member
            role_check = member.get_role(jailed_role.id)
            # check if a member already has that role
            if role_check is None:  # means the member doesn't have that role
                await member.add_roles(jailed_role)
            else:  # means the member already has that role
                message = f"{member.mention} is already **jailed**!"
                logger.error(message)
                return

            await jail_channel.send(f"{member.mention} You have been jailed for **{reason}**")
        except Exception as e:
            logger.error(f"Error in {self.qualified_name} jail_member: {e}")
