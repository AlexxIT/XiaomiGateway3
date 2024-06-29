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
