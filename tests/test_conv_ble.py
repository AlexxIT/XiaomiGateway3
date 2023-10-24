from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.device import XDevice, BLE
from custom_components.xiaomi_gateway3.core.gateway.base import GatewayBase

assert DOMAIN  # fix circular import

DID = "blt.3.abc"
MAC = "112233aabbcc"
DID2 = "123456789"  # locks have nubm did


def test_night_light():
    device = XDevice(BLE, 2038, DID, MAC)
    assert device.info.name == "Xiaomi Night Light 2"
    device.setup_converters()

    p = device.decode("mibeacon", {"eid": 15, "edata": "640000"})
    assert p == {"light": True, "motion": True}
    p = device.decode("mibeacon", {"eid": 4103, "edata": "640000"})
    assert p == {"light": True}
    p = device.decode("mibeacon", {"eid": 4106, "edata": "64"})
    assert p == {"battery": 100}
    p = device.decode("mibeacon", {"eid": 4119, "edata": "78000000"})
    assert p == {"idle_time": 120}


def test_kettle():
    device = XDevice(BLE, 131, DID, MAC)
    assert device.info.name == "Xiaomi Kettle"
    device.setup_converters()

    p = device.decode("mibeacon", {"eid": 4101, "edata": "0063"})
    assert p == {"power": False, "state": "idle", "temperature": 99}
    p = device.decode("mibeacon", {"eid": 4101, "edata": "0154"})
    assert p == {"power": True, "state": "heat", "temperature": 84}


def test_new_th():
    device = XDevice(BLE, 4611, DID, MAC)
    assert device.info.name == "Xiaomi TH Sensor"
    device.setup_converters()

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/490
    p = device.decode("mibeacon", {"eid": 19464, "edata": "cdcc3e42"})
    assert p == {"humidity": 47.7}

    p = device.decode("mibeacon", {"eid": 19457, "edata": "cdcca841"})
    assert p == {"temperature": 21.1}

    # new miIO format for Gateway fw 1.5.4+
    # https://github.com/AlexxIT/XiaomiGateway3/issues/929
    p = device.decode_miot(
        [{"did": "blt.3.123", "siid": 3, "piid": 1008, "value": 39.099998, "tid": 153}]
    )
    assert p == {"humidity": 39.1}

    p = device.decode_miot(
        [{"did": "blt.3.123", "siid": 3, "piid": 1001, "value": 24.600000, "tid": 154}]
    )
    assert p == {"temperature": 24.6}


def test_lock():
    device = XDevice(BLE, 1694, DID2, MAC)
    assert device.info.name == "Aqara Door Lock N100 (Bluetooth)"
    device.setup_converters()

    p = device.decode("mibeacon", {"eid": 4106, "edata": "329aaecd62"})
    assert p == {"battery": 50}

    p = device.decode("mibeacon", {"eid": 11, "edata": "a400000000b8aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 7, "edata": "00c5aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 7, "edata": "01cbaecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 11, "edata": "2002000180c4aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 6, "edata": "ffffffff00"})
    assert p


def test_9095():
    device = XDevice(BLE, 9095, DID, MAC)
    assert device.info.name == "Xiaomi Wireless Button"
    device.setup_converters()

    # old format
    p = device.decode("mibeacon", {"eid": 19980, "edata": ""})
    assert p == {"action": "single"}

    p = device.decode("mibeacon", {"eid": 19981, "edata": ""})
    assert p == {"action": "double"}

    p = device.decode("mibeacon", {"eid": 19982, "edata": ""})
    assert p == {"action": "hold"}

    # new format
    p = device.decode_miot([{"did": DID, "siid": 3, "eiid": 1012, "arguments": []}])
    assert p == {"action": "single", "button": 1}

    p = device.decode_miot([{"did": DID, "siid": 3, "eiid": 1013, "arguments": []}])
    assert p == {"action": "double", "button": 2}

    p = device.decode_miot([{"did": DID, "siid": 3, "eiid": 1014, "arguments": []}])
    assert p == {"action": "hold", "button": 16}


def test_10987():
    device = XDevice(BLE, 10987, DID, MAC)
    assert device.info.name == "Linptech Motion Sensor 2"
    device.setup_converters()

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/809
    p = device.decode(
        "mibeacon",
        {"did": DID, "eid": 18952, "edata": "00008041", "pdid": 10987, "seq": 72},
    )
    assert p == {"motion": True, "illuminance": 16.0}

    # new format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/956
    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 2,
                "eiid": 1008,
                "tid": 240,
                "arguments": [{"piid": 1005, "value": 23.000000}],
            }
        ]
    )
    assert p == {"motion": True, "illuminance": 23.0}


def test_7184():
    device = XDevice(BLE, 7184, DID, MAC)
    assert device.info.name == "Linptech Wireless Button"
    device.setup_converters()

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/pull/844
    p = device.decode(
        "mibeacon",
        {"did": DID, "eid": 19980, "edata": "01", "pdid": 7184},
    )
    assert p == {"action": "single"}

    # new format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/867
    # https://github.com/AlexxIT/XiaomiGateway3/issues/826
    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 3,
                "eiid": 1012,
                "tid": 117,
                "arguments": [{"piid": 1, "value": 1}],
            }
        ]
    )
    assert p == {"action": "single"}

    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 3,
                "eiid": 1012,
                "tid": 117,
                "arguments": [{"piid": 1, "value": 15}],
            }
        ]
    )
    assert p == {"action": "double"}


def test_6473():
    device = XDevice(BLE, 6473, DID, MAC)
    assert device.info.name == "Xiaomi Double Button"
    device.setup_converters()

    # new format https://github.com/AlexxIT/XiaomiGateway3/issues/965
    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 1}]}]
    )
    assert p == {"action": "button_1_single"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 2}]}]
    )
    assert p == {"action": "button_2_single"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1013, "arguments": [{"piid": 1, "value": 1}]}]
    )
    assert p == {"action": "button_1_double"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1013, "arguments": [{"piid": 1, "value": 2}]}]
    )
    assert p == {"action": "button_2_double"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1014, "arguments": [{"piid": 1, "value": 1}]}]
    )
    assert p == {"action": "button_1_hold"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1014, "arguments": [{"piid": 1, "value": 2}]}]
    )
    assert p == {"action": "button_2_hold"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 3}]}]
    )
    assert p == {"action": "button_both_single"}


def test_9385():
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1169
    device = XDevice(BLE, 9385, DID, MAC)
    assert device.info.name == "Mijia Smart Timer"
    device.setup_converters()

    p = device.decode_miot(
        [{"did": DID, "siid": 2, "eiid": 1025, "arguments": []}]
    )
    assert p == {"action": "timer1"}

    p = device.decode_miot(
        [{"did": DID, "siid": 3, "eiid": 1025, "arguments": []}]
    )
    assert p == {"action": "timer2"}


def test_10249():
    device = XDevice(BLE, 10249, DID, MAC)
    assert device.info.name == "Xiaomi Door Lock E10"
    device.setup_converters()

    p = device.decode_miot([{"did": DID, "siid": 4, "piid": 1021, "value": 2}])
    assert p == {"door": "unlocked"}

    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 3,
                "eiid": 1020,
                "arguments": [
                    {"piid": 1, "value": 65535},  # Operation ID
                    {"piid": 2, "value": 15},  # Operation Method
                    {"piid": 3, "value": 2},  # Lock Action
                    {"piid": 4, "value": 1},  # Operation Position
                    {"piid": 6, "value": 1676548432},  # Current Time
                ],
            }
        ]
    )
    assert p == {
        "action": "unlock",
        "key_id": 65535,
        "method_id": 15,
        "method": "manual",
        "action_id": 2,
        "position": "indoor",
        "timestamp": 1676548432,
    }

    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 3,
                "eiid": 1020,
                "arguments": [
                    {"piid": 1, "value": 102},
                    {"piid": 2, "value": 2},
                    {"piid": 3, "value": 2},
                    {"piid": 4, "value": 2},
                    {"piid": 6, "value": 1676548449},
                ],
            }
        ]
    )
    assert p == {
        "action": "unlock",
        "key_id": 102,
        "method_id": 2,
        "method": "fingerprint",
        "action_id": 2,
        "position": "outdoor",
        "timestamp": 1676548449,
    }

    p = device.decode_miot(
        [
            {
                "did": DID,
                "siid": 6,
                "eiid": 1006,
                "arguments": [{"piid": 1, "value": 1681029598}],
            }
        ]
    )
    assert p == {"action": "doorbell", "timestamp": 1681029598}


def test_lazy_setup():
    device = XDevice(BLE, 9538, DID, MAC)
    assert device.info.name == "Xiaomi TH Clock Pro"
    device.setup_converters()

    gw = GatewayBase()
    gw.options = {}
    gw.setups = {}
    gw.add_device(device.did, device)

    # https://github.com/AlexxIT/XiaomiGateway3/issues/1095
    payload = device.decode("mibeacon", {"eid": 18435, "edata": "64"})
    device.update(payload)
