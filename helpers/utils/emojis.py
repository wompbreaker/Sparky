import json
from typing import Optional, List, Dict
import os

class Emojis:
    __slots__ = ('emojis')

    def __init__(self) -> None:
        self.emojis: Dict[str, str] = self._load_emojis()
        if not self.emojis:
            raise ValueError("Failed to load emojis")
        
    @staticmethod
    def _load_emojis() -> Dict[str, str]:
        """Load emojis from a JSON file"""
        try:
            filepath = os.path.join(os.path.dirname(__file__), "emojis.json")
            with open(filepath, "r") as file:
                emojis = json.load(file)
                return emojis
        except Exception as e:
            print(f"An error occurred in _load_emojis: {e.__class__.__name__} {e}")
            raise ValueError("There was an error loading emojis with _load_emojis")
        
    def get_emoji(self, name: str) -> Optional[str]:
        """Get an emoji by name"""
        emoji = self.emojis.get(name, None)
        if emoji is None:
            raise ValueError(f"Emoji not found: {name}")
        if not emoji.startswith("<"):
            emoji = f"\\N{{{emoji}}}".encode().decode('unicode-escape')
        return emoji
    
    def get_emoji_by_id(self, id: int) -> Optional[str]:
        """Get an emoji by ID"""
        for name, emoji_id in self.emojis.items():
            if emoji_id == id:
                return name
        return None
    
    def get_emojis(self, *names: str) -> Optional[List[str]]:
        """Get a list of emojis by name"""
        emoji_list = [self.get_emoji(name) for name in names]
        if None in emoji_list:
            missing = [name for name, emoji in zip(names, emoji_list) if emoji is None]
            raise ValueError(f"Emojis not found: {', '.join(missing)}")
        return emoji_list
    
    def strip_emoji(self, emoji: str) -> str:
        """Removes <> from an emoji"""
        return emoji.replace("<", "").replace(">", "")
    
    def get_stripped_emoji(self, name: str) -> str:
        """Get a stripped emoji by name"""
        emoji = self.get_emoji(name)
        if emoji is None:
            raise ValueError(f"Emoji not found: {name}")
        return self.strip_emoji(emoji)
    