# buttons actions
UNKNOWN = "unknown"
BUTTON_SINGLE = "single"
BUTTON_DOUBLE = "double"
BUTTON_TRIPLE = "triple"
BUTTON_QUADRUPLE = "quadruple"
BUTTON_HOLD = "hold"
BUTTON_RELEASE = "release"

BUTTON_1_SINGLE = "button_1_single"
BUTTON_2_SINGLE = "button_2_single"
BUTTON_3_SINGLE = "button_3_single"
BUTTON_4_SINGLE = "button_4_single"

BUTTON_1_DOUBLE = "button_1_double"
BUTTON_2_DOUBLE = "button_2_double"
BUTTON_3_DOUBLE = "button_3_double"
BUTTON_4_DOUBLE = "button_4_double"

BUTTON_1_HOLD = "button_1_hold"
BUTTON_2_HOLD = "button_2_hold"
BUTTON_3_HOLD = "button_3_hold"
BUTTON_4_HOLD = "button_4_hold"

BUTTON_BOTH_12 = "button_both_12"
BUTTON_BOTH_13 = "button_both_13"
BUTTON_BOTH_23 = "button_both_23"

BUTTON_BOTH_SINGLE = "button_both_single"
BUTTON_BOTH_DOUBLE = "button_both_double"
BUTTON_BOTH_HOLD = "button_both_hold"

# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L4738
BUTTON = {
    1: BUTTON_SINGLE,
    2: BUTTON_DOUBLE,
    3: BUTTON_TRIPLE,
    4: BUTTON_QUADRUPLE,
    5: "quintuple",  # only Yeelight Dimmer
    16: BUTTON_HOLD,
    17: BUTTON_RELEASE,
    18: "shake",
    128: "many",
}
BUTTON_BOTH = {
    4: BUTTON_SINGLE,
    5: BUTTON_DOUBLE,
    6: BUTTON_TRIPLE,
    16: BUTTON_HOLD,
    17: BUTTON_RELEASE,
}

ENTITY_CONFIG = {"category": "config", "enabled": False}
ENTITY_DIAGNOSTIC = {"category": "diagnostic"}
ENTITY_DISABLED = {"enabled": False}
ENTITY_LAZY = {"lazy": True}

UNIT_CELSIUS = "°C"
UNIT_SECONDS = "s"
UNIT_MINUTES = "min"

UNIT_METERS = "m"

# door: On means open, Off means closed
# lock: On means open (unlocked), Off means closed (locked)
STATE_UNLOCK = True
STATE_LOCKED = False

LOCK_NOTIFY = {
    3235774464: "Frequent door opening failures due to incorrect passwords",  # 0xC0DE0000
    3235774465: "Frequent door opening failures due to incorrect fingerprints",  # 0xC0DE0001
    3235774469: "Frequent door opening with abnormal keys",  # 0xC0DE0005
    3235774470: "Foreign objects in the keyhole",  # 0xC0DE0006
    3235774471: "Keys not removed",  # 0xC0DE0007
    3235774472: "Frequent door opening failures with incorrect NFC",  # 0xC0DE0008
    3235774473: "Door unlocked after timeout",  # 0xC0DE0009
    3235774474: "Multiple verification failures (advanced protection)",  # 0xC0DE000A
    3235778564: "Automatic lock body abnormal"  # 0xC0DE1004
}

GESTURE_MAP = {
    2: "Two",
    4: "Four",
    5: "Five",
    6: "Eight",
    10: "OK",
    101: "Both Two",
    102: "Both Four",
    103: "Both Four",
    104: "Both Eight",
    105: "Both OK"
}

PETS_MAP = {
    0: "",
    1: "Cat",
    2: "Dog",
    3: "Cat or Dog"
}

ALARM_INDEX_MAP = {
    0: "Police car 1",
    1: "Police car 2",
    2: "Safety accident",
    3: "Missile countdown",
    4: "Ghost scream",
    5: "Sniper rifle",
    6: "Battle",
    7: "Air raid alarm",
    8: "Dog bark",
    10000: "default"
}