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
class BackToTheNumberEntity(NumberEntity):
    if (MAJOR_VERSION, MINOR_VERSION) < (2022, 7):
        _attr_value: float = None

        async def async_set_value(self, value: float) -> None:
            await self.async_set_native_value(value)

        @property
        def _attr_native_value(self):
            return self._attr_value

        @_attr_native_value.setter
        def _attr_native_value(self, value):
            self._attr_value = value

        @property
        def _attr_native_min_value(self):
            return self._attr_min_value

        @_attr_native_min_value.setter
        def _attr_native_min_value(self, value):
            self._attr_min_value = value

        @property
        def _attr_native_max_value(self):
            return self._attr_max_value

        @_attr_native_max_value.setter
        def _attr_native_max_value(self, value):
            self._attr_max_value = value


# noinspection PyAbstractClass
class XiaomiNumber(XEntity, BackToTheNumberEntity):
    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        if self.attr in UNITS:
            self._attr_native_unit_of_measurement = UNITS[self.attr]

        if hasattr(conv, "min"):
            self._attr_native_min_value = conv.min
        if hasattr(conv, "max"):
            self._attr_native_max_value = conv.max

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_native_value = data[self.attr]

    @callback
    def async_restore_last_state(self, state: float, attrs: dict):
        self._attr_native_value = state

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    async def async_set_native_value(self, value: float) -> None:
        await self.device_send({self.attr: value})
