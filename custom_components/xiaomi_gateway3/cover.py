import logging

from homeassistant.components.cover import CoverEntity, ATTR_POSITION, \
    ATTR_CURRENT_POSITION
from homeassistant.const import STATE_CLOSING, STATE_OPENING

from . import DOMAIN
from .core.gateway3 import Gateway3
from .core.helpers import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

RUN_STATES = {0: STATE_CLOSING, 1: STATE_OPENING}


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if device.get('lumi_spec'):
            async_add_entities([XiaomiCover(gateway, device, attr)])
        else:
            async_add_entities([XiaomiCoverMIOT(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('cover', setup)


class XiaomiCover(XiaomiEntity, CoverEntity):
    @property
    def current_cover_position(self):
        return self._attrs.get(ATTR_CURRENT_POSITION)

    @property
    def is_opening(self):
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        return self._state == STATE_CLOSING

    @property
    def is_closed(self):
        return self.current_cover_position == 0

    def update(self, data: dict = None):
        if 'run_state' in data:
            self._state = RUN_STATES.get(data['run_state'])

        if 'position' in data:
            self._attrs[ATTR_CURRENT_POSITION] = data['position']

        self.schedule_update_ha_state()

    def open_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 1})

    def close_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 0})

    def stop_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 2})

    def set_cover_position(self, **kwargs):
        position = kwargs.get(ATTR_POSITION)
        self.gw.send(self.device, {'position': position})


class XiaomiCoverMIOT(XiaomiCover):
    def open_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 2})

    def close_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 1})

    def stop_cover(self, **kwargs):
        self.gw.send(self.device, {'motor': 0})

    def set_cover_position(self, **kwargs):
        position = kwargs.get(ATTR_POSITION)
        self.gw.send(self.device, {'target_position': position})
