from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core import converters
from custom_components.xiaomi_gateway3.core.converters import GATEWAY, ZIGBEE, BLE, MESH
from custom_components.xiaomi_gateway3.core.device import XDevice

assert DOMAIN  # fix circular import

BDID = "blt.3.abc"
GDID = "1234567890"
ZDID = "lumi.112233aabbcc"

IEEE = "0x0000112233aabbcc"
MAC = "aabbccddeeff"
NWK = "0x12ab"


def test_buttons():
    device = XDevice(GATEWAY, "lumi.gateway.mgl03", GDID, MAC)
    b = converters.get_buttons(device.info.model)
    assert b is None

    device = XDevice(ZIGBEE, "lumi.sensor_switch", ZDID, IEEE, NWK)
    b = converters.get_buttons(device.info.model)
    assert b == ["button"]

    device = XDevice(ZIGBEE, "lumi.ctrl_ln2", ZDID, IEEE, NWK)
    b = converters.get_buttons(device.info.model)
    assert b == ["button_1", "button_2", "button_both"]

    device = XDevice(ZIGBEE, "lumi.switch.l3acn3", ZDID, IEEE, NWK)
    b = converters.get_buttons(device.info.model)
    assert b == [
        "button_1",
        "button_2",
        "button_3",
        "button_both_12",
        "button_both_13",
        "button_both_23",
    ]

    device = XDevice(ZIGBEE, "lumi.remote.acn004", ZDID, IEEE, NWK)
    b = converters.get_buttons(device.info.model)
    assert b == ["button_1", "button_2", "button_both"]

    device = XDevice(BLE, 1983, BDID, MAC)
    b = converters.get_buttons(device.info.model)
    assert b == ["button"]

    device = XDevice(MESH, 1946, GDID, MAC)
    b = converters.get_buttons(device.info.model)
    assert b == ["button_1", "button_2"]
