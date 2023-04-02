from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.converters import MESH
from custom_components.xiaomi_gateway3.core.device import XDevice

assert DOMAIN  # fix circular import


def test_mesh():
    device = XDevice(MESH, 1771, "123", "112233aabbcc")
    assert device.info.name == "Xiaomi Mesh Bulb"
    device.setup_converters()

    p = device.decode_lumi(
        [
            {"did": "1234567890", "siid": 2, "piid": 1, "value": True, "code": 0},
            {"did": "1234567890", "siid": 2, "piid": 2, "value": 65535, "code": 0},
            {"did": "1234567890", "siid": 2, "piid": 3, "value": 4000, "code": 0},
        ]
    )
    assert p == {"light": True, "brightness": 255.0, "color_temp": 250}


def test_event():
    device = XDevice(MESH, 1946, "123", "112233aabbcc")
    device.setup_converters()

    p = device.decode_miot(
        [{"did": "1234567890", "siid": 8, "eiid": 1, "arguments": []}]
    )
    assert p == {"button_1": 1, "action": "button_1_single"}


def test_brightness():
    device = XDevice(MESH, 3164, "123", "112233aabbcc")
    device.setup_converters()

    p = device.encode({"light": True, "brightness": 15.0, "color_temp": 300})
    assert p["mi_spec"] == [
        {"siid": 2, "piid": 1, "value": True},
        {"siid": 2, "piid": 2, "value": 6},
        {"siid": 2, "piid": 3, "value": 3333},
    ]


def test_es1():
    device = XDevice(MESH, 10441, "123", "112233aabbcc")
    device.setup_converters()

    p = device.decode_lumi(
        [
            {
                "did": "123",
                "siid": 3,
                "eiid": 1,
                "arguments": [{"piid": 1, "value": 1}],
            }
        ]
    )
    assert p == {"approach_away": True, "action": "approach"}
