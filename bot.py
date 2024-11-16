from __future__ import annotations
import os
from pathlib import Path
import aiomysql
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Optional, Any
import logging
from helpers import (
    Context, 
    Emojis,
    get_pool,
    handle_extension_error,
    handle_bad_argument,
    handle_bad_union_argument,
    handle_bad_literal_argument,
    handle_disabled_command,
    handle_argument_parsing_error,
    handle_check_failure,
    handle_command_on_cooldown
)


if TYPE_CHECKING:
    from cogs.misc.misc import Misc as MiscCog
    from cogs.voice.voice import Voicemaster
    from cogs.antinuke.antinuke import Antinuke

load_dotenv()
DEFAULT_PREFIX = ','

log = logging.getLogger(__name__)

description = "A little, cute bot that will grow up and do all sorts of great things!"

MISC_COG: str = "Misc"
VOICEMASTER: str = "Voicemaster"
misc_filename = "misc"

class Sparky(commands.Bot):
    user: discord.ClientUser
    pool: aiomysql.Pool
    bot_app_info: discord.AppInfo
    logging_handler: Any

    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            roles=False,
            everyone=False,
            users=True,
            replied_user=False
        )
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            messages=True,
            reactions=True,
            message_content=True,
            voice_states=True
        )
        super().__init__(
            command_prefix=_get_prefix, 
            description=description,
            allowed_mentions=allowed_mentions,
            intents=intents,
            strip_after_prefix=True,
            case_insensitive=True
        )
        self.client_id: str = os.getenv('CLIENT_ID')
        self.spam_control = commands.CooldownMapping.from_cooldown(1, 2, commands.BucketType.user)

    async def on_ready(self):
        log.info(f"We have logged in as {self.user}")
        self.loop.create_task(self.after_ready())

    async def after_ready(self):
        game_name = "discord.py"
        game = discord.Game(name=game_name)
        await self.change_presence(status=discord.Status.idle, activity=game)

    async def setup_hook(self) -> None:
        self.pool = await get_pool()
        loaded_count = 0
        total_count = 0
        cogs_path = Path('cogs')
        if not cogs_path.exists():
            raise FileNotFoundError("The cogs directory does not exist.")

        for category in cogs_path.iterdir():
            if not category.is_dir():
                continue
            elif not (category / "__init__.py").is_file():
                continue
            total_count += 1

        for category in cogs_path.iterdir():
            if not category.is_dir():
                continue
            elif not (category / "__init__.py").is_file():
                continue
            try:
                # ignore the __pycache__ directory
                # join the path to the category excluding __pycache__ and load the extension
                await self.load_extension('.'.join(category.parts)) 
                loaded_count += 1
            except Exception as e:
                log.error(f"ERROR occurred in setup_hook while loading {category.name}: {e}")
        log.info(f"Successfully loaded {loaded_count}/{total_count} extensions.")

    async def on_shutdown(self):
        self.pool.close()
        await self.pool.wait_closed()

    async def on_command_error(self, ctx: Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, commands.ExtensionError):
                await handle_extension_error(ctx, error.original)
            else:
                log.error(f"An error occurred in on_command_error: {type(error)}: {error}")
        elif isinstance(error, commands.BadArgument):
            await handle_bad_argument(ctx, error)
        elif isinstance(error, commands.BadUnionArgument):
            await handle_bad_union_argument(ctx, error)
        elif isinstance(error, commands.BadLiteralArgument):
            await handle_bad_literal_argument(ctx, error)
        elif isinstance(error, commands.DisabledCommand):
            await handle_disabled_command(ctx, error)
        elif isinstance(error, commands.ArgumentParsingError):
            await handle_argument_parsing_error(ctx, error)
        elif isinstance(error, commands.CheckFailure):
            await handle_check_failure(ctx, error)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
            return
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            await handle_command_on_cooldown(ctx, error)

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message)

        if ctx.command is None:
            return
        
        bucket = self.spam_control.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after and message.author.id != self.owner_id:
            cd_message = f"Please wait **{retry_after:.2f} seconds** before using any command again."
            lrm = "\u200E"  # Left-To-Right Mark character
            cooldown = Emojis().get_emoji("cooldown")
            embed = discord.Embed(
                color=discord.Color(0x50c7ef),
                description=f'{lrm}{cooldown} {message.author.mention}: {cd_message}'
            )
            await ctx.send(embed=embed)
            return
        
        await self.invoke(ctx)
    
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        await self.process_commands(message)

    def run(self):
        super().run(
            os.getenv('DISCORD_TOKEN'),
            reconnect=True
        )

    async def get_context(self, origin: discord.Message, *, cls=None) -> Context:
        return await super().get_context(
            origin, 
            cls=cls or Context
        )
    
    @property
    def misc_cog(self) -> Optional[MiscCog]:
        return self.get_cog(MISC_COG)  # type: ignore
    
    @property
    def voicemaster_cog(self) -> Optional[Voicemaster]:
        return self.get_cog(VOICEMASTER)  # type: ignore
    
    @property
    def antinuke_cog(self) -> Optional[Antinuke]:
        return self.get_cog("Antinuke")  # type: ignore
    
    async def bot_prefix(self, guild: discord.Guild) -> str:
        cmd_prefix = await self.get_guild_prefix(guild)
        return cmd_prefix
    
    async def get_guild_prefix(self, guild: discord.Guild):
        """Gets the guild's prefix from the database"""
        try:
            if not guild:
                return DEFAULT_PREFIX
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        "SELECT * FROM guild_prefixes WHERE guild_id = %s;",
                        (guild.id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        prefix = result['guild_prefix']
                        prefix_exists = result['is_set_prefix']
                    if not prefix_exists:
                        prefix = guild.me.mention
                    return prefix
        except Exception as e:
            log.error(f"An error occurred in get_guild_prefix: {e}")
            return DEFAULT_PREFIX

async def _get_prefix(bot: Sparky, message: discord.Message):
    try:
        if not message.guild:
            return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, message)
        async with bot.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM guild_prefixes WHERE guild_id = %s;",
                    (message.guild.id,)
                )
                result = await cur.fetchone()
                if result:
                    # check if a prefix is set for the guild
                    prefix_exists = result['is_set_prefix']
                    if prefix_exists:
                        prefix = result['guild_prefix']
                    else:
                        prefix = None
                else:
                    prefix = DEFAULT_PREFIX
                    await cur.execute(
                        "INSERT INTO guild_prefixes (guild_id, guild_prefix, is_set_prefix) VALUES (%s, %s, %s);",
                        (message.guild.id, DEFAULT_PREFIX, True,)
                    )
        return commands.when_mentioned_or(prefix)(bot, message)
    except Exception as e:
        log.error(f"An error occurred in _get_prefix: {e}")
