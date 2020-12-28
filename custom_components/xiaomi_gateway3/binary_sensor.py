import logging
import time

from homeassistant.components.automation import ATTR_LAST_TRIGGERED
from homeassistant.components.binary_sensor import BinarySensorEntity, \
    DEVICE_CLASS_DOOR, DEVICE_CLASS_MOISTURE
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import now

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
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        return DEVICE_CLASS.get(self._attr, self._attr)

    def update(self, data: dict = None):
        if self._attr in data:
            custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
            if not custom.get(CONF_INVERT_STATE):
                # gas and smoke => 1 and 2
                self._state = bool(data[self._attr])
            else:
                self._state = not data[self._attr]

        self.async_write_ha_state()


class Gateway3MotionSensor(Gateway3BinarySensor):
    _last_on = 0
    _last_off = 0
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
        self._state = False
        self.async_write_ha_state()

    def update(self, data: dict = None):
        # fix 1.4.7_0115 heartbeat error (has motion in heartbeat)
        if 'voltage' in data:
            return

        # https://github.com/AlexxIT/XiaomiGateway3/issues/135
        if 'illumination' in data and len(data) == 1:
            data[self._attr] = 1

        if self._attr not in data:
            # handle available change
            self.async_write_ha_state()
            return

        # check only motion=1
        assert data[self._attr] == 1, data

        # don't trigger motion right after illumination
        t = time.time()
        if t - self._last_on < 1:
            return

        self._state = True
        self._attrs[ATTR_LAST_TRIGGERED] = now().isoformat(timespec='seconds')
        self._last_on = t

        # handle available change
        self.async_write_ha_state()

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

            if delay < 0 and t + delay < self._last_off:
                delay *= 2

            self.debug(f"Extend delay: {delay} seconds")

            self._unsub_set_no_motion = async_call_later(
                self.hass, abs(delay), self._set_no_motion)

        # repeat event from Aqara integration
        self.hass.bus.async_fire('xiaomi_aqara.motion', {
            'entity_id': self.entity_id
        })
