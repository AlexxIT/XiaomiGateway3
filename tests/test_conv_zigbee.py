from custom_components.xiaomi_gateway3 import XDevice
from custom_components.xiaomi_gateway3.core.converters import silabs


def test_zigbee_plug():
    device = XDevice("TS0121", nwk="0x1234")
    p = device.encode_read({"plug"})
    assert p == {
        "commands": [
            {"commandcli": "zcl global read 6 0"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }

    p = device.encode_read({conv.attr for conv in device.converters})
    assert p == {
        "commands": [
            {"commandcli": "zcl global read 6 0"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "raw 2820 {100000050508050b05}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "raw 2820 {100000050508050b05}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "raw 2820 {100000050508050b05}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 1794 0"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 6 32770"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }


def test_ikea_cover():
    device = XDevice("FYRTUR block-out roller blind", nwk="0x1234")
    attrs = {i.attr for i in device.converters}
    p = device.encode_read(attrs)
    assert p == {
        "commands": [
            {"commandcli": "zcl global read 258 8"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "raw 1 {10000021002000}"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }

    p = device.encode({"motor": "close"})
    assert p == {
        "commands": [
            {"commandcli": "raw 258 {110001}"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }

    p = device.encode({"position": 23})
    assert p == {
        "commands": [
            {"commandcli": "raw 258 {1100084d}"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }


def test_aqara_cube():
    device = XDevice("lumi.sensor_cube")
    p = device.decode(
        {
            "clusterId": "0x0012",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x18140A5500215900",
        }
    )
    assert p == {"action": "flip90", "from_side": 3, "to_side": 1}


def test_aqara_gas():
    device = XDevice("")
    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x1C5F113C01F0FF00270200011100000101",
        }
    )
    assert p


def test_sonoff_motion():
    device = XDevice("MS01", nwk="0x1234")

    p = device.decode(
        {
            "clusterId": "0x0001",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x18AC0A2000201E",
        }
    )
    assert p == {"battery_voltage": 3000}

    p = device.decode(
        {
            "clusterId": "0x0001",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x18AD0A210020C8",
        }
    )
    assert p == {"battery": 100}

    p = device.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x190300000000000000",
        }
    )
    assert p == {"occupancy": False}

    p = device.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x190400010000000000",
        }
    )
    assert p == {"occupancy": True}


def test_aqara_bulb():
    device = XDevice("lumi.light.acn014", nwk="0x1234")
    p = device.encode({"brightness": 50, "transition": 5.0})
    assert p == {
        "commands": [
            {"commandcli": "zcl level-control o-mv-to-level 50 50"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }
