import logging
import time

from homeassistant.components.binary_sensor import BinarySensorEntity, \
    DEVICE_CLASS_DOOR, DEVICE_CLASS_MOISTURE
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later

from . import DOMAIN, Gateway3Device
from .core.gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS = {
    'contact': DEVICE_CLASS_DOOR,
    'water_leak': DEVICE_CLASS_MOISTURE,
}

CONF_INVERT_STATE = 'invert_state'
CONF_OCCUPANCY_TIMEOUT = 'occupancy_timeout'


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([
            Gateway3MotionSensor(gateway, device, attr)
            if attr == 'motion' else
            Gateway3BinarySensor(gateway, device, attr)
        ])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('binary_sensor', setup)


class Gateway3BinarySensor(Gateway3Device, BinarySensorEntity):
    @property
    def state(self):
        return self._state

    @property
    def is_on(self):
        # don't know if is_on important for binary sensror
        return self._state == STATE_ON

    @property
    def device_class(self):
        return DEVICE_CLASS.get(self._attr, self._attr)

    def update(self, data: dict = None):
        if self._attr in data:
            custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
            if not custom.get(CONF_INVERT_STATE):
                # gas and smoke => 1 and 2
                self._state = STATE_ON if data[self._attr] else STATE_OFF
            else:
                self._state = STATE_OFF if data[self._attr] else STATE_ON

        self.async_write_ha_state()


class Gateway3MotionSensor(Gateway3BinarySensor):
    _last_off = 0
    _state = STATE_OFF
    _timeout_pos = 0
    _unsub_set_no_motion = None

    async def async_added_to_hass(self):
        # old version
        delay = self.device.get(CONF_OCCUPANCY_TIMEOUT, 90)

        custom: dict = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        custom.setdefault(CONF_OCCUPANCY_TIMEOUT, delay)

        await super().async_added_to_hass()

    @callback
    def _set_no_motion(self, *args):
        self.debug("Clear motion")

        self._last_off = time.time()
        self._timeout_pos = 0
        self._unsub_set_no_motion = None
        self._state = STATE_OFF
        self.async_write_ha_state()

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = STATE_ON if data[self._attr] else STATE_OFF

        # handle available change
        self.async_write_ha_state()

        # continue only if motion=1 arrived
        if not data.get(self._attr):
            return

        if self._unsub_set_no_motion:
            self._unsub_set_no_motion()

        custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        timeout = custom.get(CONF_OCCUPANCY_TIMEOUT)
        if timeout:
            if isinstance(timeout, list):
                pos = min(self._timeout_pos, len(timeout) - 1)
                delay = timeout[pos]
                self._timeout_pos += 1
            else:
                delay = timeout

            if delay < 0 and time.time() + delay < self._last_off:
                delay *= 2

            self.debug(f"Extend delay: {delay} seconds")

            self._unsub_set_no_motion = async_call_later(
                self.hass, abs(delay), self._set_no_motion)

        # repeat event from Aqara integration
        self.hass.bus.async_fire('xiaomi_aqara.motion', {
            'entity_id': self.entity_id
        })
