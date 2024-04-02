from custom_components.xiaomi_gateway3 import XDevice


def test_flower_care():
    device = XDevice(152)
    assert device.market_name == "Xiaomi Flower Care"
    p = device.decode({"eid": 4100, "edata": "BF00"})
    assert p == {"temperature": 19.1}
    p = device.decode({"eid": 4103, "edata": "000000"})
    assert p == {"illuminance": 0}
    p = device.decode({"eid": 4104, "edata": "1C"})
    assert p == {"moisture": 28}
    p = device.decode({"eid": 4105, "edata": "3101"})
    assert p == {"conductivity": 305}


def test_night_light():
    device = XDevice(2038)
    assert device.market_name == "Xiaomi Night Light 2"
    p = device.decode({"eid": 15, "edata": "640000"})
    assert p == {"light": True, "motion": True}
    p = device.decode({"eid": 4103, "edata": "640000"})
    assert p == {"light": True}
    p = device.decode({"eid": 4106, "edata": "64"})
    assert p == {"battery": 100}
    p = device.decode({"eid": 4119, "edata": "78000000"})
    assert p == {"idle_time": 120}


def test_kettle():
    device = XDevice(131)
    assert device.market_name == "Xiaomi Kettle"
    p = device.decode({"eid": 4101, "edata": "0063"})
    assert p == {"power": False, "state": "idle", "temperature": 99}
    p = device.decode({"eid": 4101, "edata": "0154"})
    assert p == {"power": True, "state": "heat", "temperature": 84}


def test_839():
    device = XDevice(839)
    p = device.decode({"eid": 4109, "edata": "EC003901"})
    assert p == {"humidity": 31.3, "temperature": 23.6}


def test_2443():
    device = XDevice(2443)
    assert device.market_name == "Xiaomi Door/Window Sensor 2"
    p = device.decode({"eid": 4121, "edata": "01"})
    assert p == {"contact": False}
    p = device.decode({"eid": 4120, "edata": "01"})
    assert p == {"light": True}
    p = device.decode({"eid": 4121, "edata": "02"})
    assert p == {"action": "timeout"}


def test_2455():
    device = XDevice(2455)
    assert device.market_name == "Honeywell Smoke Alarm"
    p = device.decode({"eid": 4117, "edata": "01"})
    assert p == {"smoke": True}
    p = device.decode({"eid": 4117, "edata": "02"})
    assert p == {"action": "error"}


def test_4611():
    device = XDevice(4611)
    assert device.market_name == "Xiaomi TH Sensor"

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/490
    p = device.decode({"eid": 19464, "edata": "cdcc3e42"})
    assert p == {"humidity": 47.7}

    p = device.decode({"eid": 19457, "edata": "cdcca841"})
    assert p == {"temperature": 21.1}

    # new miIO format for Gateway fw 1.5.4+
    # https://github.com/AlexxIT/XiaomiGateway3/issues/929
    p = device.decode({"siid": 3, "piid": 1008, "value": 39.099998})
    assert p == {"humidity": 39.1}

    p = device.decode({"siid": 3, "piid": 1001, "value": 24.600000})
    assert p == {"temperature": 24.6}


def test_1694():
    device = XDevice(1694)
    assert device.market_name == "Aqara Door Lock N100 (Bluetooth)"

    p = device.decode({"eid": 4106, "edata": "329aaecd62"})
    assert p == {"battery": 50}

    p = device.decode({"eid": 11, "edata": "a400000000b8aecd62"})
    assert p == {
        "action": "lock",
        "action_id": 4,
        "error": None,
        "key_id": 0,
        "message": "Unlock inside the door",
        "method": "manual",
        "method_id": 10,
        "timestamp": "2022-07-12T20:26:16",
    }

    p = device.decode({"eid": 7, "edata": "00c5aecd62"})
    assert p == {
        "action": "door",
        "action_id": 0,
        "contact": True,
        "message": "Door is open",
        "timestamp": "2022-07-12T20:26:29",
    }

    p = device.decode({"eid": 7, "edata": "01cbaecd62"})
    assert p == {
        "action": "door",
        "action_id": 1,
        "contact": False,
        "message": "Door is closed",
        "timestamp": "2022-07-12T20:26:35",
    }

    p = device.decode({"eid": 11, "edata": "2002000180c4aecd62"})
    assert p == {
        "action": "lock",
        "action_id": 0,
        "error": None,
        "key_id": 2,
        "message": "Unlock outside the door",
        "method": "biological",
        "method_id": 2,
        "timestamp": "2022-07-12T20:26:28",
    }

    p = device.decode({"eid": 6, "edata": "ffffffff00"})
    assert p == {
        "action": "fingerprint",
        "action_id": 0,
        "key_id": "0xffffffff",
        "message": "Match successful",
    }

    p = device.decode({"eid": 8, "edata": "01"})
    assert p == {"action": "armed"}

    p = device.decode({"eid": 8, "edata": "00"})
    assert p == {"action": "disarmed"}


def test_9095():
    device = XDevice(9095)
    assert device.market_name == "Xiaomi Wireless Button"

    # old format
    p = device.decode({"eid": 19980, "edata": ""})
    assert p == {"action": "single"}
    p = device.decode({"eid": 19981, "edata": ""})
    assert p == {"action": "double"}
    p = device.decode({"eid": 19982, "edata": ""})
    assert p == {"action": "hold"}

    # new format
    p = device.decode({"siid": 3, "eiid": 1012, "arguments": []})
    assert p == {"action": "single"}
    p = device.decode({"siid": 3, "eiid": 1013, "arguments": []})
    assert p == {"action": "double"}
    p = device.decode({"siid": 3, "eiid": 1014, "arguments": []})
    assert p == {"action": "hold"}


def test_10987():
    device = XDevice(10987)
    assert device.market_name == "Linptech Motion Sensor 2"

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/809
    p = device.decode({"eid": 18952, "edata": "00008041"})
    assert p == {"motion": True, "illuminance": 16.0}
    p = device.decode({"eid": 18456, "edata": "3c00"})
    assert p == {"idle_time": 60}
    p = device.decode({"eid": 18953, "edata": "54020040"})  # unknown
    assert p == {"unknown": "54020040"}

    # new format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/956
    p = device.decode(
        {"siid": 2, "eiid": 1008, "arguments": [{"piid": 1005, "value": 23.000000}]}
    )
    assert p == {"motion": True, "illuminance": 23.0}


def test_7184():
    device = XDevice(7184)
    assert device.market_name

    # old format
    # https://github.com/AlexxIT/XiaomiGateway3/pull/844
    p = device.decode({"eid": 19980, "edata": "01"})
    assert p == {"action": "single"}

    # new format
    # https://github.com/AlexxIT/XiaomiGateway3/issues/867
    # https://github.com/AlexxIT/XiaomiGateway3/issues/826
    p = device.decode({"siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 1}]})
    assert p == {"action": "single"}

    p = device.decode(
        {"siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 15}]}
    )
    assert p == {"action": "double"}


def test_6473():
    device = XDevice(6473)
    assert device.market_name == "Yeelight Double Button"

    # new format https://github.com/AlexxIT/XiaomiGateway3/issues/965
    p = device.decode({"siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 1}]})
    assert p == {"action": "button_1_single"}

    p = device.decode({"siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 2}]})
    assert p == {"action": "button_2_single"}

    p = device.decode({"siid": 3, "eiid": 1013, "arguments": [{"piid": 1, "value": 1}]})
    assert p == {"action": "button_1_double"}

    p = device.decode({"siid": 3, "eiid": 1013, "arguments": [{"piid": 1, "value": 2}]})
    assert p == {"action": "button_2_double"}

    p = device.decode({"siid": 3, "eiid": 1014, "arguments": [{"piid": 1, "value": 1}]})
    assert p == {"action": "button_1_hold"}

    p = device.decode({"siid": 3, "eiid": 1014, "arguments": [{"piid": 1, "value": 2}]})
    assert p == {"action": "button_2_hold"}

    p = device.decode({"siid": 3, "eiid": 1012, "arguments": [{"piid": 1, "value": 3}]})
    assert p == {"action": "button_both_single"}


def test_9385():
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1169
    device = XDevice(9385)
    assert device.market_name == "Mijia Timer"

    p = device.decode({"siid": 2, "eiid": 1025, "arguments": []})
    assert p == {"action": "timer1"}

    p = device.decode({"siid": 3, "eiid": 1025, "arguments": []})
    assert p == {"action": "timer2"}


def test_10249():
    device = XDevice(10249)
    assert device.market_name == "Xiaomi Door Lock E10"

    p = device.decode([{"siid": 4, "piid": 1021, "value": 2}])
    assert p == {"door": "unlocked"}

    p = device.decode(
        {
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

    p = device.decode(
        {
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

    p = device.decode(
        {"siid": 6, "eiid": 1006, "arguments": [{"piid": 1, "value": 1681029598}]}
    )
    assert p == {"action": "doorbell", "timestamp": 1681029598}
