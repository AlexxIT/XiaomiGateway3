from custom_components.xiaomi_gateway3.core.converters.silabs import zcl_read

ZDID = "lumi.112233aabbcc"
ZMAC = "0x0000112233aabbcc"
ZNWK = "0x12ab"


def test_cli():
    p = zcl_read("0x1234", 1, 0x0B04, [1285, 1288, 1291])
    assert p == [
        {'commandcli': 'raw 2820 {100000050508050b05}'},
        {'commandcli': 'send 0x1234 1 1'}
    ]
