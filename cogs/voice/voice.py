from typing import Optional
from logging import getLogger

import discord
from discord.ext import commands

from bot import Sparky
from helpers import (
    Context, 
    make_embed_info,
    make_embed_warning,
    make_embed_success,
    make_embed_lockdown,
    make_embed_visible,
    make_embed_progress
)
from .interface import *
from .db import *
from .decorators import *
from .helper import *
from .utils import *

SUPPORT_SERVER = "https://discord.gg/8MTyyEUsJb"

log = getLogger(__name__)
    
class Voicemaster(commands.Cog):
    """Voice controls for your server"""
    
    def __init__(self, bot):
        try:
            self.bot: Sparky = bot
            log.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            log.error(f"Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return VOICE

    ###############################################################################
    #                                           LISTENER                                                  #
    ###############################################################################

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # get the Join to Create channel
        try:
            voicemaster_channel_id = await get_voicemaster_setting(member.guild, "voice_channel_id")
        except Exception as e:
            log.error(f"Failed to get voice channel id: {e}")
            return
        # create a new channel if the user joins the Join to Create channel
        if after.channel and after.channel.id == voicemaster_channel_id:
            try:
                # create a new voice channel with settings from the database
                try:
                    voice_settings = await get_voicemaster_settings(member.guild)
                except Exception as e:
                    log.error(f"Failed to get voice settings: {e}")
                    return
                category_channel_ids = await get_category_channel_ids(member.guild)
                if category_channel_ids is not None:
                    custom_category_id = category_channel_ids[0]
                    default_category_id = category_channel_ids[1]
                    category_channel_id = custom_category_id if custom_category_id is not None else default_category_id
                else:
                    category_channel_id = None
                default_name = voice_settings[5]
                if "{user.name}" in default_name:
                    default_name = default_name.format(user=member)
                default_region = voice_settings[6]
                default_bitrate = voice_settings[7]
                category_channel = member.guild.get_channel(category_channel_id)
                overwrites = {
                    member: discord.PermissionOverwrite(connect=True, view_channel=True)
                }
                new_channel = await member.guild.create_voice_channel(
                    name=default_name,
                    category=category_channel,
                    user_limit=0,
                    bitrate=default_bitrate,
                    rtc_region=default_region,
                    reason="VoiceMaster channel creation",
                    overwrites=overwrites
                )

                # move the user to the new channel
                await member.move_to(new_channel)
                # create a database entry for the new channel
                await insert_custom_voice_channel(new_channel, member)
            except Exception as e:
                log.error(f"Failed to create voice channel: {e}")

        # delete custom voice channels if they are empty
        try:
            custom_channels = await get_custom_voice_channels(member.guild)
        except Exception as e:
            log.error(f"Failed to get custom voice channels: {e}")
            return
        # check if the current channel is a custom channel
        if before.channel and before.channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
            # check if the custom channel is empty
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="VoiceMaster channel deletion")
                    await delete_custom_voice_channel(before.channel)
                except Exception as e:
                    log.error(f"Failed to delete voice channel: {e}")

        # check if a user joins a custom voice channel that has automatic roles enabled or if the server has an auto role set
        if after.channel and after.channel.id in [custom_channel['channel_id'] for custom_channel in custom_channels]:
            default_role_id = await get_voicemaster_setting(member.guild, "default_role_id")
            channel_role = await get_custom_voice_channel_role(channel=after.channel)
            role_id = channel_role.id if channel_role is not None else default_role_id
            if role_id is not None:
                role = member.guild.get_role(role_id)
                if role is not None:
                    try:
                        await member.add_roles(role, reason="VoiceMaster role assignment")
                    except Exception as e:
                        log.error(f"Failed to assign role: {e}")

    ###############################################################################
    #                                           COMMANDS                                                  #
    ###############################################################################

    @commands.group(
        name="voicemaster",
        aliases=["voice", "vm", "vc"],
        usage="Syntax: voicemaster [subcommand] <args>\nExample: voicemaster setup",
        invoke_without_command=True
    )
    async def voicemaster(self, ctx: Context):
        """Make temporary voice channels in your server!"""
        await ctx.send_help(self.voicemaster)

    @voicemaster.command(
        name="status",
        usage="Syntax: voicemaster status [status]\nExample: voicemaster status just chilling",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_status(self, ctx: Context, *, status: Optional[str]):
        """Set a status for your voice channel"""
        if status is None:
            await ctx.send_help(self.voicemaster_status)
            return
        if len(status) > 500:
            status = status[:500]
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(status=status)
                await ctx.message.add_reaction("✅")
                return
            except Exception as e:
                log.error(f"Failed to set status: {e}")
                await ctx.message.add_reaction("❌")
                return
        raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="category",
        aliases=["cat"],
        usage="Syntax: voicemaster category <category>\nExample: voicemaster category 1298214103587749888",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def voicemaster_category(self, ctx: Context, category: Optional[discord.CategoryChannel]):
        """Redirect voice channels to custom category"""
        if category is None:
            category_channel_ids = await get_category_channel_ids(ctx.guild)
            if category_channel_ids is not None:
                custom_id = category_channel_ids[0]
                if custom_id is None:
                    await ctx.send_help(self.voicemaster_category)
                    return
                val = await set_category_channel_id(ctx.guild, None)
                if val:
                    await ctx.success("Set **VoiceMaster** category back to **default**")
                else:
                    await ctx.warning("Failed to reset category channel")
                return
            else:
                await ctx.warning("Failed to change category channel")
                return
        val = await set_category_channel_id(ctx.guild, category.id)
        if val:
            await ctx.success(f"New **VoiceMaster** channels will be created under **{category.name}**")
        else:
            await ctx.warning("Failed to set category channel")

    @voicemaster.command(
        name="limit",
        usage="Syntax: voicemaster limit <limit>\nExample: voicemaster limit 5"
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_limit(self, ctx: Context, limit: Optional[int]):
        """Set a member limit for your voice channel"""
        if limit is None:
            await ctx.send_help(self.voicemaster_limit)
            return
        if limit < 0 or limit > 99:
            await ctx.warning("**Channel limit** must be between `0` and `99` members")
            return
        voice_channels = ctx.guild.voice_channels
        for voice_channel in voice_channels:
            if ctx.author in voice_channel.members:
                try:
                    await voice_channel.edit(user_limit=limit)
                    await ctx.success(f"Your **voice channel**'s limit has been updated to `{limit}`")
                except Exception as e:
                    log.error(f"Failed to set limit: {e}")
                    await ctx.error("Failed to set limit for the **voice channel**")

    @voicemaster.command(
        name="ghost",
        aliases=["hide"],
        usage="Syntax: voicemaster ghost"
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_ghost(self, ctx: Context):
        """Hide your voice channel"""
        try:
            val = await helper_ghost_channel(ctx.guild, ctx.author)
            if val:
                message = "Your **voice channel** is now **ghosted**"
                embed = make_embed_visible(ctx.author, False, message)
                await ctx.send(embed)
            else:
                await ctx.warning("Failed to **hide** the **voice channel**")
        except Exception as e:
            log.error(f"Failed to ghost channel: {e}")
            await ctx.error("Failed to **hide** the **voice channel**")

    @voicemaster.command(
        name="claim",
        usage="Syntax: voicemaster claim"
    )
    @is_voice_member()
    async def voicemaster_claim(self, ctx: Context):
        """Claim an inactive voice channel"""
        # check if an owner is already present in the channel
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                custom_channels = await get_custom_voice_channels(ctx.guild)
            except Exception as e:
                log.error(f"Failed to get custom channels: {e}")
                await ctx.warning("Failed to **claim** the **voice channel**")
                return
            for custom_channel in custom_channels:
                if custom_channel['channel_id'] == voice_channel.id:
                    owner_id = custom_channel['owner_id']
                    if owner_id == ctx.author.id:
                        await ctx.warning("You already have **ownership** of this **voice channel**")
                        return
                    if owner_id in [member.id for member in voice_channel.members]:
                        await ctx.warning("You can't claim this **voice channel** - the owner is still active here")
                        return
                    try:
                        await transfer_custom_voice_channel(voice_channel, ctx.author)
                        await ctx.success("You have **claimed** this **voice channel**")
                    except Exception as e:
                        log.error(f"Failed to claim channel: {e}")
                        await ctx.warning("Failed to **claim** the **voice channel**")
                    return
        raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="transfer",
        usage="Syntax: voicemaster transfer <user>\nExample: voicemaster transfer @Sparky",
    )
    @is_voice_owner()
    async def voicemaster_transfer(self, ctx: Context, user: Optional[discord.Member]):
        """Transfer ownership of your channel to another member"""        
        user_channel = await get_users_voice_channel(user)
        if user_channel is None:
            await ctx.warning(f"{user.mention} is not connected to a **voice channel**")
            return
        owner_channel = await get_users_voice_channel(ctx.author)
        if owner_channel is None:
            await ctx.warning("You're not connected to a **voice channel**")
            return
        if user_channel == owner_channel:
            try:
                if user.id == ctx.author.id:
                    await ctx.warning("You already own this **voice channel**!")
                    return
                if user.id not in [member.id for member in user_channel.members]:
                    await ctx.warning("You can't transfer **ownership** to a member who is not active in this **voice channel**")
                    return
                await transfer_custom_voice_channel(owner_channel, user)
                await ctx.success(f"**Ownership** of the voice channel has been transferred to {user.mention}")
            except Exception as e:
                log.error(f"Failed to transfer ownership: {e}")
                await ctx.warning("Failed to transfer **ownership**")
        else:
            await ctx.warning("You can only **transfer ownership** to users in your **voice channel**")

    @voicemaster.command(
        name="unghost",
        aliases=["unhide"],
        usage="Syntax: voicemaster unghost"
    )
    @is_voice_owner()
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def voicemaster_unghost(self, ctx: Context):
        """Unhide your voice channel"""
        val = await helper_reveal_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **visible**"
            embed = make_embed_visible(ctx.author, True, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **reveal** the **voice channel**")

    @voicemaster.group(
        name="default",
        aliases=["def"],
        usage="Syntax: voicemaster default [subcommand] <args>\nExample: voicemaster default region us-west",
        extras={"permissions": ["Manage Guild & Roles"]},
        invoke_without_command=True
    )
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_default(self, ctx: Context):
        """Configure the default settings for VM channels"""
        await ctx.send_help(ctx.command)

    @voicemaster_default.command(
        name="role",
        usage="Syntax: voicemaster default role <role>\nExample: voicemaster default role @Member",
        extras={"permissions": ["Manage Guild & Roles"]}
    )
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_default_role(self, ctx: Context, role: Optional[discord.Role]):
        """Set default role for voice channels"""
        if role is None:
            await ctx.warning("I couldn't find the **default join role**, try setting it by providing a role")
            return
        val = await set_voicemaster_setting(ctx.guild, "default_role_id", role.id)
        if val:
            await ctx.success(f"Set {role.mention} as the **default role** for **VoiceMaster** channels")
        else:
            await ctx.warning("Failed to set **default role**")

    @voicemaster_default.command(
        name="name",
        usage="Syntax: voicemaster default name <name>\nExample: voicemaster default name {user.name}'s vc",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_name(self, ctx: Context, name: Optional[str]):
        """Set default name for new Voice Channels"""
        try:
            db_name = await get_voicemaster_setting(ctx.guild, "default_name")
        except Exception as e:
            log.error(f"Failed to get default name: {e}")
            await ctx.error("Failed to get **default name**")
            return
        default_name = "{user.name}'s channel"
        if name is None and db_name == default_name:
            await ctx.send_help(self.voicemaster_default_name)
            return
        if name is None and db_name != default_name:
            await set_voicemaster_setting(ctx.guild, "default_name", "{user.name}'s channel")
            await ctx.success("Reset the **default name** for **VoiceMaster** channels")
            return
        await set_voicemaster_setting(ctx.guild, "default_name", name)
        await ctx.success(f"Set **default name** for **VoiceMaster** channels to `{name}`")

    @voicemaster_default.command(
        name="region",
        usage="Syntax: voicemaster default region [region]\nExample: voicemaster default region russia",
        extras={"permissions": ["Manage Guild"], "information": ["Use option 'regions' to see available regions"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_region(self, ctx: Context, region: Optional[str] = None):
        """Edit default region for new Voice Channels"""
        region = region.lower() if region is not None else None
        region_list = ["automatic", "brazil", "europe", "hongkong", "india", "japan", "russia", "singapore", "southafrica", "sydney", "us-central", "us-east", "us-south", "us-west"]
        if region == "regions":
            message = f"**Voice regions** are: `{', '.join(region_list)}`"
            info_embed = make_embed_info(ctx.author, message)
            await ctx.send(info_embed)
            return
        try:
            db_region = await get_voicemaster_setting(ctx.guild, "default_region")
        except Exception as e:
            log.error(f"Failed to get default region: {e}")
            await ctx.error("Failed to get **default region**")
            return
    
        if db_region is False:
            await ctx.warning("Failed to get **default region**")
            return
        if region is None and db_region is None:
            await ctx.send_help(self.voicemaster_default_region)
            return
        if region is None and db_region is not None:
            await set_voicemaster_setting(ctx.guild, "default_region", None)
            await ctx.success("Updated **default region** to `automatic` for **VM channels**")
            return
        if region not in region_list:
            await ctx.warning(f"**Voice region** must be one of the following: `{', '.join(region_list)}`")
            return
        if region == "automatic":
            region = None
        region_name = region if region is not None else "automatic"
        await set_voicemaster_setting(ctx.guild, "default_region", region)
        await ctx.success(f"Updated **default region** to `{region_name}` for **VM channels**")

    @voicemaster_default.command(
        name="bitrate",
        usage="Syntax: voicemaster default bitrate <bitrate>\nExample: voicemaster default bitrate 80",
        extras={"permissions": ["Manage Guild"], "information": ["Bitrate must be between 8 and 96 kbps"]}
    )
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_default_bitrate(self, ctx: Context, bitrate: Optional[int]):
        """Set default bitrate for voice channels"""
        if bitrate < 8 or bitrate > 96:
            await ctx.warning("**Bitrate** must be between `8` and `96` kbps")
            return
        await set_voicemaster_setting(ctx.guild, "default_bitrate", bitrate)
        await ctx.success(f"Updated **default bitrate** to `{bitrate}` for **VM channels**")

    @voicemaster.command(
        name="setup",
        usage="Syntax: voicemaster setup",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_setup(self, ctx: Context):
        """Begin VoiceMaster server configuration setup"""
        try:
            is_setup = await get_voicemaster_setting(ctx.guild, "is_setup")
        except Exception as e:
            log.error(f"Failed to get voicemaster settings: {e}")
            await ctx.warning(f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})")
            return
        if is_setup:
            message = "Server is already configured for **VoiceMaster**, run `voicemaster reset` to reset the **VoiceMaster** server configuration"
            warning_embed = make_embed_warning(ctx.author, message)
            await ctx.warning(f"Server is already configured for **VoiceMaster**, run `{ctx.prefix}voicemaster reset` to reset the **VoiceMaster** server configuration")
            return
        if is_setup is None:
            # Voicemaster configuration not found for this server
            in_database = False
        else:
            in_database = True
        message = "Starting VoiceMaster setup..."
        progress_embed = make_embed_progress(ctx.author, message)
        progress_message = await ctx.send(progress_embed)
        guild_channel_count = len(ctx.guild.channels)
        if guild_channel_count > 497:
            message = "VoiceMaster requires at least 3 free channels to setup. Please delete some channels and try again."
            warning_embed = make_embed_warning(ctx.author, message)
            await progress_message.edit(embed=warning_embed)
            return
        
        try:
            # Create category channel
            category_channel = await ctx.guild.create_category(name="Voice Channels", reason="VoiceMaster setup")
            # Create text channel with permissions
            text_overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False, 
                    send_messages_in_threads=False, 
                    create_public_threads=False, 
                    create_private_threads=False, 
                    add_reactions=False
                )
            }
            interface_channel = await ctx.guild.create_text_channel(
                name="interface", 
                category=category_channel, 
                reason="VoiceMaster setup", 
                overwrites=text_overwrites
            )
            log.info(f"Created interface channel: {interface_channel}")
            await self.create_interface(interface_channel)
            # Create voice channel
            voice_overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False
                )
            }
            voice_channel = await ctx.guild.create_voice_channel(
                name="Join to Create", 
                category=category_channel, 
                reason="VoiceMaster setup", 
                overwrites=voice_overwrites
            )
            log.info(f"Created voice channel: {voice_channel}")
            # put category channel, interface channel and voice channel ID's in database
            if in_database:
                await set_voicemaster_setting(ctx.guild, "is_setup", True)
            else:
                val = await initialize_voicemaster(ctx.guild)
                if val is False:
                    log.error("Failed to initialize VoiceMaster")
                    message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
                    warning_embed = make_embed_warning(ctx.author, message)
                    await progress_message.edit(embed=warning_embed)
                    return
            val_category = await init_category_channel_ids(ctx.guild, category_channel.id)
            log.info(f"val_category: {val_category}")
            val_interface = await set_voicemaster_setting(ctx.guild, "interface_channel_id", interface_channel.id)
            log.info(f"val_interface: {val_interface}")
            val_voice = await set_voicemaster_setting(ctx.guild, "voice_channel_id", voice_channel.id)
            log.info(f"val_voice: {val_voice}")
            if not val_category or not val_interface or not val_voice:
                log.error("Failed to initialize VoiceMaster")
                message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
                warning_embed = make_embed_warning(ctx.author, message)
                await progress_message.edit(embed=warning_embed)
                return
        except Exception as e:
            message = f"Failed to initialize **VoiceMaster**. Please contact support in the [__support server__]({SUPPORT_SERVER})"
            warning_embed = make_embed_warning(ctx.author, message)
            await progress_message.edit(embed=warning_embed)
            return
        message = "Finished setting up the **VoiceMaster** channels. A category and two channels have been created, you can move the channels or rename them if you want."        
        embed = make_embed_success(ctx.author, message)
        await progress_message.edit(embed=embed)

    @voicemaster.command(
        name="configuration",
        aliases=["config", 'info'],
        usage="Syntax: voicemaster configuration",
    )
    @is_voice_member()
    async def voicemaster_configuration(self, ctx: Context):
        """Show Voicemaster configuration"""
        embed = await helper_view_channel(ctx.guild, ctx.author)
        if embed:
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to view the **VoiceMaster** configuration")

    @voicemaster.command(
        name="reset",
        aliases=["resetserver"],
        usage="Syntax: voicemaster reset",
        extras={"permissions": ["Manage Guild"]}
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True)
    # @commands.cooldown(1, 20, commands.BucketType.guild)
    async def voicemaster_reset(self, ctx: Context):
        """Reset server configuration for VoiceMaster"""
        log.info(f"Resetting VoiceMaster for {ctx.guild}")
        
        category_channel_ids = await get_category_channel_ids(ctx.guild)
        if category_channel_ids is not None:
            log.info(f"category_channel_ids: {category_channel_ids}")
            default_category_id = category_channel_ids[1]
            category_channel = ctx.guild.get_channel(default_category_id)
            try:
                await category_channel.delete(reason="VoiceMaster reset")
                log.info("Deleted VoiceMaster category channel")
            except Exception as e:
                log.error(f"Failed to delete category channel: {e}")
        else:
            log.error("Failed to get category channel ID")
        try:
            interface_channel_id = await get_voicemaster_setting(ctx.guild, "interface_channel_id")
        except Exception as e:
            log.error(f"Failed to get interface channel ID: {e}")
            return
        if interface_channel_id is not None:
            interface_channel = ctx.guild.get_channel(interface_channel_id)
            try:
                await interface_channel.delete(reason="VoiceMaster reset")
                log.info("Deleted VoiceMaster interface channel")
            except Exception as e:
                log.error(f"Failed to delete interface channel: {e}")
        else:
            log.error("Failed to get interface channel ID")
        try:
            voice_channel_id = await get_voicemaster_setting(ctx.guild, "voice_channel_id")
        except Exception as e:
            log.error(f"Failed to get voice channel ID: {e}")
            return
        if voice_channel_id is not None:
            voice_channel = ctx.guild.get_channel(voice_channel_id)
            try:
                await voice_channel.delete(reason="VoiceMaster reset")
                log.info("Deleted VoiceMaster voice channel")
            except Exception as e:
                log.error(f"Failed to delete voice channel: {e}")
        else:
            log.error("Failed to get voice channel ID")
        log.info("Deleted VoiceMaster channels")
        reset = await reset_voicemaster_settings(ctx.guild)
        if reset:
            log.info("Reset VoiceMaster settings")
            await ctx.success("Reset the **VoiceMaster** configuration.")
        else:
            log.info("Failed to reset VoiceMaster settings")
            await ctx.warning(f"**VoiceMaster** server configuration was not found. Run `{ctx.prefix}voicemaster setup` to configure **VoiceMaster**.")

    @voicemaster.command(
        name="lock",
        usage="Syntax: voicemaster lock",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_lock(self, ctx: Context):
        """Lock your voice channel"""
        val = await helper_lock_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **locked**"
            embed = make_embed_lockdown(ctx.author, True, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **lock** the **voice channel**")

    @voicemaster.command(
        name="unlock",
        usage="Syntax: voicemaster unlock",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_unlock(self, ctx: Context):
        """Unlock your voice channel"""
        val = await helper_unlock_channel(ctx.guild, ctx.author)
        if val:
            message = "Your **voice channel** is now **unlocked**"
            embed = make_embed_lockdown(ctx.author, False, message)
            await ctx.send(embed)
        else:
            await ctx.warning("Failed to **unlock** the **voice channel**")

    @voicemaster.command(
        name="role",
        aliases=["roles"],
        usage="Syntax: voicemaster role <role>\nExample: voicemaster role @Member",
        extras={"permissions": ["manage roles"]}
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def voicemaster_role(self, ctx: Context, role: Optional[discord.Role]):
        """Grant roles to members who join and remove from members leaving"""
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is None:
            raise NotVoiceMember("You're not connected to a **voice channel**")

        if role is None:
            db_role = await get_custom_voice_channel_role(voice_channel)
            if db_role is None:
                await ctx.send_help(self.voicemaster_role)
                return
            try:
                default_role_id = await get_voicemaster_setting(ctx.guild, "default_role_id")
            except Exception as e:
                log.error(f"Failed to get default role: {e}")
                await ctx.warning("Failed to get **default role**")
                return
            if default_role_id is None:
                await ctx.warning("Failed to get **default role**")
                return
            val = await set_custom_voice_channel_role(voice_channel, default_role_id)
            if val:
                await ctx.success("Reset the **role** for the **voice channel**")
            else:
                await ctx.warning("Failed to reset the **role** for the **voice channel**")
            return
        
        if role >= ctx.guild.me.top_role:
            await ctx.warning(f"{role.mention} is **higher** than my highest role")
            return
        
        if role >= ctx.author.top_role:
            await ctx.warning(f"{role.mention} is **too high** for you to manage")
            return
        
        # assign role to all members in the channel and all the future members
        val = await set_custom_voice_channel_role(voice_channel, role.id)
        if val:
            log.info(f"Set role for voice channel: {role}")
        else:
            log.error("Failed to set role for voice channel")

        success = 0
        failed = 0
        for member in voice_channel.members:
            try:
                await member.add_roles(role, reason="VoiceMaster role assignment")
                success += 1
            except Exception as e:
                log.error(f"Failed to assign role: {e}")
                failed += 1
        message = f"Succesfully assigned {role.mention} to `{success}` members"
        if failed > 0:
            message += f" (`{failed}` failed)"

        await ctx.success(message)

    @voicemaster.command(
        name="bitrate",
        usage="Syntax: voicemaster bitrate <bitrate>\nExample: voicemaster bitrate 64",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_bitrate(self, ctx: Context, bitrate: Optional[int]):
        """Set bitrate for voice channels"""        
        if bitrate < 8 or bitrate > 96:
            await ctx.warning("**Bitrate** must be between `8` and `96` kbps")
            return
        
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(bitrate=bitrate*1000)
                await ctx.success(f"Set **bitrate** for **voice channel** to `{bitrate}` kbps")
            except Exception as e:
                log.error(f"Failed to set bitrate: {e}")
                await ctx.warning("Failed to set bitrate")

    @voicemaster.command(
        name="music",
        usage="Syntax: voicemaster music <on or off>\nExample: voicemaster music on",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_music(self, ctx: Context, *, option: Optional[str]):
        """Change your channel to a Music Only channel"""
        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.warning(f"Invalid **option**: `{option}`. Use `on` or `off`")
            return
        
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is None:
            raise NotVoiceMember("You're not connected to a **voice channel**")
        enabled_message = "Your **voice channel** is now a **music only channel**"
        disabled_message = "Your **voice channel** is no longer a **music only channel**"
        permission = False if option == "on" else None
        message = enabled_message if option == "on" else disabled_message
        music_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                speak=permission
            )
        }
        try:
            await voice_channel.edit(overwrites=music_overwrites)
        except Exception as e:
            log.error(f"Failed to set music only channel: {e}")
            await ctx.error("Failed to set music only channel")
        else:
            await ctx.success(message)

    @voicemaster.command(
        name="name",
        usage="Syntax: voicemaster name <name>\nExample: voicemaster name Jedi meeting room",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def voicemaster_name(self, ctx: Context, *, name: Optional[str]):
        """Set name for voice channels"""
        # get default name from database
        try:
            db_name = await get_voicemaster_setting(ctx.guild, "default_name")
        except Exception as e:
            log.error(f"Failed to get default name: {e}")
            return
        # if name is None and db_name is None, display help
        # if name is None and db_name is not None, set name to db_name
        # if name is not None, set name to name
        if name is None and db_name is None:
            await ctx.send_help(self.voicemaster_name)
            return
        if name is None and db_name is not None:
            name = db_name
            message = f"Successfully reset **name** for **voice channel** to `{name}`"
        if name is not None:
            message = f"Set **name** for **voice channel** to `{name}`"

        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.edit(name=name)
                await ctx.success(message)
            except Exception as e:
                log.error(f"Failed to set name: {e}")
                await ctx.warning("Failed to set name")

    @voicemaster.command(
        name="permit",
        usage="Syntax: voicemaster permit <user>\nExample: voicemaster permit @Sparky",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_permit(self, ctx: Context, user: Optional[discord.Member]):
        """Permit a user to join your voice channel"""
        overwrites = discord.PermissionOverwrite(connect=True, view_channel=True)
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            try:
                await voice_channel.set_permissions(user, overwrite=overwrites)
                await ctx.success(f"Permitted {user.mention} to **join** the **voice channel**")
            except Exception as e:
                log.error(f"Failed to permit user: {e}")
                await ctx.warning("Failed to permit user")
        else:
            raise NotVoiceMember("You're not connected to a **voice channel**")

    @voicemaster.command(
        name="reject",
        usage="Syntax: voicemaster reject <user>\nExample: voicemaster reject @Sparky",
    )
    @is_voice_owner()
    @commands.bot_has_permissions(manage_channels=True)
    async def voicemaster_reject(self, ctx: Context, user: Optional[discord.Member]):
        """Reject a user from joining your voice channel"""
        overwrites = discord.PermissionOverwrite(connect=False, view_channel=False)
        voice_channel = await get_users_voice_channel(ctx.author)
        if voice_channel is not None:
            if user.id == ctx.author.id:
                await ctx.warning("You can't reject yourself from joining the **voice channel**")
                return
            if user.id in [member.id for member in voice_channel.members]:
                try:
                    # disconnect user from voice channel
                    await user.move_to(None)
                except Exception as e:
                    log.error(f"Failed to disconnect user: {e}")
                    await ctx.warning(f"Failed to disconnect user {user.mention}")
                    return
            try:
                await voice_channel.set_permissions(user, overwrite=overwrites)
                await ctx.success(f"Rejected {user.mention} from **joining** the **voice channel**")
            except Exception as e:
                log.error(f"Failed to reject user: {e}")
                await ctx.error("Failed to reject user")
        else:
            raise NotVoiceMember("You're not connected to a **voice channel**")

    ###############################################################################
    #                                          INTERFACE                                                  #
    ###############################################################################

    async def create_interface(self, interface_channel: discord.TextChannel):
        """Create the interface for the voice channel"""
        try:
            embed = discord.Embed(
                title="VoiceMaster Interface",
                description="Click the buttons below to control your voice channel",
                color=discord.Color(0x69919d),
                type='rich'
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            invite_link = "https://discord.gg/8MTyyEUsJb"
            embed.add_field(
                name='**Button Usage**',
                value=
                    f"<{LOCK}> — [`Lock`]({invite_link}) the voice channel\n"
                    f"<{UNLOCK}> — [`Unlock`]({invite_link}) the voice channel\n"
                    f"<{GHOST}> — [`Ghost`]({invite_link}) the voice channel\n"
                    f"<{REVEAL}> — [`Reveal`]({invite_link}) the voice channel\n"
                    f"<{CLAIM}> — [`Claim`]({invite_link}) the voice channel\n"
                    f"<{DISCONNECT}> — [`Disconnect`]({invite_link}) a member\n"
                    f"<{START}> — [`Start`]({invite_link}) an activity\n"
                    f"<{VIEW}> — [`View`]({invite_link}) channel information\n"
                    f"<{INCREASE}> — [`Increase`]({invite_link}) the user limit\n"
                    f"<{DECREASE}> — [`Decrease`]({invite_link}) the user limit",
                inline=True
            )
            if interface_channel.guild.icon:
                icon_url = interface_channel.guild.icon.url
            else:
                icon_url = None
            embed.set_author(name=interface_channel.guild.name, icon_url=icon_url)
            interface_view = InterfaceView(self.bot)
            await interface_channel.send(embed=embed, view=interface_view)
        except Exception as e:
            log.error(f"Failed to create interface: {e}")
            await interface_channel.send("Failed to create interface")
