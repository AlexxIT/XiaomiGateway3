from custom_components.xiaomi_gateway3.core.converters import silabs, ZIGBEE
from custom_components.xiaomi_gateway3.core.device import XDevice

ZDID = "lumi.112233aabbcc"
ZMAC = "0x0000112233aabbcc"
ZNWK = "0x12ab"


def test_cli():
    p = silabs.zcl_read("0x1234", 1, 0x0B04, [1285, 1288, 1291])
    assert p == [
        {'commandcli': 'raw 2820 {100000050508050b05}'},
        {'commandcli': 'send 0x1234 1 1'}
    ]


def test_():
    device = XDevice(ZIGBEE, "MS01", ZDID, ZMAC, ZNWK)
    assert device.info.name == "Sonoff Motion Sensor"
    device.setup_converters()

    p = silabs.decode({
        "clusterId": "0x0001", "sourceEndpoint": "0x01",
        "APSPlayload": "0x18AC0A2000201E"
    })
    p = device.decode_zigbee(p)
    assert p == {'battery_voltage': 3000}

    p = silabs.decode({
        "clusterId": "0x0001", "sourceEndpoint": "0x01",
        "APSPlayload": "0x18AD0A210020C8"
    })
    p = device.decode_zigbee(p)
    assert p == {'battery': 100}

    p = silabs.decode({
        "clusterId": "0x0500", "sourceEndpoint": "0x01",
        "APSPlayload": "0x190300000000000000",
    })
    p = device.decode_zigbee(p)
    assert p == {'motion': False}

    p = silabs.decode({
        "clusterId": "0x0500", "sourceEndpoint": "0x01",
        "APSPlayload": "0x190400010000000000"
    })
    p = device.decode_zigbee(p)
    assert p == {'motion': True}
