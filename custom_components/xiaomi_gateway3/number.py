from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    MAJOR_VERSION,
    MINOR_VERSION,
    LENGTH_METERS,
    TIME_SECONDS,
)
from homeassistant.core import callback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        else:
            entity = XiaomiNumber(gateway, device, conv)
        async_add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


UNITS = {
    "approach_distance": LENGTH_METERS,
    "occupancy_timeout": TIME_SECONDS,
}


# noinspection PyAbstractClass
class XiaomiNumber(XEntity, NumberEntity):
<<<<<<< HEAD
    # Avoid assignment and override of deprecated attributes and methods (starting from core 2022.8)
    # while ensuring backwards compatibility
    # Addressing: https://github.com/AlexxIT/XiaomiGateway3/issues/984#issue-1586983959
    #             https://github.com/AlexxIT/XiaomiGateway3/pull/789#issuecomment-1202188504
    # Fix suggestion: https://community.home-assistant.io/t/depricated-numberentity-features/440282/2
=======
    _attr_value: float = None

    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        if self.attr in UNITS:
            self._attr_native_unit_of_measurement = UNITS[self.attr]

        if hasattr(conv, "min"):
            self._attr_min_value = conv.min
        if hasattr(conv, "max"):
            self._attr_max_value = conv.max

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_value = data[self.attr]

    @callback
    def async_restore_last_state(self, state: float, attrs: dict):
        self._attr_value = state

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    # backward compatibility fix
>>>>>>> cf192804062149d4fadc0b02b3c0813d77346c47
    if (MAJOR_VERSION, MINOR_VERSION) >= (2022, 8):
        def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
            super().__init__(gateway, device, conv)
            if hasattr(conv, "min"):
                self._attr_native_min_value = conv.min
            if hasattr(conv, "max"):
                self._attr_native_max_value = conv.max

        async def async_set_native_value(self, value: float) -> None:
            await self.device_send({self.attr: value})

        @callback
        def async_set_state(self, data: dict):
            self._attr_native_value = data[self.attr]

        @callback
        def async_restore_last_state(self, state: float, attrs: dict):
            self._attr_native_value = state

        async def async_update(self):
            await self.device_read(self.subscribed_attrs)

    else: # (MAJOR_VERSION, MINOR_VERSION) < (2022, 8):
        def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
            super().__init__(gateway, device, conv)
            if hasattr(conv, "min"):
                self._attr_min_value = conv.min
            if hasattr(conv, "max"):
                self._attr_max_value = conv.max

        async def async_set_value(self, value: float) -> None:
            await self.device_send({self.attr: value})

        @callback
        def async_set_state(self, data: dict):
            self._attr_value = data[self.attr]

        @callback
        def async_restore_last_state(self, state: float, attrs: dict):
            self._attr_value = state

        async def async_update(self):
            await self.device_read(self.subscribed_attrs)

  
