from custom_components.xiaomi_gateway3.core.converters import GATEWAY
from custom_components.xiaomi_gateway3.core.device import XDevice

DID = "123456789"
MAC = "112233aabbcc"


def test_gateway():
    device = XDevice(GATEWAY, "lumi.gateway.mgl03", DID, MAC)
    assert device.info.name == "Xiaomi Multimode Gateway"
    device.setup_converters()

    p = device.decode_lumi([{"res_name": "8.0.2109", "value": 60}])
    assert p == {"pair": True}

    p = device.encode({"pair": False})
    assert p == {"params": [{"res_name": "8.0.2109", "value": 0}]}

    # old zigbee pairing
    p = device.decode_lumi(
        [
            {
                "res_name": "8.0.2111",
                "value": {
                    "code": 0,
                    "install_code": "",
                    "mac": "",
                    "message": "no data",
                },
                "error_code": 0,
            }
        ]
    )
    assert p

    # _sync.zigbee3_get_install_code error
    p = device.decode_lumi(
        [
            {
                "res_name": "8.0.2111",
                "value": {
                    "code": -4001002,
                    "install_code": "",
                    "mac": "",
                    "message": "no data",
                },
                "error_code": 0,
            }
        ]
    )
    assert p

    # zigbee3 pairing
    p = device.decode_lumi(
        [
            {
                "res_name": "8.0.2111",
                "value": {"code": 0, "install_code": "<36 hex>", "mac": "<16 hex>"},
                "error_code": 0,
            }
        ]
    )
    assert p

    # p = device.decode_lumi(
    #     [{"res_name": "8.0.2155", "value": '{"cloud_link":1,"tz_updated":"GMT3"}'}]
    # )
    # assert p == {"cloud_link": True}

    # p = device.decode_lumi([{"res_name": "8.0.2155", "value": 1}])
    # assert p == {"cloud_link": True}
