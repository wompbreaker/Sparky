from helpers import Emojis

INTERFACE_EMOJIS = Emojis().get_emojis(
    'lock', 'unlock', 'ghost', 'unghost', 'microphone',
    'hammer', 'computer', 'info_1', 'plus', 'minus'
)

LOCK = Emojis().strip_emoji(INTERFACE_EMOJIS[0])
UNLOCK = Emojis().strip_emoji(INTERFACE_EMOJIS[1])
GHOST = Emojis().strip_emoji(INTERFACE_EMOJIS[2])
REVEAL = Emojis().strip_emoji(INTERFACE_EMOJIS[3])
CLAIM = Emojis().strip_emoji(INTERFACE_EMOJIS[4])
DISCONNECT = Emojis().strip_emoji(INTERFACE_EMOJIS[5])
START = Emojis().strip_emoji(INTERFACE_EMOJIS[6])
VIEW = Emojis().strip_emoji(INTERFACE_EMOJIS[7])
INCREASE = Emojis().strip_emoji(INTERFACE_EMOJIS[8])
DECREASE = Emojis().strip_emoji(INTERFACE_EMOJIS[9])

ACTIVITY_EMOJIS = Emojis().get_emojis(
    'youtube', 'gartic_phone', 'poker_night', 'putt_party', 'chess',
    'checkers', 'blazing_8s', 'bobble_league', 'sketch_heads', 'color_together',
    'land_io', 'know_what_i_meme', 'letter_league', 'spellcast', 'chef_showdown',
    'whiteboard'
)

CHECKED = Emojis().get_emoji('approve')
DENY = Emojis().get_emoji('deny')
VOICE = Emojis().get_emoji('voice')
ACTIVITIES = {
    "watch_together": {
        "activity_id": 880218394199220334,
        "activity_name": "Watch Together",
        "activity_emoji": ACTIVITY_EMOJIS[0]
    },
    "gartic_phone": {
        "activity_id": 1007373802981822582,
        "activity_name": "Gartic Phone",
        "activity_emoji": ACTIVITY_EMOJIS[1]
    },
    "poker_night": {
        "activity_id": 755827207812677713,
        "activity_name": "Poker Night",
        "activity_emoji": ACTIVITY_EMOJIS[2]
    },
    "putt_party": {
        "activity_id": 945737671223947305,
        "activity_name": "Putt Party",
        "activity_emoji": ACTIVITY_EMOJIS[3]
    },
    "chess_in_the_park": {
        "activity_id": 832012774040141894,
        "activity_name": "Chess in the Park",
        "activity_emoji": ACTIVITY_EMOJIS[4]
    },
    "checkers_in_the_park": {
        "activity_id": 832013003968348200,
        "activity_name": "Checkers in the Park",
        "activity_emoji": ACTIVITY_EMOJIS[5]
    },
    "blazing_8s": {
        "activity_id": 832025144389533716,
        "activity_name": "Blazing 8s",
        "activity_emoji": ACTIVITY_EMOJIS[6]
    },
    "bobble_league": {
        "activity_id": 947957217959759964,
        "activity_name": "Bobble League",
        "activity_emoji": ACTIVITY_EMOJIS[7]
    },
    "sketch_heads": {
        "activity_id": 902271654783242291,
        "activity_name": "Sketch Heads",
        "activity_emoji": ACTIVITY_EMOJIS[8]
    },
    "color_together": {
        "activity_id": 1039835161136746497,
        "activity_name": "Color Together",
        "activity_emoji": ACTIVITY_EMOJIS[9]
    },
    "land_io": {
        "activity_id": 903769130790969345,
        "activity_name": "Land-io",
        "activity_emoji": ACTIVITY_EMOJIS[10]
    },
    "know_what_i_meme": {
        "activity_id": 950505761862189096,
        "activity_name": "Know What I Meme",
        "activity_emoji": ACTIVITY_EMOJIS[11]
    },
    "letter_league": {
        "activity_id": 879863686565621790,
        "activity_name": "Letter League",
        "activity_emoji": ACTIVITY_EMOJIS[12]
    },
    "spellcast": {
        "activity_id": 852509694341283871,
        "activity_name": "SpellCast",
        "activity_emoji": ACTIVITY_EMOJIS[13]
    },
    "chef_showdown": {
        "activity_id": 1037680572660727838,
        "activity_name": "Chef Showdown",
        "activity_emoji": ACTIVITY_EMOJIS[14]
    },
    "whiteboard": {
        "activity_id": 1070087967294631976,
        "activity_name": "Whiteboard",
        "activity_emoji": ACTIVITY_EMOJIS[15]
    }
}