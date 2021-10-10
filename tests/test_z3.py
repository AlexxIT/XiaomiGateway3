from custom_components.xiaomi_gateway3.core.gateway3 import Gateway3


def test_console():
    class Entity:
        passed = False

        def update(self, data: dict):
            assert data == {
                'eui64': '0x00158D0000000002', 'nwk': '0x131e', 'ago': 335,
                'type': 'router', 'parent': '0x1f0c'
            }
            Entity.passed = True

    gw = Gateway3('', '')
    gw.devices['lumi.158d0000000002'] = {
        'nwk': '0x131e',
        'stats': Entity()
    }
    # gw.add_stats('0x00158D0000000002', handler)
    gw.z3buffer = {
        "plugin device-table print":
            "0 E265:  00158D0000000000 0  JOINED 882\r"
            "1 7585:  00158D0000000001 0  JOINED 335\r"
            "2 131E:  00158D0000000002 0  JOINED 335\r"
            "3 1F0C:  00158D0000000003 0  JOINED 247\r",
        "plugin stack-diagnostics child-table":
            "0: Sleepy 0xE265 (>)00158D0000000000 512 min debug timeout:249\r"
            "1: Sleepy 0x7585 (>)00158D0000000001 512 min debug timeout:249\r",
        "plugin stack-diagnostics neighbor-table":
            "0: 0x131E 201 1 1 3 (>)00158D0000000002\r"
            "1: 0x1F0C 172 1 0 7 (>)00158D0000000003\r",
        "buffer":
            "0: 0x1F0C -> 0x0000 (Me)\r"
            "1: 0x131E -> 0x1F0C -> 0x0000 (Me)\r"
    }
    gw.process_z3("CLI command executed: plugin concentrator print-table\r")
    assert Entity.passed
