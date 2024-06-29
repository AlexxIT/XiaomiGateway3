from custom_components.xiaomi_gateway3.core.device import XDevice


def test_gateway_read():
    device = XDevice("lumi.gateway.mgl03")
    attrs = {i.attr for i in device.converters}
    p = device.encode_read(attrs)
    assert p == {
        "cmd": "read",
        "did": None,
        "params": [
            {"res_name": "8.0.2109"},
            {"res_name": "8.0.2110"},
            {"res_name": "8.0.2111"},
            {"res_name": "8.0.2084"},
            {"res_name": "8.0.2082"},
            {"res_name": "8.0.2080"},
            {"res_name": "8.0.2166"},
            {"res_name": "8.0.2091"},
            {"res_name": "8.0.2012"},
            {"res_name": "8.0.2024"},
            {"did": None, "siid": 3, "piid": 1},
            {"did": None, "siid": 3, "piid": 22},
            {"did": None, "siid": 6, "piid": 6},
        ],
        "method": "get_properties",
    }


def test_gas_read():
    device = XDevice("lumi.sensor_natgas")
    attrs = {i.attr for i in device.converters}
    p = device.encode_read(attrs)
    assert p == {
        "cmd": "read",
        "commands": [
            {"commandcli": "zcl mfg-code 4447"},
            {"commandcli": "zcl global read 1280 65520"},
            {"commandcli": "send 0x0000 1 1"},
        ],
        "did": None,
        "params": [{"res_name": "0.1.85"}, {"res_name": "13.1.85"}],
    }
