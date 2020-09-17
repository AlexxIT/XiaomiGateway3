from datetime import datetime
from typing import Optional

BLE_FINGERPRINT_ACTION = [
    "Match successful", "Match failed", "Timeout", "Low quality",
    "Insufficient area", "Skin is too dry", "Skin is too wet"
]
BLE_DOOR_ACTION = [
    "Door is open", "Door is closed", "Timeout is not closed",
    "Knock on the door", "Breaking the door", "Door is stuck"
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
    0b1111: None
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
    0b1111: None
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
}


def get_ble_domain(param: str) -> Optional[str]:
    if param in (
            'sleep', 'lock', 'opening', 'water_leak', 'smoke', 'gas', 'light',
            'contact'):
        return 'binary_sensor'

    elif param in (
            'action', 'rssi', 'temperature', 'humidity', 'illuminance',
            'moisture', 'conductivity', 'battery', 'formaldehyde',
            'mosquitto'):
        return 'sensor'

    return None


def parse_xiaomi_ble(event: dict) -> Optional[dict]:
    """Parse Xiaomi BLE Data
    https://iot.mi.com/new/doc/embedded-development/ble/object-definition
    """
    eid = event['eid']
    data = bytes.fromhex(event['edata'])
    length = len(data)

    # TODO: check
    if eid == 0x1001 and length == 3:  # magic cube
        return {'action': 'right' if data[0] == 0 else 'left'}

    elif eid == 0x1002 and length == 1:
        # No sleep (0x00), falling asleep (0x01)
        return {'sleep': data[0]}  # 1 => true

    elif eid == 0x1003 and length == 1:
        # Signal strength value
        return {'rssi': data[0]}

    elif eid == 0x1004 and length == 2:
        return {'temperature': int.from_bytes(data, 'little') / 10.0}

    elif eid == 0x1006 and length == 2:
        # Humidity percentage, ranging from 0-1000
        return {'humidity': int.from_bytes(data, 'little') / 10.0}

    elif eid == 0x1007 and length == 3:
        # Range: 0-120000
        return {'illuminance': int.from_bytes(data, 'little')}

    elif eid == 0x1008 and length == 1:
        # Humidity percentage, range: 0-100
        return {'moisture': data[0]}

    elif eid == 0x1009 and length == 2:
        # Soil EC value, Unit us/cm, range: 0-5000
        return {'conductivity': int.from_bytes(data, 'little')}

    elif eid == 0x100A:
        # TODO: lock timestamp
        return {'battery': data[0]}

    elif eid == 0x100D and length == 4:
        return {
            'temperature': int.from_bytes(data[:2], 'little') / 10.0,
            'humidity': int.from_bytes(data[2:], 'little') / 10.0
        }

    elif eid == 0x100E and length == 1:
        # 1 => true => on => unlocked
        # 0x00: unlock state (all bolts retracted)
        # TODO: other values
        return {'lock': 1 if data[0] == 0 else 0}

    elif eid == 0x1010 and length == 2:
        return {'formaldehyde': int.from_bytes(data, 'little') / 100.0}

    elif eid == 0x1012 and length == 1:
        return {'opening': data[0]}  # 1 => true => open

    elif eid == 0x1013 and length == 1:
        # Remaining percentage, range 0~100
        return {'mosquitto': data[0]}

    elif eid == 0x1014 and length == 1:
        return {'water_leak': data[0]}  # 1 => on => wet

    elif eid == 0x1015 and length == 1:
        # TODO: equipment failure (0x02)
        return {'smoke': data[0]}  # 1 => on => alarm

    elif eid == 0x1016 and length == 1:
        return {'gas': data[0]}  # 1 => on => alarm

    elif eid == 0x1017 and length == 4:
        # The duration of the unmanned state, in seconds
        return {'idle_time': int.from_bytes(data, 'little')}

    elif eid == 0x1018 and length == 1:
        return {'light': data[0]}  # 1 => on => strong light

    elif eid == 0x1019 and length == 1:
        # 0x00: open the door, 0x01: close the door,
        # 0x02: not closed after timeout, 0x03: device reset
        # 1 => true => open
        if data[0] == 0:
            return {'contact': 1}
        elif data[0] == 1:
            return {'contact': 0}
        else:
            return {}

    elif eid == 0x0006 and len(data) == 5:
        action = int.from_bytes(data[4:], 'little')
        # status, action, state
        return {
            'action': 'fingerprint',
            'action_id': action,
            'key_id': hex(int.from_bytes(data[:4], 'little')),
            'message': BLE_FINGERPRINT_ACTION[action]
        }

    elif eid == 0x0007:
        # TODO: lock timestamp
        return {
            'action': 'door',
            'action_id': data[0],
            'message': BLE_DOOR_ACTION[data[0]]
        }

    elif eid == 0x0008:
        # TODO: lock timestamp
        return {
            'action': 'armed',
            'state': bool(data[0])
        }

    elif eid == 0x000B:
        action = data[0] & 0x0F
        method = data[0] >> 4
        key_id = int.from_bytes(data[1:5], 'little')
        error = BLE_LOCK_ERROR.get(key_id)

        # all keys except Bluetooth have only 65536 values
        if error is None and method > 0:
            key_id &= 0xFFFF
        elif error:
            key_id = hex(key_id)

        timestamp = int.from_bytes(data[5:], 'little')
        timestamp = datetime.fromtimestamp(timestamp).isoformat()

        return {
            'action': 'lock',
            'action_id': action,
            'method_id': method,
            'message': BLE_LOCK_ACTION[action],
            'method': BLE_LOCK_METHOD[method],
            'key_id': key_id,
            'error': error,
            'timestamp': timestamp
        }

    return None
