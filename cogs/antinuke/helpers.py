import logging
from typing import Optional, Literal

logger = logging.getLogger(__name__)

def get_punishment(value: int) -> Optional[Literal['stripstaff', 'kick', 'ban']]:
	"""Get the punishment name from the value"""
	value = int(value)
	try:
		punishments = {
			0: "stripstaff",
			1: "kick",
			2: "ban"
		}
		return punishments[value]
	except Exception as e:
		logger.error(f"{type(e)} error in get_punishment: {e}")