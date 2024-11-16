from .managers.context import Context
from .utils.embeds import *
from .utils.emojis import Emojis
from .utils.text import *
from .paginator import *
from .utils.doxx import *
from .errors import *
from typing import Optional
from aiomysql import Pool, create_pool
from dotenv import load_dotenv
from logging import getLogger
import os

load_dotenv()

logger = getLogger(__name__)

__all__ = (
	'Context',
	'make_embed_mute',
	'make_embed_warning',
	'make_embed_cooldown',
	'make_embed_error',
	'make_embed_add',
	'make_embed_info',
	'make_embed_progress',
	'make_embed_remove',
	'make_embed_success',
	'make_embed_sleep',
	'make_embed_wakeup',
	'make_embed_snipe',
	'make_embed_snipe_reaction',
	'make_embed_snipe_not_found',
	'make_embed_loading',
	'make_embed_index_not_found',
	'make_embed_warn',
	'make_embed_lockdown',
	'make_embed_visible',
	'Emojis',
	'format_timedelta',
	'extract_extension',
	'Paginator',
	'get_doxx',
	'handle_extension_error',
	'handle_bad_argument',
	'handle_bad_union_argument',
	'handle_bad_literal_argument',
	'handle_check_failure',
	'get_pool'
)

async def get_pool() -> Optional[Pool]:
    """Create a database pool"""
    try:
        pool = await create_pool(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_DATABASE'),
            autocommit=True
        )
        return pool
    except Exception as e:
        logger.exception(f"An error has occurred in get_pool: {e}")
        return None