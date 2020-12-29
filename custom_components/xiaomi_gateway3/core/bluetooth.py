from datetime import datetime
from typing import Optional, Union

DEVICES = {
    # BLE
    152: ["Xiaomi", "Flower Care", "HHCCJCY01"],
    426: ["Xiaomi", "TH Sensor", "LYWSDCGQ/01ZM"],
    839: ["Xiaomi", "Qingping TH Sensor", "CGG1"],
    1034: ["Xiaomi", "Mosquito Repellent", "WX08ZM"],
    1115: ["Xiaomi", "TH Clock", "LYWSD02MMC"],
    1249: ["Xiaomi", "Magic Cube", "XMMF01JQD"],
    1371: ["Xiaomi", "TH Sensor 2", "LYWSD03MMC"],
    1398: ["Xiaomi", "Alarm Clock", "CGD1"],
    1694: ["Aqara", "Door Lock N100", "ZNMS16LM"],
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM"],
    1747: ["Xiaomi", "ZenMeasure Clock", "MHO-C303"],
    1983: ["Yeelight", "Button S1", "YLAI003"],
    2038: ["Xiaomi", "Night Light 2", "MJYD02YL-A"],
    2443: ["Xiaomi", "Door Sensor 2", "MCCGQ02HL"],
    2444: ["Xiaomi", "Door Lock", "XMZNMST02YD"],
    2480: ["Xiaomi", "Safe Box", "BGX-5/X1-3001"],
    2701: ["Xiaomi", "Motion Sensor 2", "RTCGQ02LM"],
    # Mesh
    948: ["Yeelight", "Mesh Downlight", "YLSD01YL"],
    995: ["Yeelight", "Mesh Bulb E14", "YLDP09YL"],
    996: ["Yeelight", "Mesh Bulb E27", "YLDP10YL"],
    997: ["Yeelight", "Mesh Spotlight", "YLSD04YL"],
    1771: ["Xiaomi", "Mesh Bulb", "MJDP09YL"],
    1772: ["Xiaomi", "Mesh Downlight", "MJTS01YL"],
    2076: ["Yeelight", "Mesh Downlight M2", "YLTS02YL/YLTS04YL"],
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL"],
    # Mesh Switches
    1946: ["Xiaomi", "Mesh Wall Double Switch", "DHKG02ZM"],
    2007: ["Unknown", "Mesh Switch Controller", "2007"],
    2093: ["PTX", "Mesh Wall Triple Switch", "PTX-TK3/M"],
    2257: ["PTX", "Mesh Wall Double Switch", "PTX-SK2M"],
    2258: ["PTX", "Mesh Wall Single Switch", "PTX-SK1M"],
    # Mesh Group
    0: ["Xiaomi", "Mesh Group", "Mesh Group"]
}

# model: [
#   [siid, piid, name, on_value, off_value],
#   [siid, piid, name, on_value, off_value],
#   ...
# ]
BLE_SWITCH_DEVICES_PROPS = {
    1946: [
        [2, 1, 'Left Switch', True, False],
        [3, 1, 'Right Switch', True, False],
    ],
    2007: [
        [2, 1, None, True, False]
    ],
    2093: [
        [2, 1, 'Left Switch', True, False],
        [3, 1, 'Middle Switch', True, False],
        [4, 1, 'Right Switch', True, False],
        [8, 1, 'Backlight', 1, 0],
        [8, 2, 'Left - Always On', 1, 0],
        [8, 3, 'Middle - Always On', 1, 0],
        [8, 4, 'Right - Always On', 1, 0]
    ],
    2257: [
        [2, 1, 'Left Switch', True, False],
        [3, 1, 'Right Switch', True, False],
        [8, 1, 'Backlight', 1, 0],
        [8, 2, 'Left - Always On', 1, 0],
        [8, 3, 'Right - Always On', 1, 0],
    ],
    2258: [
        [2, 1, 'Switch', True, False],
        [8, 1, 'Backlight', 1, 0],
        [8, 2, 'Always On', 1, 0],
    ]
}

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

ACTIONS = {
    1249: ['right', 'left'],
    1983: ['single', 'double', 'hold']
}


def get_ble_domain(param: str) -> Optional[str]:
    if param in (
            'sleep', 'lock', 'opening', 'water_leak', 'smoke', 'gas', 'light',
            'contact'):
        return 'binary_sensor'

    elif param in (
            'action', 'rssi', 'temperature', 'humidity', 'illuminance',
            'moisture', 'conductivity', 'battery', 'formaldehyde',
            'mosquitto', 'idle_time'):
        return 'sensor'

    return None


def parse_xiaomi_ble(event: dict, pdid: int) -> Optional[dict]:
    """Parse Xiaomi BLE Data
    https://iot.mi.com/new/doc/embedded-development/ble/object-definition
    """
    eid = event['eid']
    data = bytes.fromhex(event['edata'])
    length = len(data)

    if eid == 0x1001 and length == 3:  # 4097
        if pdid in ACTIONS and data[0] < len(ACTIONS[pdid]):
            return {'action': ACTIONS[pdid][data[0]]}
        else:
            return {'action': data[0]}

    elif eid == 0x1002 and length == 1:  # 4098
        # No sleep (0x00), falling asleep (0x01)
        return {'sleep': data[0]}  # 1 => true

    elif eid == 0x1003 and length == 1:  # 4099
        # Signal strength value
        return {'rssi': data[0]}

    elif eid == 0x1004 and length == 2:  # 4100
        return {'temperature': int.from_bytes(data, 'little', signed=True) / 10.0}

    elif eid == 0x1006 and length == 2:  # 4102
        # Humidity percentage, ranging from 0-1000
        return {'humidity': int.from_bytes(data, 'little') / 10.0}

    elif eid == 0x1007 and length == 3:  # 4103
        # Range: 0-120000, lux
        return {'illuminance': int.from_bytes(data, 'little')}

    elif eid == 0x1008 and length == 1:  # 4104
        # Humidity percentage, range: 0-100
        return {'moisture': data[0]}

    elif eid == 0x1009 and length == 2:  # 4105
        # Soil EC value, Unit us/cm, range: 0-5000
        return {'conductivity': int.from_bytes(data, 'little')}

    elif eid == 0x100A:  # 4106
        # TODO: lock timestamp
        return {'battery': data[0]}

    elif eid == 0x100D and length == 4:  # 4109
        return {
            'temperature': int.from_bytes(data[:2], 'little', signed=True) / 10.0,
            'humidity': int.from_bytes(data[2:], 'little') / 10.0
        }

    elif eid == 0x100E and length == 1:  # 4110
        # 1 => true => on => unlocked
        # 0x00: unlock state (all bolts retracted)
        # TODO: other values
        return {'lock': 1 if data[0] == 0 else 0}

    elif eid == 0x100F and length == 1:  # 4111
        # 1 => true => on => dooor opening
        return {'opening': 1 if data[0] == 0 else 0}

    elif eid == 0x1010 and length == 2:  # 4112
        return {'formaldehyde': int.from_bytes(data, 'little') / 100.0}

    elif eid == 0x1012 and length == 1:  # 4114
        return {'opening': data[0]}  # 1 => true => open

    elif eid == 0x1013 and length == 1:  # 4115
        # Remaining percentage, range 0~100
        return {'mosquitto': data[0]}

    elif eid == 0x1014 and length == 1:  # 4116
        return {'water_leak': data[0]}  # 1 => on => wet

    elif eid == 0x1015 and length == 1:  # 4117
        # TODO: equipment failure (0x02)
        return {'smoke': data[0]}  # 1 => on => alarm

    elif eid == 0x1016 and length == 1:  # 4118
        return {'gas': data[0]}  # 1 => on => alarm

    elif eid == 0x1017 and length == 4:  # 4119
        # The duration of the unmanned state, in seconds
        return {'idle_time': int.from_bytes(data, 'little')}

    elif eid == 0x1018 and length == 1:  # 4120
        return {'light': data[0]}  # 1 => on => strong light

    elif eid == 0x1019 and length == 1:  # 4121
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

    elif eid == 0x000B:  # 11
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

    elif eid == 0x0F:  # 15
        # 1 - moving no light, 100 - moving with light
        # TODO: fix me in future
        return {'action': int.from_bytes(data, 'little')}

    return None


MESH_PROPS = [None, 'light', 'brightness', 'color_temp']


def parse_xiaomi_mesh(data: list):
    """Can receive multiple properties from multiple devices."""
    result = {}

    for payload in data:
        if payload.get('code', 0) != 0:
            continue

        did = payload['did']
        if payload['model'] in BLE_SWITCH_DEVICES_PROPS.keys():
            # handle response for BLE mesh switches
            # a tuple of (siid, piid) is used as the key
            key = (payload['siid'], payload['piid'])
            result.setdefault(did, {})[key] = payload['value']
        else:
            if payload['siid'] != 2:
                continue

            key = MESH_PROPS[payload['piid']]
            result.setdefault(did, {})[key] = payload['value']

    return result


def pack_xiaomi_mesh(did: str, data: Union[dict, list]):
    if isinstance(data, dict):
        if data.get('is_switch', False):
            # for mesh switches, key of the dict is a tuple of (siid, piid)
            return [{
                'did': did,
                'siid': k[0],
                'piid': k[1],
                'value': v
            } for k, v in data.items() if k != 'is_switch']

        return [{
            'did': did,
            'siid': 2,
            'piid': MESH_PROPS.index(k),
            'value': v
        } for k, v in data.items()]
    else:
        return [{
            'did': did,
            'siid': 2,
            'piid': MESH_PROPS.index(k),
        } for k in data]


def get_device(pdid: int, default_name: str) -> Optional[dict]:
    if pdid in DEVICES:
        desc = DEVICES[pdid]
        return {
            'device_manufacturer': desc[0],
            'device_name': desc[0] + ' ' + desc[1],
            'device_model': desc[2] if len(desc) > 2 else pdid
        }
    else:
        return {
            'device_name': default_name,
            'device_model': pdid
        }
