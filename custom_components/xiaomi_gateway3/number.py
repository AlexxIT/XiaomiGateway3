from homeassistant.components.number import NumberEntity
from homeassistant.components.number.const import DEFAULT_STEP
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity, setup_entity
from .core.gateway import XGateway


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    def new_entity(gateway: XGateway, device: XDevice, conv: Converter) -> XEntity:
        return XiaomiNumber(gateway, device, conv)

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup_entity(hass, config_entry, add_entities, new_entity))


UNITS = {
    "approach_distance": UnitOfLength.METERS,
    "occupancy_timeout": UnitOfTime.SECONDS,
}


# noinspection PyAbstractClass
class XiaomiNumber(XEntity, NumberEntity):
    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        if self.attr in UNITS:
            self._attr_native_unit_of_measurement = UNITS[self.attr]

        multiply = getattr(conv, "multiply", 0) or 1

        if hasattr(conv, "min"):
            self._attr_native_min_value = conv.min * multiply
        if hasattr(conv, "max"):
            self._attr_native_max_value = conv.max * multiply
        if hasattr(conv, "step") or hasattr(conv, "multiply"):
            self._attr_native_step = getattr(conv, "step", DEFAULT_STEP) * multiply

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
