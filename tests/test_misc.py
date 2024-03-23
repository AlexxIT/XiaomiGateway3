import copy
from dataclasses import dataclass

from bellows.uart import Gateway
from sensor_state_data import BinarySensorDeviceClass

from custom_components.xiaomi_gateway3.core.converters.base import BaseConv


def test_bellows():
    class FakeTransport:
        calls = []

        def frame_received(self, data):
            self.calls.append(("frame_received", data))

        def write(self, data):
            self.calls.append(("write", data))

    fake = FakeTransport()

    uart = Gateway(fake)
    uart.connection_made(fake)

    uart.data_received(bytes.fromhex("45"))
    uart.data_received(bytes.fromhex("41a157"))
    uart.data_received(bytes.fromhex("547915ac"))
    uart.data_received(bytes.fromhex("4d7e"))

    assert fake.calls


def test_dataclass():
    @dataclass
    class Base:
        attr: str
        domain: str = None

    @dataclass
    class First(Base):
        domain: str = "switch"

    item = First("plug")
    assert item.attr == "plug"
    assert item.domain == "switch"

    item = First("plug", "test")
    assert item.attr == "plug"
    assert item.domain == "test"


def test_enum():
    assert "battery" in iter(BinarySensorDeviceClass)
    assert "battery2" not in iter(BinarySensorDeviceClass)


def test_copy():
    conv1 = BaseConv("plug", "sensor")
    conv2 = copy.copy(conv1)
    conv2.domain = "light"
    assert conv1.domain != conv2.domain
