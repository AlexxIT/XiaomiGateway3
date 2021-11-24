GATEWAY = "gateway"
ZIGBEE = "zigbee"
BLE = "ble"
MESH = "mesh"

MESH_GROUP_MODEL = 1054

UNKNOWN = "unknown"
SINGLE = "single"
DOUBLE = "double"
TRIPLE = "triple"
QUADRUPLE = "quadruple"
HOLD = "hold"
RELEASE = "release"

# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L4738
BUTTON = {
    1: SINGLE,
    2: DOUBLE,
    3: TRIPLE,
    4: QUADRUPLE,
    5: "quintuple",  # only Yeelight Dimmer
    16: HOLD,
    17: RELEASE,
    18: "shake",
    128: "many",
}
BUTTON_BOTH = {
    4: SINGLE,
    5: DOUBLE,
    6: TRIPLE,
    16: HOLD,
    17: RELEASE,
}
VIBRATION = {1: "vibration", 2: "tilt", 3: "drop"}
LOCK_STATE = {
    1: "door_open", 2: "door_close", 3: "lock_close", 4: "tongue_close",
}
LOCK_CONTROL = {
    0: "in_unlocked", 1: "out_unlocked", 2: "in_locked", 3: "out_locked",
}
MOTOR = {0: "close", 1: "open", 2: "stop"}
RUN_STATE = {0: "closing", 1: "opening", 2: "stop"}
GATE_ALARM = {
    0: "disarmed", 1: "armed_home", 2: "armed_away", 3: "armed_night"
}
POWEROFF_MEMORY = {0: "off", 1: "previous"}
# Hass: On means low, Off means normal
BATTERY_LOW = {1: False, 2: True}
SWITCH_MODE = {1: "250 ms", 2: "500 ms", 3: "750 ms", 4: "1 sec"}
INVERSE = {0: True, 1: False}

GATE_COMMANDS = {
    "idle": "Idle",
    "pair": "Zigbee Pair",
    "remove": "Zigbee Remove",
    # "bind": "Zigbee Bind",
    "ota": "Zigbee OTA",
    "config": "Zigbee Config",
    "miio": "MiIO Command",
    "other": "Other Commands",
}
GW3_COMMANDS = {**GATE_COMMANDS, "lock": "Firmware Lock"}
