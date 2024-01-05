import asyncio
import json

from homeassistant.components.sensor import DOMAIN
from zigpy.types import EUI64

from custom_components.xiaomi_gateway3.core.converters import silabs, ZIGBEE
from custom_components.xiaomi_gateway3.core.converters.zigbee import ZConverter
from custom_components.xiaomi_gateway3.core.device import XDevice
from custom_components.xiaomi_gateway3.core.gateway.silabs import SilabsGateway

assert DOMAIN  # fix circular import

ZDID = "lumi.112233aabbcc"
ZMAC = "0x0000112233aabbcc"
ZNWK = "0x12ab"


def test_cli():
    p = silabs.zcl_read("0x1234", 1, "on_off", "on_off")
    assert p == [
        {"commandcli": "zcl global read 6 0"},
        {"commandcli": "send 0x1234 1 1"},
    ]

    p = silabs.zcl_read(
        "0x1234",
        1,
        "electrical_measurement",
        "rms_voltage",
        "rms_current",
        "active_power",
    )
    assert p == [
        {"commandcli": "raw 2820 {100000050508050b05}"},
        {"commandcli": "send 0x1234 1 1"},
    ]

    p = silabs.zcl_write("0x1234", 1, 0xFCC0, 9, 1, type=0x20, mfg=0x115F)
    assert p == [
        {"commandcli": "zcl mfg-code 4447"},
        {"commandcli": "zcl global write 64704 9 32 {01}"},
        {"commandcli": "send 0x1234 1 1"},
    ]


def test_aqara_cube():
    device = XDevice(ZIGBEE, "lumi.sensor_cube", ZDID, ZMAC, ZNWK)
    assert device.info.name == "Aqara Cube"
    device.setup_converters()

    p = silabs.decode(
        {
            "clusterId": "0x0012",
            "sourceEndpoint": "0x02",
            "APSPlayload": "0x18140A5500215900",
        }
    )
    p = device.decode_zigbee(p)
    assert p == {"action": "flip90", "from_side": 3, "to_side": 1}


def test_tuya_button():
    device = XDevice(ZIGBEE, "TS004F", ZDID, ZMAC, ZNWK)
    device.setup_converters()

    p0 = silabs.decode(
        {
            "clusterId": "0x0006",
            "sourceEndpoint": "0x03",
            "APSPlayload": "0x010AFD02",
        }
    )
    p = device.decode_zigbee(p0)
    assert p == {"button_3": "hold", "action": "button_3_hold"}

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

    assert p["commands"] == [
        {"commandcli": "raw 6 {10000004000000010005000700feff}"},
        {"commandcli": "send 0x12ab 1 1"},
        {"commandcli": "zcl global read 57345 53265"},
        {"commandcli": "send 0x12ab 1 1"},
        {"commandcli": "zdo bind 0x12ab 1 1 6 {0000112233aabbcc} {0xAABBCC}"},
        {"commandcli": "zdo bind 0x12ab 2 1 6 {0000112233aabbcc} {0xAABBCC}"},
        {"commandcli": "zdo bind 0x12ab 3 1 6 {0000112233aabbcc} {0xAABBCC}"},
        {"commandcli": "zdo bind 0x12ab 4 1 6 {0000112233aabbcc} {0xAABBCC}"},
        {"commandcli": "zdo bind 0x12ab 1 1 1 {0000112233aabbcc} {0xAABBCC}"},
        {"commandcli": "zcl global write 6 32772 48 {01}"},
        {"commandcli": "send 0x12ab 1 1"},
    ]


def test_config2():
    device = XDevice(ZIGBEE, "TS011F", ZDID, ZMAC, ZNWK)
    device.setup_converters()

    gw = type("", (), {"ieee": "0xAABBCC"})

    p = {}
    for conv in device.converters:
        if isinstance(conv, ZConverter):
            conv.config(device, p, gw)

    assert p["commands"] == [
        {"commandcli": "zcl global send-me-a-report 2820 1285 33 5 3600 {0100}"},
        {"commandcli": "send 0x12ab 1 1"},
        {"commandcli": "zcl global send-me-a-report 2820 1288 33 5 3600 {0100}"},
        {"commandcli": "send 0x12ab 1 1"},
        {"commandcli": "zcl global send-me-a-report 2820 1291 41 5 3600 {0100}"},
        {"commandcli": "send 0x12ab 1 1"},
        {"commandcli": "zcl global send-me-a-report 1794 0 37 5 3600 {010000000000}"},
        {"commandcli": "send 0x12ab 1 1"},
    ]


def test_():
    device = XDevice(ZIGBEE, "MS01", ZDID, ZMAC, ZNWK)
    assert device.info.name == "Sonoff Motion Sensor"
    device.setup_converters()

    p = silabs.decode(
        {
            "clusterId": "0x0001",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x18AC0A2000201E",
        }
    )
    p = device.decode_zigbee(p)
    assert p == {"battery_voltage": 3000}

    p = silabs.decode(
        {
            "clusterId": "0x0001",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x18AD0A210020C8",
        }
    )
    p = device.decode_zigbee(p)
    assert p == {"battery": 100}

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x190300000000000000",
        }
    )
    p = device.decode_zigbee(p)
    assert p == {"occupancy": False}

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x190400010000000000",
        }
    )
    p = device.decode_zigbee(p)
    assert p == {"occupancy": True}


def test_silabs_decode():
    p = silabs.decode(
        {
            "clusterId": "0x0006",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x08080A04803001",
        }
    )
    assert p == {
        "endpoint": 1,
        "seq": 8,
        "cluster": "on_off",
        "command": "Report_Attributes",
        32772: 1,
    }

    p = silabs.decode(
        {"clusterId": "0x0006", "sourceEndpoint": "0x03", "APSPlayload": "0x010AFD02"}
    )
    assert p == {
        "endpoint": 3,
        "seq": 10,
        "cluster": "on_off",
        "command_id": 253,
        "value": b"\x02",
    }


def test_ias_zone():
    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "sourceEndpoint": "0x01",
            "APSPlayload": "0x096700210000000000",
        }
    )
    p["command"] = p["command"].name
    p["value"] = [int(i) for i in p["value"]]
    assert p == {
        "endpoint": 1,
        "seq": 103,
        "cluster": "ias_zone",
        "command_id": 0,
        "command": "enroll_response",
        "value": [33, 0, 0, 0],
    }


def test_misc():
    p = silabs.decode(
        {
            "clusterId": "0x8000",
            "sourceEndpoint": "0x00",
            "APSPlayload": "0x02005D6A9303008D15002723",
        }
    )
    assert p == {
        "command": "NWK_addr_rsp",
        "status": 0,
        "nwk": 0x2327,
        "ieee": EUI64.convert("00:15:8d:00:03:93:6a:5d"),
    }


def test_hass2023_4():
    device = XDevice(ZIGBEE, "01MINIZB", ZDID, ZMAC, ZNWK)
    device.setup_converters()

    p = device.encode_read({"switch"})
    assert p == {
        "commands": [
            {"commandcli": "zcl global read 6 0"},
            {"commandcli": "send 0x12ab 1 1"},
        ]
    }


def test_message_pre_sent_callback():
    gw = SilabsGateway()
    gw.options = {"debug": ["zigbee"]}

    # Xiaomi Multimode 1 and 2
    raw = json.loads(
        b'{"eui64":"0xAABBCCDDEEFF1122","destinationEndpoint":"0x01","clusterId":"0x0006","profileId":"0x0104","sourceEndpoint":"0x01","APSCounter":"0x00","APSPlayload":"0x1001000000"}'
    )
    coro = gw.silabs_process_send(raw)
    asyncio.get_event_loop().run_until_complete(coro)

    # Xiaomi Multimode fw 1.0.7_0019+
    raw = json.loads(
        b'{"msgTick":"0x0000000000000721","type":"0x00","shortId":"0xDDCB","destinationEndpoint":"0x01","clusterId":"0x000A","profileId":"0x0104","sourceEndpoint":"0x01","APSCounter":"0x00","APSPlayload":"0x189F01000000E2407DF42C"}'
    )
    coro = gw.silabs_process_send(raw)
    asyncio.get_event_loop().run_until_complete(coro)
