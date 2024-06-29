import struct
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .base import BaseConv

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

ACTIONS = {
    1249: {0: "right", 1: "left"},
    1983: {0: "single", 0x010000: "double", 0x020000: "hold"},
    2147: {0: "single"},
}


class BLEByteConv(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        payload[self.attr] = int(data[:2], 16)  # uint8


@dataclass
class BLEMathConv(BaseConv):
    multiply: float = 1.0
    round: int = None
    signed: bool = False

    def decode(self, device: "XDevice", payload: dict, data: str):
        value = int.from_bytes(bytes.fromhex(data), "little", signed=self.signed)
        if self.multiply != 1.0:
            value *= self.multiply
        if self.round is not None:
            # convert to int when round is zero
            value = round(value, self.round or None)
        payload[self.attr] = value


@dataclass
class BLEFloatConv(BaseConv):
    round: int = None

    def decode(self, device: "XDevice", payload: dict, data: str):
        value = struct.unpack("<f", bytes.fromhex(data))[0]
        if self.round is not None:
            # convert to int when round is zero
            value = round(value, self.round or None)
        payload[self.attr] = value


@dataclass
class BLEMapConv(BaseConv):
    map: dict[str, bool | int | str] = None

    def decode(self, device: "XDevice", payload: dict, data: str):
        if data in self.map:
            payload[self.attr] = self.map[data]


class BLEFinger(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        data = bytes.fromhex(data)
        action = int.from_bytes(data[4:], "little")
        if action >= len(BLE_FINGERPRINT_ACTION):
            return
        # status, action, state
        payload.update(
            {
                "action": self.attr,
                "action_id": action,
                "key_id": hex(int.from_bytes(data[:4], "little")),
                "message": BLE_FINGERPRINT_ACTION[action],
            }
        )


class BLEDoor(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        data = bytes.fromhex(data)
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
                "action": self.attr,
                "action_id": action,
                "message": BLE_DOOR_ACTION[action],
                "timestamp": timestamp,
            }
        )


class BLELock(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        data = bytes.fromhex(data)
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
                "action": self.attr,
                "action_id": action,
                "method_id": method,
                "message": BLE_LOCK_ACTION[action],
                "method": BLE_LOCK_METHOD[method],
                "key_id": key_id,
                "error": error,
                "timestamp": timestamp,
            }
        )


class BLETempHumi(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        data = bytes.fromhex(data)
        payload["temperature"] = int.from_bytes(data[:2], "little", signed=True) / 10.0
        payload["humidity"] = int.from_bytes(data[2:], "little") / 10.0


class BLEToothbrush(BaseConv):
    def decode(self, device: "XDevice", payload: dict, data: str):
        data = bytes.fromhex(data)
        if data[0] == 0:
            payload.update({"action": "start", "counter": data[1]})
        else:
            payload.update({"action": "finish", "score": data[1]})


class BLEKettle(BaseConv):
    map = {0: "idle", 1: "heat", 2: "cool_down", 3: "warm_up"}

    def decode(self, device: "XDevice", payload: dict, data: str):
        # Kettle, thanks https://github.com/custom-components/ble_monitor/
        # hass: On means power detected, Off means no power
        data = bytes.fromhex(data)
        payload.update(
            {
                "power": bool(data[0]),
                "state": self.map[data[0]],
                "temperature": data[1],
            }
        )


class BLEBattery2691(BaseConv):
    # noinspection PyTypedDict
    def decode(self, device: "XDevice", payload: dict, data: str):
        # this sensor sends some kind of counter once an hour instead of the battery,
        # so filter out the false values
        value = int(data, 16)  # uint8
        if value == device.extra.get("battery"):
            payload[self.attr] = value
        device.extra["battery"] = value
