from datetime import datetime

from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.converters import stats, GATEWAY, ZIGBEE
from custom_components.xiaomi_gateway3.core.device import XDevice

assert DOMAIN  # fix circular import

DID = "123456789"
MAC = "112233aabbcc"
ZDID = "lumi.112233aabbcc"
ZMAC = "0x0000112233aabbcc"
ZNWK = "0x12ab"


def test_gateway_stats():
    device = XDevice(GATEWAY, "lumi.gateway.mgl03", DID, MAC)
    device.setup_converters()

    p = device.decode(GATEWAY, {"networkUp": False})
    assert p == {"network_pan_id": None, "radio_channel": None, "radio_tx_power": None}

    p = device.decode(
        GATEWAY,
        {
            "networkUp": True,
            "networkPanId": "0x9180",
            "radioTxPower": 7,
            "radioChannel": 15,
        },
    )
    assert p == {"network_pan_id": "0x9180", "radio_tx_power": 7, "radio_channel": 15}

    p = device.decode(
        GATEWAY,
        {
            "free_mem": 3488,
            "ip": "192.168.1.123",
            "load_avg": "1.92|2.00|2.25|5/91|21135",
            "rssi": 58,
            "run_time": 367357,
            "setupcode": "123-45-678",
            "ssid": "WiFi",
            "tz": "GMT3",
        },
    )
    assert p == {
        "free_mem": 3488,
        "load_avg": "1.92|2.00|2.25|5/91|21135",
        "rssi": -42,
        "uptime": "4 days, 06:02:37",
    }

    p = device.decode(
        GATEWAY,
        {
            "serial": """serinfo:1.0 driver revision:
0: uart:16550A mmio:0x18147000 irq:17 tx:6337952 rx:0 RTS|CTS|DTR
1: uart:16550A mmio:0x18147400 irq:46 tx:19370 rx:154557484 oe:1684 RTS|DTR
2: uart:16550A mmio:0x18147800 irq:47 tx:1846359 rx:3845724 oe:18 RTS|DTR"""
        },
    )
    assert p == {
        "bluetooth_tx": 19370,
        "bluetooth_rx": 154557484,
        "bluetooth_oe": 1684,
        "zigbee_tx": 1846359,
        "zigbee_rx": 3845724,
        "zigbee_oe": 18,
    }


def test_zigbee_stats():
    stats.now = lambda: datetime(2021, 12, 31, 23, 59)

    device = XDevice(ZIGBEE, "lumi.plug", ZDID, ZMAC, ZNWK)
    device.setup_converters({ZIGBEE: "sensor"})

    p = device.decode(
        ZIGBEE,
        {
            "sourceAddress": "0x9B43",
            "eui64": "0x00158D0000AABBCC",
            "destinationEndpoint": "0x01",
            "clusterId": "0x000A",
            "profileId": "0x0104",
            "sourceEndpoint": "0x01",
            "APSCounter": "0x71",
            "APSPlayload": "0x1071000000",
            "rssi": -61,
            "linkQuality": 156,
        },
    )
    assert p == {
        "zigbee": p["zigbee"],
        # 'ieee': '0x00158D0000AABBCC', 'nwk': '0x9B43',
        "msg_received": 1,
        "msg_missed": 0,
        "linkquality": 156,
        "rssi": -61,
        "last_msg": "Time",
    }

    p = device.decode(
        ZIGBEE,
        {
            "sourceAddress": "0x9B43",
            "eui64": "0x00158D0000AABBCC",
            "destinationEndpoint": "0x01",
            "clusterId": "0x000A",
            "profileId": "0x0104",
            "sourceEndpoint": "0x01",
            "APSCounter": "0x73",
            "APSPlayload": "0x1075000000",
            "rssi": -61,
            "linkQuality": 156,
        },
    )
    assert p == {
        "zigbee": p["zigbee"],
        # 'ieee': '0x00158D0000AABBCC', 'nwk': '0x9B43',
        "msg_received": 2,
        "msg_missed": 1,
        "linkquality": 156,
        "rssi": -61,
        "last_msg": "Time",
    }

    p = device.decode(
        ZIGBEE,
        {
            "sourceAddress": "0x9B43",
            "eui64": "0x00158D0000AABBCC",
            "destinationEndpoint": "0x01",
            "clusterId": "0x000A",
            "profileId": "0x0104",
            "sourceEndpoint": "0x01",
            "APSCounter": "0x72",
            "APSPlayload": "0x1074000000",
            "rssi": -61,
            "linkQuality": 156,
        },
    )
    assert p == {
        "zigbee": p["zigbee"],
        # 'ieee': '0x00158D0000AABBCC', 'nwk': '0x9B43',
        "msg_received": 3,
        "msg_missed": 1,
        "linkquality": 156,
        "rssi": -61,
        "last_msg": "Time",
    }

    p = device.decode(
        ZIGBEE,
        {"eui64": "", "nwk": "0x9B43", "ago": 60, "type": "device", "parent": "0xABCD"},
    )
    assert p == {"parent": "0xABCD"}

    # p = device.decode(ZIGBEE, {'parent': '0xABCD'})
    # assert p == {'parent': '0xABCD'}

    # p = device.decode(ZIGBEE, {'resets': 10})
    # assert p == {'new_resets': 0}

    # p = device.decode(ZIGBEE, {'resets': 15})
    # assert p == {'new_resets': 5}


def test_154_stats():
    device = XDevice(GATEWAY, "lumi.gateway.mgl03", DID, MAC)
    device.setup_converters()

    p = device.decode(
        GATEWAY,
        {
            "serial": """serinfo:1.0 driver revision:
0: uart:16550A mmio:0x18147000 irq:17 tx:360643 rx:0 RTS|CTS|DTR
1: uart:16550A mmio:0x18147400 irq:46 tx:1664 rx:36814303 fe:6 RTS|CTS|DTR
2: uart:16550A mmio:0x18147800 irq:47 tx:56627 rx:88704 oe:52 RTS|DTR"""
        },
    )
    assert p == {
        "bluetooth_tx": 1664,
        "bluetooth_rx": 36814303,
        "bluetooth_fe": 6,
        "zigbee_tx": 56627,
        "zigbee_rx": 88704,
        "zigbee_oe": 52,
    }
