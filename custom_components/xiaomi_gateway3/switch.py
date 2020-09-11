import logging

from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Switch(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.unique_id]
    gw.add_setup('switch', setup)


class Gateway3Switch(Gateway3Device, ToggleEntity):
    @property
    def is_on(self) -> bool:
        return self._state

    def update(self, data: dict = None):
        if self._attr not in data:
            return
        self._state = data[self._attr] == 1
        self.schedule_update_ha_state()

    def turn_on(self):
        self.gw.send(self.device, {self._attr: 1})

    def turn_off(self):
        self.gw.send(self.device, {self._attr: 0})
