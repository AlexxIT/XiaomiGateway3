from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.converters import silabs, ZIGBEE
from custom_components.xiaomi_gateway3.core.converters.zigbee import ZConverter
from custom_components.xiaomi_gateway3.core.device import XDevice

assert DOMAIN  # fix circular import

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


def test_tuya_button():
    device = XDevice(ZIGBEE, "TS004F", ZDID, ZMAC, ZNWK)
    device.setup_converters()

    p0 = silabs.decode({
        "clusterId": "0x0006", "sourceEndpoint": "0x03",
        "APSPlayload": "0x010AFD02",
    })
    p = device.decode_zigbee(p0)
    assert p == {'button_3': 'hold', 'action': 'button_3_hold'}

    # test processing same sequence
    p = device.decode_zigbee(p0)
    assert p == {}


def test_config():
    device = XDevice(ZIGBEE, "TS004F", ZDID, ZMAC, ZNWK)
    device.setup_converters()

    gw = type("", (), {"ieee": "0xAABBCC"})

    p = {}
    for conv in device.converters:
        if isinstance(conv, ZConverter):
            conv.config(device, p, gw)

    assert p['commands'] == [
        {'commandcli': 'raw 6 {10000004000000010005000700feff}'},
        {'commandcli': 'send 0x12ab 1 1'},
        {'commandcli': 'zcl global read 57345 53265'},
        {'commandcli': 'send 0x12ab 1 1'},
        {'commandcli': 'zdo bind 0x12ab 1 1 6 {0000112233aabbcc} {0xAABBCC}'},
        {'commandcli': 'zdo bind 0x12ab 2 1 6 {0000112233aabbcc} {0xAABBCC}'},
        {'commandcli': 'zdo bind 0x12ab 3 1 6 {0000112233aabbcc} {0xAABBCC}'},
        {'commandcli': 'zdo bind 0x12ab 4 1 6 {0000112233aabbcc} {0xAABBCC}'},
        {'commandcli': 'zdo bind 0x12ab 1 1 1 {0000112233aabbcc} {0xAABBCC}'},
        {'commandcli': 'zcl global write 6 32772 48 {01}'},
        {'commandcli': 'send 0x12ab 1 1'}
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
    assert p == {'occupancy': False}

    p = silabs.decode({
        "clusterId": "0x0500", "sourceEndpoint": "0x01",
        "APSPlayload": "0x190400010000000000"
    })
    p = device.decode_zigbee(p)
    assert p == {'occupancy': True}


def test_silabs_decode():
    p = silabs.decode({
        "clusterId": "0x0006", "sourceEndpoint": "0x01",
        "APSPlayload": "0x08080A04803001"
    })
    assert p == {
        'endpoint': 1, 'seq': 8, 'cluster': 'on_off',
        'command': 'Report_Attributes', 32772: 1
    }

    p = silabs.decode({
        "clusterId": "0x0006", "sourceEndpoint": "0x03",
        "APSPlayload": "0x010AFD02"
    })
    assert p == {
        'endpoint': 3, 'seq': 10, 'cluster': 'on_off', 'command_id': 253,
        'value': b'\x02'
    }


def test_ias_zone():
    p = silabs.decode({
        "clusterId": "0x0500", "sourceEndpoint": "0x01",
        "APSPlayload": "0x096700210000000000"
    })
    p['value'] = list(p['value'])
    assert p == {
        'endpoint': 1, 'seq': 103, 'cluster': 'ias_zone', 'command_id': 0,
        'command': 'enroll_response', 'value': [33, 0, 0, 0]
    }
