GATEWAY = "gateway"
ZIGBEE = "zigbee"
BLE = "ble"
MESH = "mesh"

MESH_GROUP_MODEL = 1054

TIME = {"s": 1, "m": 60, "h": 3600, "d": 86400}

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
DOOR_STATE = {0: "open", 1: "close", 2: "ajar"}
LOCK_STATE = {
    0: "door_cannot_locked",
    1: "door_opened",
    2: "door_without_lift",
    3: "door_locked",
    4: "reverse_locked",
}
LOCK_CONTROL = {
    0: "in_unlocked",
    1: "out_unlocked",
    2: "in_locked",
    3: "out_locked",
}
LOCK_ALARM = {
    0: "off",
    1: "key_open",
    4: "unlocked",
    8: "hijack",
    16: "pry",
    32: "normally_open",
    256: "less_storage",
    500: "low_bat",
    512: "doorbell",
}
MOTOR = {0: "close", 1: "open", 2: "stop"}
RUN_STATE = {0: "closing", 1: "opening", 2: "stop"}
GATE_ALARM = {0: "disarmed", 1: "armed_home", 2: "armed_away", 3: "armed_night"}
BULB_MEMORY = {0: "on", 1: "previous"}
POWEROFF_MEMORY = {0: "off", 1: "previous"}
# Hass: On means low, Off means normal
BATTERY_LOW = {1: False, 2: True}
SWITCH_MODE = {1: "250 ms", 2: "500 ms", 3: "750 ms", 4: "1 sec"}
INVERSE = {0: True, 1: False}
INVERSE_BOOL = {False: True, True: False}
