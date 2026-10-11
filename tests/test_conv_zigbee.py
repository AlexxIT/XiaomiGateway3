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


def test_tuya_button():
    device = XDevice("TS0041", nwk="0x1234")

    p = device.decode(
        {
            "clusterId": "0x0006",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x0135FD00",
        }
    )
    assert p == {"action": "button_single", "button": "single"}


def test_aqara_p1_contact():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa"
    )
    # IAS notifications from #1004; other zone status bits must not open the door.
    for status, contact in ((0x20, False), (0x21, True), (0x24, False), (0x25, True)):
        p = decode(
            device,
            {"clusterId": "0x0500", "APSPlayload": f"0x199C00{status:02X}0000000000"},
        )
        assert p == {"contact": contact}


def test_aqara_p1_tamper():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa", nwk="0x1234"
    )
    for value, tamper in ((0, False), (1, True)):
        p = decode(
            device,
            {"clusterId": "0xFCC0", "APSPlayload": f"0x1C5F11ED0A400110{value:02X}"},
        )
        assert p == {"tamper": tamper}
    assert decode(
        device, {"clusterId": "0xFCC0", "APSPlayload": "0x1C5F11EE01400186"}
    ) == {}
    assert device.encode_read({"tamper"}) == {
        "commands": [
            {"commandcli": "zcl mfg-code 4447"},
            {"commandcli": "zcl global read 64704 320"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }


def test_aqara_p1_battery():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa", nwk="0x1234"
    )
    for raw, voltage, battery in (
        (28, 2800, 0),
        (29, 2900, 33),
        (30, 3000, 100),
        (37, 3700, 100),
    ):
        p = decode(
            device,
            {"clusterId": "0x0001", "APSPlayload": f"0x18AC0A200020{raw:02X}"},
        )
        assert p == {"battery_voltage": voltage, "battery": battery}
    for frame in ("0x18AD01200086", "0x18AE0A200020FF"):
        assert decode(device, {"clusterId": "0x0001", "APSPlayload": frame}) == {}
    assert device.encode_read({"battery", "battery_voltage"}) == {
        "commands": [
            {"commandcli": "zcl global read 1 32"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }


def test_aqara_p1_detection_distance():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa"
    )
    # Report attribute 0x009F and readback attribute 0x010C use the same options.
    for prefix in ("0x1C5F11ED0A9F0020", "0x1C5F11ED010C010020"):
        for value, option in ((1, "10mm"), (2, "20mm"), (3, "30mm")):
            p = decode(
                device,
                {"clusterId": "0xFCC0", "APSPlayload": f"{prefix}{value:02X}"},
            )
            assert p == {"detection_distance": option}
    for frame in (
        "0x1C5F11EE0A9F0020010C012002",
        "0x1C5F11EF0A0C0120029F002001",
    ):
        assert decode(device, {"clusterId": "0xFCC0", "APSPlayload": frame}) == {
            "detection_distance": "20mm"
        }
    assert decode(
        device,
        {"clusterId": "0xFCC0", "APSPlayload": "0x1C5F11F0019F000020030C0186"},
    ) == {"detection_distance": "30mm"}
    for frame in (
        "0x1C5F11F1010C0186",
        "0x1C5F11F2010C01002004",
        "0x1C5F11F30A9F002000",
        "0x1C5F11F40A9F0020010C012004",
    ):
        assert decode(device, {"clusterId": "0xFCC0", "APSPlayload": frame}) == {}


def test_aqara_p1_detection_distance_commands():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa", nwk="0x1234"
    )
    p = device.encode({"detection_distance": "20mm"})
    silabs.optimize_read(p["commands"])
    assert p == {
        "commands": [
            {"commandcli": "zcl mfg-code 4447"},
            {"commandcli": "zcl global write 64704 268 32 {02}"},
            {"commandcli": "send 0x1234 1 1"},
            {"commandcli": "zcl mfg-code 4447"},
            {"commandcli": "zcl global read 64704 268"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }
    assert device.encode_read({"detection_distance"}) == {
        "commands": [
            {"commandcli": "zcl mfg-code 4447"},
            {"commandcli": "zcl global read 64704 268"},
            {"commandcli": "send 0x1234 1 1"},
        ]
    }


def test_aqara_p1_action():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa"
    )
    assert device.decode([{"siid": 4, "piid": 1, "value": 1}]) == {"action": "single"}
    assert device.decode([{"siid": 4, "piid": 1, "value": 2}]) == {}


def test_aqara_p1_open_time_notify_only():
    device = XDevice(
        "lumi.magnet.ac01", type=ZIGBEE, ieee="aa:aa:aa:aa:aa:aa:aa:aa", nwk="0x1234"
    )
    assert device.decode([{"siid": 5, "piid": 1, "value": 20}]) == {"open_time": 20}

    # Manual updates must not poll or write this notify-only MIoT property.
    assert device.encode_read({"open_time"}) == {}
    assert device.encode({"open_time": 0}) == {}
    assert device.encode_read(
        {"open_time", "detection_distance"}
    ) == device.encode_read({"detection_distance"})
