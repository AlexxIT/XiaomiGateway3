import struct
from datetime import datetime
from typing import TYPE_CHECKING

from .base import Converter

if TYPE_CHECKING:
    from ..device import XDevice

BLE_FINGERPRINT_ACTION = [
    "Match successful",
    "Match failed",
    "Timeout",
    "Low quality",
    "Insufficient area",
    "Skin is too dry",
    "Skin is too wet",
]
BLE_DOOR_ACTION = [
    "Door is open",
    "Door is closed",
    "Timeout is not closed",
    "Knock on the door",
    "Breaking the door",
    "Door is stuck",
]
BLE_LOCK_ACTION = {
    0b0000: "Unlock outside the door",
    0b0001: "Lock",
    0b0010: "Turn on anti-lock",
    0b0011: "Turn off anti-lock",
    0b0100: "Unlock inside the door",
    0b0101: "Lock inside the door",
    0b0110: "Turn on child lock",
    0b0111: "Turn off child lock",
    0b1000: "Lock outside the door",
    0b1111: "Abnormal",
}
BLE_LOCK_METHOD = {
    0b0000: "bluetooth",
    0b0001: "password",
    0b0010: "biological",
    0b0011: "key",
    0b0100: "turntable",
    0b0101: "nfc",
    0b0110: "one-time password",
    0b0111: "two-step verification",
    0b1000: "coercion",
    0b1010: "manual",
    0b1011: "automatic",
    0b1111: "abnormal",
}
BLE_LOCK_ERROR = {
    0xC0DE0000: "Frequent unlocking with incorrect password",
    0xC0DE0001: "Frequent unlocking with wrong fingerprints",
    0xC0DE0002: "Operation timeout (password input timeout)",
    0xC0DE0003: "Lock picking",
    0xC0DE0004: "Reset button is pressed",
    0xC0DE0005: "The wrong key is frequently unlocked",
    0xC0DE0006: "Foreign body in the keyhole",
    0xC0DE0007: "The key has not been taken out",
    0xC0DE0008: "Error NFC frequently unlocks",
    0xC0DE0009: "Timeout is not locked as required",
    0xC0DE000A: "Failure to unlock frequently in multiple ways",
    0xC0DE000B: "Unlocking the face frequently fails",
    0xC0DE000C: "Failure to unlock the vein frequently",
    0xC0DE000D: "Hijacking alarm",
    0xC0DE000E: "Unlock inside the door after arming",
    0xC0DE000F: "Palmprints frequently fail to unlock",
    0xC0DE0010: "The safe was moved",
    0xC0DE1000: "The battery level is less than 10%",
    0xC0DE1001: "The battery is less than 5%",
    0xC0DE1002: "The fingerprint sensor is abnormal",
    0xC0DE1003: "The accessory battery is low",
    0xC0DE1004: "Mechanical failure",
    0xC0DE1005: "the lock sensor is faulty",
}

BLE_SPEC_LOCK_ACTION = {
    0b0000: None,
    0b0001: "Lock",
    0b0010: "Unlock",
    0b0011: "Lifted Up The Door Handle From Outside To Lock",
    0b0100: "Locked From Inside",
    0b0101: "Released Lock From Inside",
    0b0110: "Enabled Child Lock",
    0b0111: "Disabled Child Lock",
    0b1000: "Enable The Away From Home Mode",
    0b1001: "Disable The Away From Home Mode",
}

BLE_SPEC_LOCK_METHOD = {
    0b0000: None,
    0b0001: "Mobile Phone",
    0b0010: "Finger Print",
    0b0011: "PassWord",
    0b0100: "NFC",
    0b0101: "Face",
    0b0110: "Finger Vein",
    0b0111: "Palm Print",
    0b1000: "Lock Key",
    0b1001: "One Time Password",
    0b1010: "Periodic Password",
    0b1011: "HomeKit",
    0b1100: "Coerce",
    0b1101: "Two Step Verification",
    0b1110: "Turntable",
    0b1111: "Manual",
    0b10000: "Auto",
}
BLE_SPEC_LOCK_ERROR = {
    1: "Frequent Unlocking Failed By Multiple Methods",
    2: "Frequent Unlocking Failed By Password",
    3: "Frequent Unlocking Failed By Fingerprint",
    4: "Frequent Unlocking Failed By NFC",
    5: "Frequent Unlocking Failed By Face",
    6: "Frequent Unlocking Failed By Palmprint",
    7: "Frequent Unlocking Failed By Finger Vein",
    8: "Frequent Unlocking Failed By Key",
    9: "Door Lock Was Damaged",
    10: "Locked Unsuccessfully",
    11: "Unlock From Inside After Leaving Home",
    12: "Door Lock Was Reset",
    13: "Foreign Object Detected In The Keyhole",
    14: "Key Was Not Removed",
    15: "Door Lock Fingerprint Sensor Error",
    16: "Door Lock Mechanical Failure",
    17: "Door Lock Main Part Failure",
    18: "The Lithium Battery Temperature Is Too High",
    19: "Door Lock Batteries Are Low",
    20: "Door Lock Batteries Are Nearly Depleted",
    21: "Door Lock Camera Batteries Are Low",
    22: "Door Lock Camera Batteries Are Nearly Depleted",
    23: "Leaving The Door Open Timed Out",
    24: "Door Was Ajar",
    25: "Door Was Opened Forcefully",
}

BLE_SPEC_LOCK_POSITION = {
    1: "Indoor",
    2: "OutDoor",
    3: "Not Tell The Inside Or Outside Of The Door",
}

KETTLE = {0: "idle", 1: "heat", 2: "cool_down", 3: "warm_up"}

ACTIONS = {
    1249: {0: "right", 1: "left"},
    1983: {0: "single", 0x010000: "double", 0x020000: "hold"},
    2147: {0: "single"},
}


# https://iot.mi.com/new/doc/embedded-development/ble/object-definition
class MiBeaconConv(Converter):
    # TODO: think...
    childs = {
        "action": "sensor",
        "battery": "sensor",
        "conductivity": "sensor",
        "formaldehyde": "sensor",
        "humidity": "sensor",
        "idle_time": "sensor",
        "moisture": "sensor",
        "rssi": "sensor",
        "supply": "sensor",
        "temperature": "sensor",
        "contact": "sensor",
        "gas": "binary_sensor",
        "light": "binary_sensor",
        "lock": "binary_sensor",
        "motion": "binary_sensor",
        "opening": "binary_sensor",
        "power": "binary_sensor",
        "sleep": "binary_sensor",
        "smoke": "binary_sensor",
        "water_leak": "binary_sensor",
    }

    def decode(self, device: "XDevice", payload: dict, value: dict):
        """Parse Xiaomi BLE Data."""
        eid = value["eid"]
        data = bytes.fromhex(value["edata"])

        if eid == 0x1001 and len(data) == 3:  # 4097
            # button action
            value = int.from_bytes(data, "little")
            payload["action"] = (
                ACTIONS[device.model][value]
                if device.model in ACTIONS and value in ACTIONS[device.model]
                else value
            )

        elif eid == 0x1002 and len(data) == 1:  # 4098
            # No sleep (0x00), falling asleep (0x01)
            payload["sleep"] = bool(data[0])  # 1 => true

        elif eid == 0x1003 and len(data) == 1:  # 4099
            # Signal strength value
            payload["rssi"] = data[0]

        elif eid == 0x1004 and len(data) == 2:  # 4100
            payload["temperature"] = int.from_bytes(data, "little", signed=True) / 10.0

        elif eid == 0x1005 and len(data) == 2:  # 4101
            # Kettle, thanks https://github.com/custom-components/ble_monitor/
            # hass: On means power detected, Off means no power
            payload.update(
                {
                    "power": bool(data[0]),
                    "state": KETTLE[data[0]],
                    "temperature": data[1],
                }
            )

        elif eid == 0x1006 and len(data) == 2:  # 4102
            # Humidity percentage, ranging from 0-1000
            value = int.from_bytes(data, "little") / 10.0
            if device.model in (903, 1371):
                # two models has bug, they increase humidity on each msg by 0.1
                value = int(value)
            payload["humidity"] = value

        elif eid == 0x1007 and len(data) == 3:  # 4103
            value = int.from_bytes(data, "little")
            if device.model == 2038:
                # Night Light 2: 1 - no light, 100 - light
                # hass: On means light detected, Off means no light
                payload["light"] = bool(value >= 100)
            else:
                # Range: 0-120000, lux
                payload["illuminance"] = value

        elif eid == 0x1008 and len(data) == 1:  # 4104
            # Humidity percentage, range: 0-100
            payload["moisture"] = data[0]

        elif eid == 0x1009 and len(data) == 2:  # 4105
            # Soil EC value, Unit us/cm, range: 0-5000
            payload["conductivity"] = int.from_bytes(data, "little")

        elif eid == 0x100A:  # 4106
            # TODO: lock timestamp
            value = data[0]
            if device.model == 2691:
                # this sensor sends some kind of counter once an hour instead
                # of the battery, so filter out the false values
                prev = device.extra.get("battery")
                device.extra["battery"] = value
                if prev != value:
                    return
            payload["battery"] = value

        elif eid == 0x100D and len(data) == 4:  # 4109
            payload.update(
                {
                    "temperature": int.from_bytes(data[:2], "little", signed=True)
                    / 10.0,
                    "humidity": int.from_bytes(data[2:], "little") / 10.0,
                }
            )

        elif eid == 0x100E and len(data) == 1:  # 4110
            # 0x00: unlock state (all bolts retracted)
            # hass: On means open (unlocked), Off means closed (locked)
            # TODO: other values
            payload["lock"] = bool(data[0] == 0)

        elif eid == 0x100F and len(data) == 1:  # 4111
            # 0x00: open the door, 0x01: Close the door
            # 0x02: Timeout is not closed, 0x03: knock on the door
            # 0x04: Pry the door, 0x05: The door is stuck
            # hass: On means open, Off means closed
            payload["opening"] = bool(data[0] == 0)

        elif eid == 0x1010 and len(data) == 2:  # 4112
            if device.model == 1809:
                payload["formaldehyde"] = int.from_bytes(data, "little") / 1000.0
            else:
                payload["formaldehyde"] = int.from_bytes(data, "little") / 100.0

        elif eid == 0x1012 and len(data) == 1:  # 4114
            # hass: On means open, Off means closed
            payload["opening"] = bool(data[0])  # 1 => true => open

        elif eid == 0x1013 and len(data) == 1:  # 4115
            # Remaining percentage, range 0~100
            payload["supply"] = data[0]

        elif eid == 0x1014 and len(data) == 1:  # 4116
            # hass: On means wet, Off means dry
            payload["water_leak"] = bool(data[0])

        elif eid == 0x1015 and len(data) == 1:  # 4117
            # hass: On means smoke detected, Off means no smoke (clear)
            if data[0] <= 1:
                payload["smoke"] = bool(data[0])  # 1 => on => alarm
            elif data[0] == 2:
                payload["action"] = "equipment failure"

        elif eid == 0x1016 and len(data) == 1:  # 4118
            # hass: On means gas detected, Off means no gas (clear)
            payload["gas"] = bool(data[0])  # 1 => on => alarm

        elif eid == 0x1017 and len(data) == 4:  # 4119
            # The duration of the unmanned state, in seconds
            payload["idle_time"] = int.from_bytes(data, "little")

        elif eid == 0x1018 and len(data) == 1:  # 4120
            # Door Sensor 2: 0 - dark, 1 - light
            # hass: On means light detected, Off means no light
            payload["light"] = bool(data[0])

        elif eid == 0x1019 and len(data) == 1:  # 4121
            # 0x00: open the door, 0x01: close the door,
            # 0x02: not closed after timeout, 0x03: device reset
            # hass: On means open, Off means closed
            if data[0] == 0:
                payload["contact"] = True
            elif data[0] == 1:
                payload["contact"] = False
            elif data[0] == 2:
                payload["action"] = "timeout"
            elif data[0] == 3:
                payload["action"] = "reset"

        elif eid == 0x4803:
            payload["battery"] = data[0]

        elif eid == 0x4C01 and len(data) == 4:
            payload["temperature"] = round(struct.unpack("<f", data)[0], 2)

        elif eid == 0x4C02:
            # xiaomi TH Sensor 3  Humidity
            payload["humidity"] = data[0]

        elif eid == 0x4C08 and len(data) == 4:
            payload["humidity"] = round(struct.unpack("<f", data)[0], 2)

        elif eid == 0x0006 and len(data) == 5:
            action = int.from_bytes(data[4:], "little")
            if action >= len(BLE_FINGERPRINT_ACTION):
                return
            # status, action, state
            payload.update(
                {
                    "action": "fingerprint",
                    "action_id": action,
                    "key_id": hex(int.from_bytes(data[:4], "little")),
                    "message": BLE_FINGERPRINT_ACTION[action],
                }
            )

        elif eid == 0x0007:
            action = data[0]
            if action >= len(BLE_DOOR_ACTION):
                return

            timestamp = int.from_bytes(data[1:5], "little")
            timestamp = datetime.fromtimestamp(timestamp).isoformat()

            if action == 0:
                # 0 open, 1 closed
                payload["contact"] = True
            elif action == 1:
                payload["contact"] = False
            elif action == 3:
                # 3 doorbell
                payload["doorbell"] = timestamp

            payload.update(
                {
                    "action": "door",
                    "action_id": action,
                    "message": BLE_DOOR_ACTION[action],
                    "timestamp": timestamp,
                }
            )

        elif eid == 0x0008:
            # TODO: lock timestamp
            payload.update({"action": "armed", "state": data[0]})

        elif eid == 0x000B:  # 11
            action = data[0] & 0x0F
            method = data[0] >> 4
            key_id = int.from_bytes(data[1:5], "little")
            error = BLE_LOCK_ERROR.get(key_id)

            # all keys except Bluetooth have only 65536 values
            if error is None and method > 0:
                key_id &= 0xFFFF
            elif error:
                key_id = hex(key_id)

            timestamp = int.from_bytes(data[5:], "little")
            timestamp = datetime.fromtimestamp(timestamp).isoformat()

            if action not in BLE_LOCK_ACTION or method not in BLE_LOCK_METHOD:
                return

            payload.update(
                {
                    "action": "lock",
                    "action_id": action,
                    "method_id": method,
                    "message": BLE_LOCK_ACTION[action],
                    "method": BLE_LOCK_METHOD[method],
                    "key_id": key_id,
                    "error": error,
                    "timestamp": timestamp,
                }
            )

        elif eid == 0x000F:  # 15
            # Night Light 2: 1 - moving no light, 100 - moving with light
            # Motion Sensor 2: 0 - moving no light, 256 - moving with light
            # Qingping Motion Sensor - moving with illuminance data
            value = int.from_bytes(data, "little")
            if device.model == 2691:
                payload.update({"motion": True, "illuminance": value})
            else:
                payload.update({"motion": True, "light": bool(value >= 100)})

        elif eid == 0x0010 and len(data) == 2:  # 16
            # Toothbrush Т500
            if data[0] == 0:
                payload.update({"action": "start", "counter": data[1]})
            else:
                payload.update({"action": "finish", "score": data[1]})

        elif eid == 0x4E0C:  # 19980
            value = int.from_bytes(data, "little")
            # wireless button XMWXKG01YL
            if device.model == 6473:
                if value == 1:
                    payload.update({"action": "button_1_single"})
                if value == 2:
                    payload.update({"action": "button_2_single"})
                if value == 3:
                    payload.update({"action": "button_both_single"})
            # wireless switch Linptech K11
            elif device.model == 7184:
                if value == 1:
                    payload.update({"action": "single"})
                if value == 8:
                    payload.update({"action": "hold"})
                if value == 15:
                    payload.update({"action": "double"})
            # wireless button Xiaomi Wireless Switch Bluetooth Version
            elif device.model == 9095:
                payload.update({"action": "single"})

        elif eid == 0x4E0D:  # 19981
            value = int.from_bytes(data, "little")
            # wireless button XMWXKG01YL
            if device.model == 6473:
                if value == 1:
                    payload.update({"action": "button_1_double"})
                if value == 2:
                    payload.update(
                        {"action": "button_2_double"}
                    )  # wireless button Xiaomi Wireless Switch Bluetooth Version
            elif device.model == 9095:
                payload.update({"action": "double"})

        elif eid == 0x4E0E:  # 19982
            value = int.from_bytes(data, "little")
            # wireless button XMWXKG01YL
            if device.model == 6473:
                if value == 1:
                    payload.update({"action": "button_1_hold"})
                if value == 2:
                    payload.update({"action": "button_2_hold"})
            # wireless button Xiaomi Wireless Switch Bluetooth Version
            elif device.model == 9095:
                payload.update({"action": "hold"})

        elif eid == 0x4818:  # 18456
            # Linptech motion sensor version 2
            payload["idle_time"] = int.from_bytes(data, "little")

        elif eid == 0x4A08:  # 18952
            # Linptech motion sensor version 2
            value = struct.unpack("<f", data)[0]
            payload.update({"motion": True, "illuminance": value})

        elif eid == 0x4C03:  # 19459
            # Linptech motion sensor version 2
            payload["battery"] = data[0]

        elif eid == 0x5003:  # 20483
            # xiaomi face recogenize lock battery
            payload["battery"] = data[0]
        elif eid == 0x4A14:  # 18964
            # xiaomi face recogenize lock action
            action_id = data[6]
            method_id = data[7]
            key_id = int.from_bytes(data[0:1], "little")
            position_id = data[8]

            timestamp = int.from_bytes(data[2:6], "little")
            timestamp = datetime.fromtimestamp(timestamp).isoformat()

            # 1 lock,2 unlock
            if action_id == 1:
                payload["contact"] = False
                payload["lock"] = False
                action = "lock"
            elif action_id == 2:
                payload["contact"] = True
                payload["lock"] = True
                action = "unlock"
            else:
                action = None

            if (
                action_id not in BLE_SPEC_LOCK_ACTION
                or method_id not in BLE_SPEC_LOCK_METHOD
                or position_id not in BLE_SPEC_LOCK_POSITION
            ):
                return

            payload.update(
                {
                    "action": action,
                    "action_id": action_id,
                    "method_id": method_id,
                    "posotion_id": position_id,
                    "message": BLE_SPEC_LOCK_ACTION[action_id],
                    "method": BLE_SPEC_LOCK_METHOD[method_id],
                    "position": BLE_SPEC_LOCK_POSITION[position_id],
                    "key_id": key_id,
                    "timestamp": timestamp,
                }
            )
        elif eid == 0x5606:  # 22022
            # xiaomi face recogenize lock doorbell
            timestamp = int.from_bytes(data[0:4], "little")
            timestamp = datetime.fromtimestamp(timestamp).isoformat()

            payload["doorbell"] = timestamp
        elif eid == 0x4A07:
            # xiaomi face recogenize lock abnormal-condition
            error_id = data[5]
            if error_id not in BLE_SPEC_LOCK_ERROR:
                return
            payload["error"] = BLE_SPEC_LOCK_ERROR[error_id]
        elif eid == 0x560C:  # 22028
            # wireless button KS1PBB
            if device.model == 15895:
                value = int.from_bytes(data, "little")
                if value == 1:
                    payload.update({"action": "button_1_single"})
                if value == 2:
                    payload.update({"action": "button_2_single"})
                if value == 3:
                    payload.update({"action": "button_3_single"})
                if value == 4:
                    payload.update({"action": "button_4_single"})
        elif eid == 0x560D:  # 22029
            # wireless button KS1PBB
            if device.model == 15895:
                value = int.from_bytes(data, "little")
                if value == 1:
                    payload.update({"action": "button_1_double"})
                if value == 2:
                    payload.update({"action": "button_2_double"})
                if value == 3:
                    payload.update({"action": "button_3_double"})
                if value == 4:
                    payload.update({"action": "button_4_double"})
        elif eid == 0x560E:  # 22030
            # wireless button KS1PBB
            if device.model == 15895:
                value = int.from_bytes(data, "little")
                if value == 1:
                    payload.update({"action": "button_1_hold"})
                if value == 2:
                    payload.update({"action": "button_2_hold"})
                if value == 3:
                    payload.update({"action": "button_3_hold"})
                if value == 4:
                    payload.update({"action": "button_4_hold"})
        elif eid == 0x4801:  # 18433
            # wireless button KS1PBB
            if device.model == 15895:
                payload["temperature"] = round(struct.unpack("<f", data)[0], 2)
        elif eid == 0x4808:  # 18440
            # wireless button KS1PBB
            if device.model == 15895:
                payload["humidity"] = round(struct.unpack("<f", data)[0], 2)

MiBeacon = MiBeaconConv("mibeacon")

BLEAction = Converter("action", "sensor")
BLEAction.childs = {
    "action_id",
    "counter",
    "error",
    "key_id",
    "message",
    "method",
    "method_id",
    "score",
    "state",
    "timestamp",
}
BLEBattery = Converter("battery", "sensor")
BLEConductivity = Converter("conductivity", "sensor")
BLEFormaldehyde = Converter("formaldehyde", "sensor")
BLEHumidity = Converter("humidity", "sensor")
BLEIdleTime = Converter("idle_time", "sensor")
BLEIlluminance = Converter("illuminance", "sensor")
BLEMoisture = Converter("moisture", "sensor")
BLERSSI = Converter("rssi", "sensor")
BLESupply = Converter("supply", "sensor")
BLETemperature = Converter("temperature", "sensor")
BLEContact = Converter("contact", "binary_sensor")
BLEGas = Converter("gas", "binary_sensor")
BLELight = Converter("light", "binary_sensor")  # night light, door sensor
BLELock = Converter("lock", "binary_sensor")
BLEMotion = Converter("motion", "binary_sensor")
BLEOpening = Converter("opening", "binary_sensor")
BLEPower = Converter("power", "binary_sensor")  # kettle
BLEPower.childs = {"state"}
BLESleep = Converter("sleep", "binary_sensor")
BLESmoke = Converter("smoke", "binary_sensor")
BLEWaterLeak = Converter("water_leak", "binary_sensor")
