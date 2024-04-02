from custom_components.xiaomi_gateway3 import XDevice
from custom_components.xiaomi_gateway3.core.const import ZIGBEE
from custom_components.xiaomi_gateway3.core.converters import silabs


def decode(device: XDevice, data: dict) -> dict:
    data.setdefault("sourceEndpoint", "0x01")
    return device.decode(data)


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
            {"commandcli": "zcl global read 2820 1285"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 2820 1288"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 2820 1291"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 1794 0"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 6 32770"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }

    assert silabs.optimize_read(p["commands"])
    assert p == {
        "commands": [
            {"commandcli": "raw 6 {10000000000280}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "raw 2820 {100000050508050b05}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 1794 0"},
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
            {"commandcli": "zcl global read 1 33"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl global read 1 32"},
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
            {"commandcli": "raw 258 {1100054d}"},
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
    p = device.encode({"transition": 2.5, "brightness": 50})
    assert p == {
        "commands": [
            {"commandcli": "zcl level-control o-mv-to-level 50 25"},
            {"commandcli": "send 0x1234 1 1"},
        ],
        "transition": 2.5,
    }


def test_unknown_device():
    device = XDevice("dummy", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa")
    p = decode(device, {"clusterId": "0x0400", "APSPlayload": "0x18610A0000211F00"})
    assert p == {"illuminance": 31}
    p = decode(device, {"clusterId": "0x0402", "APSPlayload": "0x18020A0000298C07"})
    assert p == {"temperature": 19.32}
    p = decode(device, {"clusterId": "0x0405", "APSPlayload": "0x18030A000021CC0F"})
    assert p == {"humidity": 40.44}
    p = decode(device, {"clusterId": "0x000C", "APSPlayload": "0x18630A5500398FC23541"})
    assert p == {"analog": 11.36}
    p = decode(device, {"clusterId": "0x0001", "APSPlayload": "0x189B0A2000201E"})
    assert p == {"battery_voltage": 3000}
    p = decode(device, {"clusterId": "0x0001", "APSPlayload": "0x08660A200020FF"})
    assert p == {"battery_voltage": 25500}
    p = decode(device, {"clusterId": "0x0406", "APSPlayload": "0x18620A00001801"})
    assert p == {"occupancy": True}
    p = decode(device, {"clusterId": "0x0500", "APSPlayload": "0x195300010000FF0000"})
    assert p == {"binary": True}
    p = decode(device, {"clusterId": "0x0300", "APSPlayload": "0x18280107000021C700"})
    assert p == {"color_temp": 199}


def test_error():
    payload = {"clusterId": "0x0001", "APSPlayload": "0x182701210086"}
    p = silabs.decode(payload)
    assert p == {"cluster": "power", "general_command_id": 1, 33: None}

    device = XDevice("dummy", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa")
    p = decode(device, payload)
    assert p == {}
