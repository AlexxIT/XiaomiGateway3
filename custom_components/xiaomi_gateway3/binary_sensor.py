import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS = {
    'contact': 'door'
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3BinarySensor(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.unique_id]
    gw.add_setup('binary_sensor', setup)


class Gateway3BinarySensor(Gateway3Device, BinarySensorEntity):
    @property
    def is_on(self):
        return self._state is True

    @property
    def device_class(self):
        return DEVICE_CLASS.get(self._attr, self._attr)

    def update(self, data: dict = None):
        if self._attr not in data:
            return
        self._state = data[self._attr] == 1
        self.schedule_update_ha_state()
