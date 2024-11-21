import typing
from logging import getLogger 

import aiomysql
import discord
from discord.ext import commands, tasks

from bot import Sparky
from helpers import (
    Context,
    make_embed_progress,
    make_embed_error,
    make_embed_success,
    make_embed_mute
)

log = getLogger(__name__)

class Mute(commands.Cog):
    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            self.periodically_empty_muted_users.start()
            log.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            log.error(f"ERROR: Failed to initialize {self.qualified_name}: {e}")

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{SPEAKING HEAD IN SILHOUETTE}')
    
    @tasks.loop(minutes=30)
    async def periodically_empty_muted_users(self):
        try:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM muted_users WHERE is_muted = %s AND is_imuted = %s AND is_rmuted = %s;",
                        (False, False, False,)
                    )
        except aiomysql.MySQLError as e:
            log.error(f"Database error in {self.qualified_name} periodically_empty_muted_users: {e}")
        except Exception as e:
            log.error(f"Error in {self.qualified_name} periodically_empty_muted_users: {e}")

    @periodically_empty_muted_users.before_loop
    async def before_periodically_empty_muted_users(self):
        await self.bot.wait_until_ready()

    def cog_unload(self) -> None:
        self.periodically_empty_muted_users.cancel()
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            # Create a connection and a cursor with the database
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Check if the server has mute system setup
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (member.guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        # This means the server has the mute system setup
                        is_muted_setup = result['is_muted_setup']
                        if is_muted_setup:
                            # Get muted role IDs
                            muted_role_id = result['muted_id']
                            imuted_role_id = result['imuted_id']
                            rmuted_role_id = result['rmuted_id']
                            # check if the member is already in the database
                            await cur.execute(
                                "SELECT * FROM muted_users WHERE guild_id = %s AND member_id = %s;",
                                (member.guild.id, member.id,)
                            )
                            result = await cur.fetchone()
                            if result:
                                # If there are results in the database, that means the member was previously muted
                                member_is_muted = result['is_muted']
                                member_is_imuted = result['is_imuted']
                                member_is_rmuted = result['is_rmuted']
                                # Checking if the member was previously in a guild, got muted and then rejoined
                                # If any of these are found in the database, add those roles back
                                if member_is_muted:
                                    muted_role = member.guild.get_role(muted_role_id)
                                    await member.add_roles(muted_role)
                                if member_is_imuted:
                                    imuted_role = member.guild.get_role(imuted_role_id)
                                    await member.add_roles(imuted_role)
                                if member_is_rmuted:
                                    rmuted_role = member.guild.get_role(rmuted_role_id)
                                    await member.add_roles(rmuted_role)
        except Exception as e:
            log.error(f"Error in {self.qualified_name} on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, member_before: discord.Member, member_after: discord.Member):
        try:
            # Create a connection and a cursor with the database
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Check if the server has mute system setup
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (member_after.guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        muted_role_id = result['muted_id']
                        imuted_role_id = result['imuted_id']
                        rmuted_role_id = result['rmuted_id']

                        # muted role check
                        muted_role_check_before = member_before.get_role(muted_role_id)
                        muted_role_check_after = member_after.get_role(muted_role_id)
                        # imuted role check
                        imuted_role_check_before = member_before.get_role(imuted_role_id)
                        imuted_role_check_after = member_after.get_role(imuted_role_id)
                        # rmuted role check
                        rmuted_role_check_before = member_before.get_role(rmuted_role_id)
                        rmuted_role_check_after = member_after.get_role(rmuted_role_id)
                        changed_count = 0
                        if type(muted_role_check_before) != type(muted_role_check_after):
                            changed_count += 1
                        if type(imuted_role_check_before) != type(imuted_role_check_after):
                            changed_count += 1
                        if type(rmuted_role_check_before) != type(rmuted_role_check_after):
                            changed_count += 1

                        if changed_count == 0:
                            return

                        is_muted = True if muted_role_check_after else False
                        is_imuted = True if imuted_role_check_after else False
                        is_rmuted = True if rmuted_role_check_after else False
                        await cur.execute(
                            "UPDATE muted_users SET is_muted = %s, is_imuted = %s, is_rmuted = %s WHERE guild_id = %s AND member_id = %s;",
                            (is_muted, is_imuted, is_rmuted, member_after.guild.id, member_after.id,)
                        )
                        
                        count = cur.rowcount
                        if count == 0:
                            await cur.execute(
                                "INSERT INTO muted_users (guild_id, member_id, is_muted, is_imuted, is_rmuted) VALUES (%s, %s, %s, %s, %s);",
                                (member_after.guild.id, member_after.id, is_muted, is_imuted, is_rmuted,)
                            )
                            
        except aiomysql.MySQLError as e:
            log.error(f"Database error in {self.qualified_name} on_member_update: {e}")
        except Exception as e:
            log.error(f"Error in {self.qualified_name} on_member_update: {e}")

    # Function to set channel permission
    async def set_channel_perm(self, channel: discord.abc.GuildChannel, role: discord.Role, overwrite: discord.PermissionOverwrite):
        try:
            if not isinstance(channel, discord.CategoryChannel):
                await channel.set_permissions(role, overwrite=overwrite)
        except Exception as e:
            log.error(f"An error has occurred in setting {role} creation: {e}")

    @commands.command(name='setupmute')
    @commands.bot_has_guild_permissions(manage_guild=True, manage_channels=True, manage_roles=True)
    @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
    async def setup_mute_member(self, ctx: Context):
        message = "Starting the setup of the **mute system**. This might take a while..."
        progress_embed = make_embed_progress(ctx.author, message)
        progress_message = await ctx.send(progress_embed)
        try:
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    # get a list of column values from the database
                    muted_params = await cur.fetchone()
                    if muted_params:
                        # it was already setup before
                        muted_role_id = muted_params['muted_id']
                        imuted_role_id = muted_params['imuted_id']
                        rmuted_role_id = muted_params['rmuted_id']
                        is_already_setup = True
                    else:
                        # first time setup
                        is_already_setup = False
        except Exception as e:
            log.error(f"An error has occurred in {self.qualified_name} database check setupmute: {e}")
            message = "An error has occurred while checking the database"
            error_embed = make_embed_error(ctx.author, message)
            await progress_message.edit(embed=error_embed)
            return

        muted_role_exists = False
        imuted_role_exists = False
        rmuted_role_exists = False
        if is_already_setup:
            # check if muted roles already exist
            for role in ctx.guild.roles:
                if role.id == muted_role_id:
                    muted_role_exists = True
                elif role.id == imuted_role_id:
                    imuted_role_exists = True
                elif role.id == rmuted_role_id:
                    rmuted_role_exists = True
        try:
            # Creating the **text mute** role
            message = "Creating the **text mute** role"
            progress_embed = make_embed_progress(ctx.author, message)
            progress_message = await progress_message.edit(embed=progress_embed)
            # if the setupmute was already setup before
            if is_already_setup is True:
                # Check if imuted role exists
                if muted_role_exists:
                    muted_role = ctx.guild.get_role(muted_role_id)
                else:
                    muted_role = await ctx.guild.create_role(name="muted")
            else:
                muted_role = await ctx.guild.create_role(name="muted")

            # Create overwrites for muted role
            muted_overwrite = discord.PermissionOverwrite(send_messages=False, send_messages_in_threads=False,
                                                          create_public_threads=False, create_private_threads=False)
            for channel in ctx.guild.channels:
                await self.set_channel_perm(channel, muted_role, muted_overwrite)

        except Exception as e:
            log.error(f"An error has occurred in {self.qualified_name} text muted setupmute: {e}")
            message = "An error has occurred while creating the **text mute** role"
            error_embed = make_embed_error(ctx.author, message)
            await progress_message.edit(embed=error_embed)
            return

        try:
            # Creating the **image mute** role
            message = "Creating the **image mute** role"
            progress_embed = make_embed_progress(ctx.author, message)
            progress_message = await progress_message.edit(embed=progress_embed)
            # if the setupmute was already setup before
            if is_already_setup is True:
                # Check if muted role exists
                if imuted_role_exists:
                    imuted_role = ctx.guild.get_role(imuted_role_id)
                else:
                    imuted_role = await ctx.guild.create_role(name="imuted")
            else:
                imuted_role = await ctx.guild.create_role(name="imuted")

            # Create overwrites for muted role
            imuted_overwrite = discord.PermissionOverwrite(embed_links=False, attach_files=False)

            for channel in ctx.guild.channels:
                await self.set_channel_perm(channel, imuted_role, imuted_overwrite)

        except Exception as e:
            log.error(f"An error has occurred in {self.qualified_name} image muted setupmute: {e}")
            message = "An error has occurred while creating the **image mute** role"
            error_embed = make_embed_error(ctx.author, message)
            await progress_message.edit(embed=error_embed)
            return

        try:
            # Creating the **reaction and external emoji mute** role
            message = "Creating the **reaction and external emoji mute** role"
            progress_embed = make_embed_progress(ctx.author, message)
            progress_message = await progress_message.edit(embed=progress_embed)
            # if the setupmute was already setup before
            if is_already_setup is True:
                # Check if muted role exists
                if rmuted_role_exists:
                    rmuted_role = ctx.guild.get_role(rmuted_role_id)
                else:
                    rmuted_role = await ctx.guild.create_role(name="rmuted")
            else:
                rmuted_role = await ctx.guild.create_role(name="rmuted")

            # Create overwrites for muted role
            rmuted_overwrite = discord.PermissionOverwrite(add_reactions=False, use_external_emojis=False, use_external_stickers=False)

            for channel in ctx.guild.channels:
                await self.set_channel_perm(channel, rmuted_role, rmuted_overwrite)

        except Exception as e:
            log.error(f"An error has occurred in {self.qualified_name} reaction muted setupmute: {e}")
            message = "An error has occurred while creating the **reaction and external emoji mute** role"
            error_embed = make_embed_error(ctx.author, message)
            await progress_message.edit(embed=error_embed)
            return

        try:
            if is_already_setup:
                # set database values
                async with self.bot.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(
                            "UPDATE mute_system SET muted_id = %s, imuted_id = %s, rmuted_id = %s, is_muted_setup = %s WHERE guild_id = %s;",
                            (muted_role.id, imuted_role.id, rmuted_role.id, True, ctx.guild.id,)
                        )
                        
            else:
                async with self.bot.pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(
                            "INSERT INTO mute_system (guild_id, muted_id, imuted_id, rmuted_id, is_muted_setup) VALUES (%s, %s, %s, %s, %s);",
                            (ctx.guild.id, muted_role.id, imuted_role.id, rmuted_role.id, True,)
                        )
                        

        except Exception as e:
            log.error(f"An error has occurred in {self.qualified_name} database update setupmute: {e}")
            message = "An error has occurred while creating the **reaction and external emoji mute** role"
            error_embed = make_embed_error(ctx.author, message)
            await progress_message.edit(embed=error_embed)
            return

        message = "Muted setup **finished**! Permissions for **all channels** have been updated"
        success_embed = make_embed_success(ctx.author, message)
        await progress_message.edit(embed=success_embed)


    @commands.command(
        name='mute',
        aliases=['m'],
        usage='Syntax: mute <member> [reason]\nExample: mute anakin spreading hate',
        extras={'permissions': ['moderate_members']}
    )
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def mute_member(self, ctx: Context, member: discord.Member = None, *,
                          reason: typing.Optional[str] = "No reason provided"):

        # display help embed if command parameters are invalid
        if member is None and reason == "No reason provided":
            await ctx.send_help(self.mute_member)
            return
        try:
            # Check the database if the guild has the muted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        muted_role_id = cur_result['muted_id']
                        muted_role = ctx.guild.get_role(muted_role_id)
                        if not muted_role:
                            muted_role_exists = False
                        else:
                            muted_role_exists = True
                    else:
                        muted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred in {self.qualified_name} database mute check: {e}")
            return

        try:
            if muted_role_exists is False:
                await ctx.warning(f"No **muted** role was found, please run the `{ctx.prefix}setupmute` command first")
                return

            if muted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **muted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and muted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **mute** yourself.")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **mute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return
            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **mute** someone **equal or higher** than you.")
                return

            # Try to mute members
            role_check = member.get_role(muted_role_id)
            # check if a member already has that role
            if role_check is None:
                await member.add_roles(muted_role)
            else:
                await ctx.warning(f"**{member}** is already muted")
                return

            await ctx.success(f"Succesfully muted {member.mention}\nReason: *{reason}*")
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")

    @commands.command(name='imute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def image_mute_member(self, ctx: Context, member: discord.Member = None, *,
                                reason: typing.Optional[str] = "No reason provided"):

        try:
            # Check the database if the guild has the imuted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        imuted_role_id = cur_result['imuted_id']
                        imuted_role = ctx.guild.get_role(imuted_role_id)
                        if not imuted_role:
                            imuted_role_exists = False
                        else:
                            imuted_role_exists = True
                    else:
                        imuted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
            return

        try:
            if imuted_role_exists is False:
                await ctx.warning(
                    f"No **imuted** role was found, please run the `{ctx.prefix}setupmute` command first"
                )
                return

            if imuted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **imuted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and imuted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **imute** yourself.")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **imute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return
            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **imute** someone **equal or higher** than you.")
                return

            # Try to imute members
            role_check = member.get_role(imuted_role_id)
            # check if a member already has that role
            if role_check is None:  # means the member doesn't have that role
                await member.add_roles(imuted_role)
            else:
                await ctx.warning(f"**{member}** is already imuted")
                return

            success_message = f"Successfully **imuted** {member.mention}\nReason: *{reason}*"
            embed = make_embed_mute(ctx.author, success_message)
            await ctx.send(embed)
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")

    @commands.command(name='rmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def reaction_mute_member(self, ctx: Context, member: discord.Member = None, *,
                                   reason: typing.Optional[str] = "No reason provided"):
        try:
            # Check the database if the guild has the rmuted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        rmuted_role_id = cur_result['rmuted_id']
                        rmuted_role = ctx.guild.get_role(rmuted_role_id)
                        if not rmuted_role:
                            rmuted_role_exists = False
                        else:
                            rmuted_role_exists = True
                    else:
                        rmuted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
            return

        try:
            if rmuted_role_exists is False:
                await ctx.warning(f"No **rmuted** role was found, please run the `{ctx.prefix}setupmute` command first")
                return

            if rmuted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **rmuted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and rmuted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **rmute** yourself.")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **rmute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return

            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **rmute** someone **equal or higher** than you.")
                return

            # Try to rmute members
            role_check = member.get_role(rmuted_role_id)
            # check if a member already has that role
            if role_check is None:  # means the member doesn't have that role
                await member.add_roles(rmuted_role)
            else:
                await ctx.warning(f"**{member}** is already rmuted")
                return

            success_message = f"Successfully **rmuted** {member.mention}\nReason: *{reason}*"
            embed = make_embed_mute(ctx.author, success_message)
            await ctx.send(embed)
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")

    @commands.command(name='unmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def unmute_member(self, ctx: Context, member: discord.Member = None, *,
                            reason: typing.Optional[str] = "No reason provided"):

        try:
            # Check the database if the guild has the muted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        muted_role_id = cur_result['muted_id']
                        muted_role = ctx.guild.get_role(muted_role_id)
                        if not muted_role:
                            muted_role_exists = False
                        else:
                            muted_role_exists = True
                    else:
                        muted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
            return

        try:
            if muted_role_exists is False:
                await ctx.warning(f"No **muted** role was found, please run the `{ctx.prefix}setupmute` command first")
                return

            if muted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **muted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and muted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **unmute** yourself.")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **unmute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return

            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **unmute** someone **equal or higher** than you.")
                return

            # Try to mute member
            role_check = member.get_role(muted_role_id)

            # check if a member already has that role
            if role_check is not None:  # means the member has that role
                await member.remove_roles(muted_role)
            else:  # means the member doesn't have that role
                await ctx.warning(f"**{member}** is not muted")
                return

            success_message = f"Successfully **unmuted** {member.mention}\nReason: *{reason}*"
            embed = make_embed_mute(ctx.author, success_message)
            await ctx.send(embed)
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")

    @commands.command(name='iunmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def image_unmute_member(self, ctx: Context, member: discord.Member = None, *,
                                  reason: typing.Optional[str] = "No reason provided"):

        try:
            # Check the database if the guild has the muted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        imuted_role_id = cur_result['imuted_id']
                        imuted_role = ctx.guild.get_role(imuted_role_id)
                        if not imuted_role:
                            imuted_role_exists = False
                        else:
                            imuted_role_exists = True
                    else:
                        imuted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
            return

        try:
            if imuted_role_exists is False:
                await ctx.warning("No **imuted** role was found, please run the `,setupmute` command first")
                return

            if imuted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **imuted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and imuted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **iunmute** yourself.")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **iunmute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return

            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **iunmute** someone **equal or higher** than you.")
                return

            # Try to mute member
            role_check = member.get_role(imuted_role_id)

            # check if a member already has that role
            if role_check is not None:  # means the member has that role
                await member.remove_roles(imuted_role)
            else:  # means the member doesn't have that role
                await ctx.warning(f"**{member}** is not imuted")
                return

            success_message = success_message = f"Restored **attach files & embed links** to {member.mention}\nReason: *{reason}*"
            embed = make_embed_mute(ctx.author, success_message)
            await ctx.send(embed)
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")

    @commands.command(name='runmute')
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(moderate_members=True)
    async def reaction_unmute_member(self, ctx: Context, member: discord.Member = None, *,
                                     reason: typing.Optional[str] = "No reason provided"):
        try:
            # Check the database if the guild has the muted role
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM mute_system WHERE guild_id = %s;",
                        (ctx.guild.id,)
                    )
                    cur_result = await cur.fetchone()
                    if cur_result:
                        rmuted_role_id = cur_result['rmuted_id']
                        rmuted_role = ctx.guild.get_role(rmuted_role_id)
                        if not rmuted_role:
                            rmuted_role_exists = False
                        else:
                            rmuted_role_exists = True
                    else:
                        rmuted_role_exists = False

        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
            return

        try:
            if rmuted_role_exists is False:
                await ctx.warning(f"No **rmuted** role was found, please run the `{ctx.prefix}setupmute` command first")
                return

            if rmuted_role >= ctx.guild.me.top_role:
                await ctx.warning("The **rmuted role** is higher than my top role! Please **move it below my top role**.")
                return

            # Check if the target member is the command author
            if member == ctx.author and rmuted_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **runmute** yourself")
                return

            if member == ctx.guild.owner and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **runmute the owner**.")
                return

            # Check if the member has admin perms
            if member.guild_permissions.administrator:
                await ctx.warning(f"**{member}** has administrator permission so this won't work")
                return

            # Check if the target member is higher than author
            if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.warning("You can't **runmute** someone **equal or higher** than you.")
                return
            # Try to mute members
            role_check = member.get_role(rmuted_role_id)

            # check if a member already has that role
            if role_check is not None:  # means the member has that role
                await member.remove_roles(rmuted_role)
            else:  # means the member doesn't have that role
                await ctx.warning(f"**{member}** is not rmuted")
                return

            success_message = f"Restored **add reactions & use external emotes** to {member.mention}\nReason: *{reason}*"
            embed = make_embed_mute(ctx.author, success_message)
            await ctx.send(embed)
        except Exception as e:
            await ctx.error(f"An error has occurred: {e}")
