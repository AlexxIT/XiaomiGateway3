import asyncio

from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.converters import MESH
from custom_components.xiaomi_gateway3.core.device import XDevice
from custom_components.xiaomi_gateway3.core.gateway.miot import MIoTGateway

assert DOMAIN  # fix circular import


def test_sequence():
    decode_miot = []

    device = XDevice(MESH, 0, "123", "112233aabbcc")
    device.decode_miot = lambda *args: decode_miot.extend(args)

    gw = MIoTGateway()
    gw.devices["123"] = device

    loop = asyncio.new_event_loop()

    # test 1
    coro = gw.miot_process_properties(
        [{"did": "123", "siid": 2, "piid": 4, "tid": 229, "value": 90}]
    )
    loop.run_until_complete(coro)

    assert decode_miot

    # test 2
    decode_miot.clear()

    coro = gw.miot_process_properties(
        [{"did": "123", "siid": 2, "piid": 4, "tid": 229, "value": 90}]
    )
    loop.run_until_complete(coro)

    assert not decode_miot
