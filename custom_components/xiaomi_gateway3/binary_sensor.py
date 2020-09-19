import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, \
    DEVICE_CLASS_DOOR, DEVICE_CLASS_MOISTURE
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS = {
    'contact': DEVICE_CLASS_DOOR,
    'water_leak': DEVICE_CLASS_MOISTURE,
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([
            Gateway3MotionSensor(gateway, device, attr)
            if attr == 'motion' else
            Gateway3BinarySensor(gateway, device, attr)
        ])

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


class Gateway3MotionSensor(Gateway3BinarySensor):
    _occupancy_timeout = None
    _unsub_set_no_motion = None

    async def async_added_to_hass(self):
        self._occupancy_timeout = self.device.get('occupancy_timeout', 90)

        await super().async_added_to_hass()

    @callback
    def _set_no_motion(self, *args):
        self._unsub_set_no_motion = None
        self._state = False
        self.async_write_ha_state()

    def update(self, data: dict = None):
        if self._attr not in data:
            return
        # gas and smoke => 1 and 2
        self._state = data[self._attr] >= 1
        self.schedule_update_ha_state()

        if self._state:
            if self._unsub_set_no_motion:
                self._unsub_set_no_motion()

            _unsub_set_no_motion = async_call_later(
                self.hass, self._occupancy_timeout, self._set_no_motion)
