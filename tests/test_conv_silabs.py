from custom_components.xiaomi_gateway3.core.converters import silabs, ZIGBEE
from custom_components.xiaomi_gateway3.core.device import XDevice

ZDID = "lumi.112233aabbcc"
ZMAC = "0x0000112233aabbcc"
ZNWK = "0x12ab"


def test_cli():
    p = silabs.zcl_read("0x1234", 1, "on_off", "on_off")
    assert p == [
        {'commandcli': 'zcl global read 6 0'},
        {'commandcli': 'send 0x1234 1 1'}
    ]

    p = silabs.zcl_read(
        "0x1234", 1, "electrical_measurement", "rms_voltage", "rms_current",
        "active_power"
    )
    assert p == [
        {'commandcli': 'raw 2820 {100000050508050b05}'},
        {'commandcli': 'send 0x1234 1 1'}
    ]

    p = silabs.zcl_write("0x1234", 1, 0xFCC0, 9, 1, type=0x20, mfg=0x115f)
    assert p == [
        {'commandcli': 'zcl mfg-code 4447'},
        {'commandcli': 'zcl global write 64704 9 32 {01}'},
        {'commandcli': 'send 0x1234 1 1'}
    ]


def test_aqara_cube():
    device = XDevice(ZIGBEE, "lumi.sensor_cube", ZDID, ZMAC, ZNWK)
    assert device.info.name == "Aqara Cube"
    device.setup_converters()

    p = silabs.decode({
        "clusterId": "0x0012", "sourceEndpoint": "0x02",
        "APSPlayload": "0x18140A5500215900"
    })
    p = device.decode_zigbee(p)
    assert p == {'action': 'flip90', 'from_side': 3, 'to_side': 1}


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
    assert p == {'occupancy': False}

    p = silabs.decode({
        "clusterId": "0x0500", "sourceEndpoint": "0x01",
        "APSPlayload": "0x190400010000000000"
    })
    p = device.decode_zigbee(p)
    assert p == {'occupancy': True}
