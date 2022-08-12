from homeassistant.components.number import NumberEntity
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
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


# noinspection PyAbstractClass
class XiaomiNumber(XEntity, NumberEntity):
    _attr_value: float = None

    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

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
    if (MAJOR_VERSION, MINOR_VERSION) >= (2022, 8):
        async def async_set_native_value(self, value: float) -> None:
            await self.device_send({self.attr: value})
    else:
        async def async_set_value(self, value: float) -> None:
            await self.device_send({self.attr: value})
