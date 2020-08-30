import logging

from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Entity(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.unique_id]
    gw.add_setup('remote', setup)


class Gateway3Entity(Gateway3Device, ToggleEntity):
    _state = False

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def icon(self):
        return 'mdi:zigbee'

    def update(self, data: dict = None):
        if 'pairing_start' in data:
            self._state = True
            self.schedule_update_ha_state()
        elif 'pairing_stop' in data:
            self._state = False
            self.schedule_update_ha_state()

    def turn_on(self):
        self.gw.send(self.device, 'pairing_start', 60)

    def turn_off(self):
        self.gw.send(self.device, 'pairing_stop', 0)
