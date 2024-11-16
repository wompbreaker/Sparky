# This file includes parts of code from https://github.com/Rapptz/RoboDanny/blob/rewrite/launcher.py
# Original code by Rapptz
# Modifications by wompbreaker
# This file is licensed under the Mozilla Public License 2.0 (MPL 2.0)
# See the LICENSE file for more details

from __future__ import annotations
import asyncio
import os
import discord
import logging
import contextlib

from bot import Sparky

from logging.handlers import RotatingFileHandler

try:
	import uvloop  # type: ignore
except ImportError:
	pass
else:
	asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

bot = Sparky()
print(f"Discord.py version: {discord.__version__}")

class RemoveNoise(logging.Filter):
	def __init__(self):
		super().__init__(name='discord.state')

	def filter(self, record: logging.LogRecord) -> bool:
		if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
			return False
		return True
	
class RemoveRateLimit(logging.Filter):
	def __init__(self):
		super().__init__(name='discord.http')

	def filter(self, record: logging.LogRecord) -> bool:
		if record.levelname == 'WARNING' and 'being rate limited' in record.msg:
			return False
		return True
	
@contextlib.contextmanager
def setup_logging():
	log = logging.getLogger()

	try:
		discord.utils.setup_logging()
		# __enter__
		max_bytes = 32 * 1024 * 1024  # 32 MiB
		logging.getLogger('discord').setLevel(logging.INFO)
		logging.getLogger('discord.http').setLevel(logging.WARNING)
		logging.getLogger('discord.http').addFilter(RemoveRateLimit())
		logging.getLogger('discord.state').addFilter(RemoveNoise())

		log.setLevel(logging.INFO)
		handler = RotatingFileHandler(
			filename='sparky.log',
			encoding='utf-8',
			mode='w',
			maxBytes=max_bytes,
			backupCount=5
		)
		dt_fmt = '%Y-%m-%d %H:%M:%S'
		fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
		handler.setFormatter(fmt)
		log.addHandler(handler)

		yield  # All the code after the yield will be executed as __exit
	finally:
		# __exit__
		handlers = log.handlers[:]
		for handler in handlers:
			handler.close()
			log.removeHandler(handler)

async def main():
	# Start the bot
	try:
		token = os.getenv('TOKEN') or ""
		log = logging.getLogger()
		if token == "":
			raise Exception("Add your token to the .env file")
		await bot.start(token)
	except discord.HTTPException as e:
		if e.status == 429:
			log.exception("The Discord servers denied the connection for making too many requests")
		else:
			raise e
	else:
		if bot is not None and bot.pool is not None:
			await bot.pool.close()
		if bot is not None and bot.pool is not None:
			await bot.pool.wait_closed()
		await bot.close()


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	try:
		with setup_logging():
			loop.run_until_complete(main())
	finally:
		loop.close()
