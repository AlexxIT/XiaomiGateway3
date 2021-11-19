from custom_components.xiaomi_gateway3.core.converters import MESH
from custom_components.xiaomi_gateway3.core.device import XDevice


def test_mesh():
    device = XDevice(MESH, 1771, "123", "112233aabbcc")
    assert device.info.name == 'Xiaomi Mesh Bulb'
    device.setup_converters()

    p = device.decode_lumi([
        {'did': '1234567890', 'siid': 2, 'piid': 1, 'value': True, 'code': 0},
        {'did': '1234567890', 'siid': 2, 'piid': 2, 'value': 65535, 'code': 0},
        {'did': '1234567890', 'siid': 2, 'piid': 3, 'value': 4000, 'code': 0}
    ])
    assert p == {'light': True, 'brightness': 255.0, 'color_temp': 250}
