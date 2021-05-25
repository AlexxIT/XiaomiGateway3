from datetime import datetime
from typing import Optional

from Crypto.Cipher import AES

# Bluetooth Model: [Manufacturer, Device Name, Device Model]
# params: [siid, piid, hass attr name, hass domain]
DEVICES = [{
    # BLE
    131: ["Xiaomi", "Kettle", "YM-K1501"],
    152: ["Xiaomi", "Flower Care", "HHCCJCY01"],
    339: ["Yeelight", "Remote Control", "YLYK01YL"],
    426: ["Xiaomi", "TH Sensor", "LYWSDCGQ/01ZM"],
    794: ["Xiaomi", "Door Lock", "MJZNMS02LM"],
    839: ["Xiaomi", "Qingping TH Sensor", "CGG1"],
    903: ["Xiaomi", "ZenMeasure TH", "MHO-C401"],
    950: ["Yeelight", "Dimmer", "YLKG07YL"],
    982: ["Xiaomi", "Qingping Door Sensor", "CGH1"],
    1034: ["Xiaomi", "Mosquito Repellent", "WX08ZM"],
    1115: ["Xiaomi", "TH Clock", "LYWSD02MMC"],
    1249: ["Xiaomi", "Magic Cube", "XMMF01JQD"],
    1371: ["Xiaomi", "TH Sensor 2", "LYWSD03MMC"],
    1398: ["Xiaomi", "Alarm Clock", "CGD1"],
    1694: ["Aqara", "Door Lock N100", "ZNMS16LM"],
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM"],
    1747: ["Xiaomi", "ZenMeasure Clock", "MHO-C303"],
    1983: ["Yeelight", "Button S1", "YLAI003"],
    2038: ["Xiaomi", "Night Light 2", "MJYD02YL-A"],  # 15,4103,4106,4119,4120
    2147: ["Xiaomi", "Water Leak Sensor", "SJWS01LM"],
    2443: ["Xiaomi", "Door Sensor 2", "MCCGQ02HL"],
    2444: ["Xiaomi", "Door Lock", "XMZNMST02YD"],
    2480: ["Xiaomi", "Safe Box", "BGX-5/X1-3001"],
    2691: ["Xiaomi", "Qingping Motion Sensor", "CGPR1"],
    # logs: https://github.com/AlexxIT/XiaomiGateway3/issues/180
    2701: ["Xiaomi", "Motion Sensor 2", "RTCGQ02LM"],  # 15,4119,4120
    2888: ["Xiaomi", "Qingping TH Sensor", "CGG1"],  # same model as 839?!
}, {
    # Mesh Light
    0: ["Xiaomi", "Mesh Group", "Mesh Group"],
    948: ["Yeelight", "Mesh Downlight", "YLSD01YL"],
    995: ["Yeelight", "Mesh Bulb E14", "YLDP09YL"],
    996: ["Yeelight", "Mesh Bulb E27", "YLDP10YL"],
    997: ["Yeelight", "Mesh Spotlight", "YLSD04YL"],
    1771: ["Xiaomi", "Mesh Bulb", "MJDP09YL"],
    1772: ["Xiaomi", "Mesh Downlight", "MJTS01YL"],
    2076: ["Yeelight", "Mesh Downlight M2", "YLTS02YL/YLTS04YL"],
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL"],
    2584: ["XinGuang", "XinGuang Smart Light", "LIBMDA09X"],
    'miot_spec': [
        [2, 1, 'light', 'light'],
        [2, 2, 'brightness', None],
        [2, 3, 'color_temp', None],
    ]
}, {
    # Mesh Switches
    1946: ["Xiaomi", "Mesh Wall Double Switch", "DHKG02ZM"],
    'miot_spec': [
        [2, 1, 'left_switch', 'switch'],
        [3, 1, 'right_switch', 'switch'],
    ]
}, {
    1945: ["Xiaomi", "Mesh Wall Switch", "DHKG01ZM"],
    2007: ["Unknown", "Mesh Switch Controller"],
    'miot_spec': [
        [2, 1, 'switch', 'switch']
    ],
}, {
    2093: ["PTX", "Mesh Wall Triple Switch", "PTX-TK3/M"],
    3878: ["PTX", "Mesh Wall Triple Switch", "PTX-SK3M"],
    'miot_spec': [
        [2, 1, 'left_switch', 'switch'],
        [3, 1, 'middle_switch', 'switch'],
        [4, 1, 'right_switch', 'switch'],
        [8, 1, 'backlight', 'switch'],
        [8, 2, 'left_smart', 'switch'],
        [8, 3, 'middle_smart', 'switch'],
        [8, 4, 'right_smart', 'switch']
    ]
}, {
    2257: ["PTX", "Mesh Wall Double Switch", "PTX-SK2M"],
    'miot_spec': [
        [2, 1, 'left_switch', 'switch'],
        [3, 1, 'right_switch', 'switch'],
        [8, 1, 'backlight', 'switch'],
        [8, 2, 'left_smart', 'switch'],
        [8, 3, 'right_smart', 'switch'],
    ]
}, {
    2258: ["PTX", "Mesh Wall Single Switch", "PTX-SK1M"],
    'miot_spec': [
        [2, 1, 'switch', 'switch'],
        [8, 1, 'backlight', 'switch'],
        [8, 2, 'smart', 'switch'],
    ]
}, {
    2717: ["Xiaomi", "Mesh Wall Triple Switch", "ISA-KG03HL"],
    'miot_spec': [
        [2, 1, 'left_switch', 'switch'],
        [3, 1, 'middle_switch', 'switch'],
        [4, 1, 'right_switch', 'switch'],
        [6, 1, 'humidity', 'sensor'],
        [6, 7, 'temperature', 'sensor'],
    ]
}, {
    3083: ["Xiaomi", "Mi Smart Electrical Outlet", "ZNCZ01ZM"],
    'miot_spec': [
        [2, 1, 'outlet', 'switch'],
        [3, 1, 'power', 'sensor'],
        [4, 1, 'backlight', 'switch'],
    ]
}]

# if color temp not default 2700..6500
COLOR_TEMP = {
    2584: [3000, 6400],
}
# if max brightness not default 65535
MAX_BRIGHTNESS = {
    2584: 100
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
    339: {
        0: 'on', 1: 'off', 2: 'temp', 4: 'mode', 3: 'up', 5: 'down',
        0x20000: 'on_hold', 0x20001: 'off_hold', 0x20002: 'temp_hold',
        0x20004: 'mode_hold', 0x20003: 'up_hold', 0x20005: 'down_hold',
    },
    1249: {0: 'right', 1: 'left'},
    1983: {0: 'single', 0x010000: 'double', 0x020000: 'hold'},
    2147: {0: 'single'},
}

# https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/
BLE_MANUF = {
    b'\x4C\x00': "Apple",
    b'\x8f\x03': "Xiaomi"
}

# mac in lower case witout colon = key in hexstring
BLE_KEYS = {}
BLE_SEQ = {}


def get_ble_domain(param: str) -> Optional[str]:
    if param in (
            'sleep', 'lock', 'opening', 'water_leak', 'smoke', 'gas', 'light',
            'contact', 'motion', 'power'):
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
        if pdid == 950:
            if data[2] == 3:
                if data[0] == 0:
                    # click from 1 to 5
                    return {'button': data[1]}
                elif data[0] == 1:
                    # hold with duration
                    return {'action': 'hold', 'duration': data[1]}
            elif data[2] == 4:
                if data[0] == 0:
                    # rotate with sign (right or left)
                    value = int.from_bytes(data[1:2], 'little', signed=True)
                    return {'action': 'rotate', 'angle': value}
                elif data[1] == 0:
                    # hold and rotate with sign (right or left)
                    value = int.from_bytes(data[0:1], 'little', signed=True)
                    return {'action': 'rotate_hold', 'angle': value}
            return None

        value = int.from_bytes(data, 'little')
        return {
            'action': ACTIONS[pdid][value]
            if pdid in ACTIONS and value in ACTIONS[pdid]
            else value
        }

    elif eid == 0x1002 and length == 1:  # 4098
        # No sleep (0x00), falling asleep (0x01)
        return {'sleep': data[0]}  # 1 => true

    elif eid == 0x1003 and length == 1:  # 4099
        # Signal strength value
        return {'rssi': data[0]}

    elif eid == 0x1004 and length == 2:  # 4100
        return {
            'temperature': int.from_bytes(data, 'little', signed=True) / 10.0
        }

    elif eid == 0x1005 and length == 2:  # 4101
        # Kettle, thanks https://github.com/custom-components/ble_monitor/
        return {'power': data[0], 'temperature': data[1]}

    elif eid == 0x1006 and length == 2:  # 4102
        # Humidity percentage, ranging from 0-1000
        value = int.from_bytes(data, 'little') / 10.0
        if pdid in (903, 1371):
            # two models has bug, they increase humidity on each data by 0.1
            value = int(value)
        return {'humidity': value}

    elif eid == 0x1007 and length == 3:  # 4103
        value = int.from_bytes(data, 'little')

        if pdid == 2038:
            # Night Light 2: 1 - no light, 100 - light
            return {'light': int(value >= 100)}

        # Range: 0-120000, lux
        return {'illuminance': value}

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
            'temperature': int.from_bytes(data[:2], 'little',
                                          signed=True) / 10.0,
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
        # Door Sensor 2: 0 - dark, 1 - light
        return {'light': 1 if data[0] else 0}

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
        # Night Light 2: 1 - moving no light, 100 - moving with light
        # Motion Sensor 2: 0 - moving no light, 256 - moving with light
        # Qingping Motion Sensor - moving with illuminance data
        value = int.from_bytes(data, 'little')
        return (
            {'motion': 1, 'illuminance': value}
            if pdid == 2691 else
            {'motion': 1, 'light': int(value >= 100)}
        )

    return None


def mibeacon_decode4(mibeacon: bytes, payload_pos: int, key: str):
    payload = mibeacon[payload_pos:-7]
    if not payload:
        return None

    try:
        # mac + pid + cnt + counter
        key = bytes.fromhex(key)
        nonce = mibeacon[5:11] + mibeacon[2:5] + mibeacon[-7:-4]
        cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=4)
        cipher.update(b'\x11')

        token = mibeacon[-4:]
        return cipher.decrypt_and_verify(payload, token)
    except:
        return None


def mibeacon_decode2(mibeacon: bytes, payload_pos: int, key: str):
    payload = mibeacon[payload_pos:-4]
    if not payload:
        return None

    key = bytes.fromhex(key[0:12] + '8d3d3c97' + key[12:24])

    # frame + pid + cnt + counter + mac5
    nonce = mibeacon[0:5] + mibeacon[-4:-1] + mibeacon[5:10]
    cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=4)
    cipher.update(b'\x11')

    return cipher.decrypt(payload)


def parse_raw_xiaomi(data: bytes):
    frame = int.from_bytes(data[:2], 'little')
    # check mac
    if frame & 0x10 == 0:
        return None
    # check payload
    if frame & 0x40 == 0:
        return None

    mac = bytearray(reversed(data[5:11])).hex()
    seq = data[4]

    # check same seq
    if BLE_SEQ.get(mac) == seq:
        return None

    BLE_SEQ[mac] = seq

    version = (frame >> 12) & 0b1111

    i = 5 + 6
    # check capability
    if frame & 0x20:
        cap = data[i]
        i += 1
        if (cap >> 3) == 0b11:
            i += 2
        if version == 5 and cap & 0x20:
            i += 2

    payload = data[i:-2] if version == 5 and frame & 0x80 else data[i:]
    if payload == b'':
        return None

    # check encription
    if frame & 0x08:
        if mac not in BLE_KEYS:
            return None

        if 4 <= version <= 5:
            payload = mibeacon_decode4(data, i, BLE_KEYS[mac])
        elif 2 <= version <= 3:
            payload = mibeacon_decode2(data, i, BLE_KEYS[mac])
        else:
            return None

    # eid - 2 bytes, size - 1 byte, value 1+ bytes
    if not payload or len(payload) < 4:
        return None

    pdid = int.from_bytes(data[2:4], 'little')
    eid = int.from_bytes(payload[:2], 'little')
    edata = payload[3:]

    if payload[2] != len(edata):
        # wrong payload len
        return None

    return {
        'dev': {'mac': mac, 'pdid': pdid},
        'evt': {'eid': eid, 'edata': edata.hex()},
        'frmCnt': seq
    }


def parse_raw_ble(data: str) -> Optional[dict]:
    """Return payload only for valid Advertising."""
    # https://www.silabs.com/community/wireless/bluetooth/knowledge-base.entry.html/2017/02/10/bluetooth_advertisin-hGsf
    # https://www.argenox.com/library/bluetooth-low-energy/ble-advertising-primer/
    data = bytes.fromhex(data)

    result = None

    # validate payload
    i = 0
    while i < len(data):
        len_ = data[i]
        if i + len_ >= len(data):
            return None

        ad_type = data[i + 1]
        # https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile/
        if 0x2D < ad_type < 0xFF or ad_type == 0:
            return None

        # Service Data + 16-bit UUID
        if ad_type == 0x16 and data[i + 2:i + 4] == b'\x95\xfe':
            result = parse_raw_xiaomi(data[i + 4:i + 1 + len_])

        i += 1 + len_

    if i != len(data):
        return None

    return result


def get_ble_model(data: str) -> Optional[str]:
    """Return Xiaomi Product ID if available. Or known manufacturer. If payload
    invalid - return Null.
    """
    data = bytes.fromhex(data)

    if len(data) < 3:
        return None

    pdid = manuf = None

    # validate payload
    i = 0
    while i < len(data):
        len_ = data[i]
        if i + len_ >= len(data):
            return None

        ad_type = data[i + 1]
        if 0x2D < ad_type < 0xFF or ad_type == 0:
            return None

        # Service Data + 16-bit UUID
        if ad_type == 0x16:
            if data[i + 2:i + 4] == b'\x95\xfe':
                pdid = str(int.from_bytes(data[i + 6:i + 8], 'little'))
        elif ad_type == 0x2A:
            pdid = "Mesh"
        elif ad_type == 0xFF:
            # Manufacturer Specific Data
            manuf = BLE_MANUF.get(data[i + 2:i + 4])
            if data[i + 2:i + 4] == b'\x8f\x03':
                if data[i + 5] == 0x10:  # proximity
                    pdid = str(int.from_bytes(data[i + 6:i + 8], 'little'))
                elif data[i + 5] == 0x11:  # phone
                    name_len = data[i + 9] >> 4
                    pdid = data[i + 10:i + 10 + name_len].decode()

        i += 1 + len_

    if i != len(data):
        return None

    return pdid or manuf or "Unknown"


def add_beaconkey(mac: str, beaconkey: str, from_db: bool = False):
    if mac in BLE_KEYS:
        return

    if from_db:
        key = bytes.fromhex('00000000000000000000000000000000')
        cipher = AES.new(key, AES.MODE_CCM, nonce=key[:8], mac_len=4)
        payload = bytes.fromhex(beaconkey)
        BLE_KEYS[mac] = cipher.decrypt(payload).hex()
    else:
        BLE_KEYS[mac] = beaconkey


def get_device(pdid: int, default_name: str) -> Optional[dict]:
    for device in DEVICES:
        if pdid in device:
            desc = device[pdid]
            return {
                'device_manufacturer': desc[0],
                'device_name': desc[0] + ' ' + desc[1],
                'device_model': desc[2] if len(desc) > 2 else pdid,
                'lumi_spec': None,
                'miot_spec': device.get('miot_spec'),
                # if color temp not default 2700..6500
                'color_temp': COLOR_TEMP.get(pdid),
                'max_brightness': MAX_BRIGHTNESS.get(pdid)
            }

    return {
        'device_name': default_name,
        'device_model': pdid,
        'lumi_spec': None,
        # default Mesh device will be Bulb
        'miot_spec': [
            [2, 1, 'light', 'light'],
            [2, 2, 'brightness', None],
            [2, 3, 'color_temp', None],
        ]
    } if default_name == 'Mesh' else {
        'device_name': default_name,
        'device_model': pdid,
    }
