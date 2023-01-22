import asyncio

from custom_components.xiaomi_gateway3.core.converters import ZIGBEE
from custom_components.xiaomi_gateway3.core.device import XDevice
from custom_components.xiaomi_gateway3.core.gateway.z3 import Z3Gateway


def test_console():
    gw = Z3Gateway()
    gw.options = {}
    gw.z3_buffer = {
        "plugin device-table print": "0 E265:  00158D0000000000 0  JOINED 882\r"
        "1 7585:  00158D0000000001 0  JOINED 335\r"
        "2 131E:  00158D0000000002 0  JOINED 335\r"
        "3 1F0C:  00158D0000000003 0  JOINED 247\r",
        "plugin stack-diagnostics child-table": "0: Sleepy 0xE265 (>)00158D0000000000 512 min debug timeout:249\r"
        "1: Sleepy 0x7585 (>)00158D0000000001 512 min debug timeout:249\r",
        "plugin stack-diagnostics neighbor-table": "0: 0x131E 201 1 1 3 (>)00158D0000000002\r"
        "1: 0x1F0C 172 1 0 7 (>)00158D0000000003\r",
        "buffer": "0: 0x1F0C -> 0x0000 (Me)\r" "1: 0x131E -> 0x1F0C -> 0x0000 (Me)\r",
    }

    payload = {}

    def update(data: dict):
        payload.update(data)

    device = XDevice(ZIGBEE, "", "lumi.158d0000000002", "0x1234567890123456", "0x131e")
    device.entities = {ZIGBEE}
    device.update = update
    gw.devices[device.did] = device

    asyncio.run(
        gw.z3_process_log("CLI command executed: plugin concentrator print-table\r")
    )

    assert payload == {
        # 'eui64': '0x00158D0000000002', 'nwk': '0x131e', 'ago': 335,
        # 'type': 'router', 'parent': '0x1f0c'
    }
