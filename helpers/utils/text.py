import datetime
import re
from typing import List, Optional, Tuple
import discord
import pytz

__all__ = (
    'singular_plural',
    'return_delta_and_time_dict',
    'format_timedelta',
    'check_links',
    'extract_extension'
)

def singular_plural(time_unit: str, value: int) -> str:
    """Return the singular or plural form of a time unit based on the value"""
    if value == 1:
        return time_unit[:-1]  # Remove 's' for singular
    else:
        return time_unit
    
def _parse_time(time_param: str) -> Tuple[int, int, int, int, int]:
    current_digit = ''
    weeks = days = hours = minutes = seconds = 0
    time_param = time_param.lower().strip()

    for char in time_param:
        if char.isdigit():
            current_digit += char
        elif char.isalpha():
            if char == 'w' and current_digit:
                weeks += int(current_digit)
            elif char == 'd' and current_digit:
                days += int(current_digit)
            elif char == 'h' and current_digit:
                hours += int(current_digit)
            elif char == 'm' and current_digit:
                minutes += int(current_digit)
            elif char == 's' and current_digit:
                seconds += int(current_digit)
            current_digit = ''
        else:
            raise ValueError(f"Invalid character in input string: {char}")
        
    return weeks, days, hours, minutes, seconds
    
def _calculate_time(time_param: int) -> Tuple[bool, int, int, int, int, int]:
    """Turns a time string into a boolean value, weeks, days, hours, minutes and seconds"""
    
    weeks, days, hours, minutes, seconds = _parse_time(time_param)

    seconds_check = (days + weeks * 7) * 86400 + hours * 3600 + minutes * 60 + seconds
    minutes += seconds // 60
    seconds %= 60
    hours += minutes // 60
    minutes %= 60
    days += hours // 24
    hours %= 24
    weeks += days // 7
    days %= 7

    return seconds_check > 2419200, weeks, days, hours, minutes, seconds

def return_delta_and_time_dict(
    duration: int
) -> Optional[Tuple[
    datetime.datetime, 
    List[str], 
    List[int],
    int,
    bool
]]:
    # Turn the 'duration' parameter into a proper time format
    """Return a datetime object and a list of time units"""
    if duration < 0:
        return None
    try:
        limit, weeks, days, hours, minutes, seconds = _calculate_time(duration)
    except ValueError:
        return None
    final_dict = {}
    time_dict = {
        'weeks': 0 if limit else weeks,
        'days': 0 if limit else days,
        'hours': 0 if limit else hours,
        'minutes': 0 if limit else minutes,
        'seconds': 0 if limit else seconds
    }
    for time_format, time_value in time_dict.items():
        if time_value > 0 and len(final_dict) < 3:
            final_dict.update({time_format: time_value})
    if len(final_dict) == 0:
        final_dict.update({'minutes': 5})

    final_dict_keys = list(final_dict.keys())
    final_dict_values = list(final_dict.values())
    weeks = days = hours = minutes = seconds = 0

    weeks = final_dict.get('weeks', 0)
    days = final_dict.get('days', 0)
    hours = final_dict.get('hours', 0)
    minutes = final_dict.get('minutes', 0)
    seconds = final_dict.get('seconds', 0)

    delta = datetime.timedelta(
        weeks=weeks,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    future_time = utc_now + delta
    future_time_aware = future_time.replace(tzinfo=datetime.timezone.utc)
    future_time_aware_local = future_time_aware.astimezone(pytz.timezone('America/New_York'))
    return future_time_aware_local, final_dict_keys, final_dict_values, len(final_dict), limit

def format_timedelta(td: datetime.timedelta) -> str:
    """Format a timedelta into a string"""
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f'{days} {singular_plural("days", days)}'
    elif hours:
        return f'{hours} {singular_plural("hours", hours)}'
    elif minutes:
        return f'{minutes} {singular_plural("minutes", minutes)}'
    else:
        return f'{seconds} {singular_plural("seconds", seconds)}'

def check_links(message: discord.Message) -> bool:
    """Checks messages for links"""
    regex = r"(https?:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
    matches = re.finditer(regex, message.content)
    for _ in matches:
        return True
    return False

def extract_extension(url: str) -> Optional[str]:
    pattern = r"https:\/\/cdn\.discordapp\.com\/attachments\/\d+\/\d+\/[^.]+\.(\w+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None