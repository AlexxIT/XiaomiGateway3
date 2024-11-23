from custom_components.xiaomi_gateway3 import XDevice


def test_es1():
    device = XDevice(10441)

    # p = device.decode({"siid": 3, "eiid": 1, "arguments": [{"piid": 1, "value": 1}]})
    # assert p == {"approach_away": True, "action": "approach"}

    p = device.decode({"siid": 3, "piid": 2, "value": 5})
    assert p == {"induction_range": "0+0.8_1.5+2.3_3.0_3.8_4.5_5.3_6"}

    p = device.encode({"induction_range": "0+0.8+1.5+2.3+3.0_3.8_4.5_5.3_6"})
    assert p["params"] == [{"did": None, "piid": 2, "siid": 3, "value": 15}]


def test_11724():
    device = XDevice(11724)

    p = device.decode({"did": "123", "siid": 3, "piid": 16, "value": 23591044})
    assert p == {"night_light_time": "23:59-10:44"}

    p = device.encode({"night_light_time": "23:59-10:44"})
    assert p["params"] == [{"did": None, "siid": 3, "piid": 16, "value": 23591044}]


def test_17573():
    device = XDevice(17573)

    p = device.decode({"did": "123", "siid": 2, "piid": 1, "value": True})
    assert p == {"light": True}

    p = device.decode({"did": "123", "siid": 2, "piid": 4, "value": 16711680})
    assert p == {"rgb_color": (255, 0, 0)}

    p = device.decode({"did": "123", "siid": 2, "piid": 4, "value": 65280})
    assert p == {"rgb_color": (0, 255, 0)}

    p = device.decode({"did": "123", "siid": 2, "piid": 4, "value": 255})
    assert p == {"rgb_color": (0, 0, 255)}

    p = device.encode({"rgb_color": (255, 255, 0)})
    assert p["params"] == [{"did": None, "piid": 4, "siid": 2, "value": 16776960}]
