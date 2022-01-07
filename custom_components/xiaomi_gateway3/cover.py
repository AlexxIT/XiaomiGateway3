from homeassistant.components.cover import CoverEntity, ATTR_POSITION
from homeassistant.const import STATE_CLOSING, STATE_OPENING
from homeassistant.core import callback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        async_add_entities([XiaomiCover(gateway, device, conv)])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiCover(XEntity, CoverEntity):
    _attr_is_closed = None

    @callback
    def async_set_state(self, data: dict):
        if 'run_state' in data:
            self._attr_state = data["run_state"]
            self._attr_is_opening = self._attr_state == STATE_OPENING
            self._attr_is_closing = self._attr_state == STATE_CLOSING
        if 'position' in data:
            self._attr_current_cover_position = data['position']
            self._attr_is_closed = self._attr_current_cover_position == 0

    async def async_open_cover(self, **kwargs):
        await self.device_send({self.attr: "open"})

    async def async_close_cover(self, **kwargs):
        await self.device_send({self.attr: "close"})

    async def async_stop_cover(self, **kwargs):
        await self.device_send({self.attr: "stop"})

    async def async_set_cover_position(self, **kwargs):
        await self.device_send({"position": kwargs[ATTR_POSITION]})
