import logging
import time

from homeassistant.components.automation import ATTR_LAST_TRIGGERED
from homeassistant.components.binary_sensor import BinarySensorEntity, \
    DEVICE_CLASS_DOOR, DEVICE_CLASS_MOISTURE
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import now

from . import DOMAIN
from .core.gateway3 import Gateway3
from .core.helpers import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS = {
    'contact': DEVICE_CLASS_DOOR,
    'water_leak': DEVICE_CLASS_MOISTURE,
}

CONF_INVERT_STATE = 'invert_state'
CONF_OCCUPANCY_TIMEOUT = 'occupancy_timeout'


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if attr == 'motion':
            async_add_entities([XiaomiMotionSensor(gateway, device, attr)])
        elif attr == 'power':
            async_add_entities([XiaomiKettleSensor(gateway, device, attr)])
        else:
            async_add_entities([XiaomiBinarySensor(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('binary_sensor', setup)


class XiaomiBinarySensor(XiaomiEntity, BinarySensorEntity):
    @property
    def is_on(self):
        return self._state

    @property
    def device_class(self):
        return DEVICE_CLASS.get(self.attr, self.attr)

    def update(self, data: dict = None):
        if self.attr in data:
            custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
            if not custom.get(CONF_INVERT_STATE):
                # gas and smoke => 1 and 2
                self._state = bool(data[self.attr])
            else:
                self._state = not data[self.attr]

        self.schedule_update_ha_state()


KETTLE = {
    0: 'idle',
    1: 'heat',
    2: 'cool_down',
    3: 'warm_up',
}


class XiaomiKettleSensor(XiaomiBinarySensor):
    def update(self, data: dict = None):
        if self.attr in data:
            value = data[self.attr]
            self._state = bool(value)
            self._attrs['action_id'] = value
            self._attrs['action'] = KETTLE[value]

        self.schedule_update_ha_state()


class XiaomiMotionSensor(XiaomiBinarySensor):
    _default_delay = None
    _last_on = 0
    _last_off = 0
    _timeout_pos = 0
    _unsub_set_no_motion = None

    async def async_added_to_hass(self):
        # old version
        self._default_delay = self.device.get(CONF_OCCUPANCY_TIMEOUT, 90)

        custom: dict = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        custom.setdefault(CONF_OCCUPANCY_TIMEOUT, self._default_delay)

        await super().async_added_to_hass()

    async def _start_no_motion_timer(self, delay: float):
        if self._unsub_set_no_motion:
            self._unsub_set_no_motion()

        self._unsub_set_no_motion = async_call_later(
            self.hass, abs(delay), self._set_no_motion)

    async def _set_no_motion(self, *args):
        self.debug("Clear motion")

        self._last_off = time.time()
        self._timeout_pos = 0
        self._unsub_set_no_motion = None
        self._state = False
        self.schedule_update_ha_state()

    def update(self, data: dict = None):
        # fix 1.4.7_0115 heartbeat error (has motion in heartbeat)
        if 'battery' in data:
            return

        # https://github.com/AlexxIT/XiaomiGateway3/issues/135
        if 'illuminance' in data and ('lumi.sensor_motion.aq2' in
                                      self.device['device_model']):
            data[self.attr] = 1

        # check only motion=1
        if data.get(self.attr) != 1:
            # handle available change
            self.schedule_update_ha_state()
            return

        # don't trigger motion right after illumination
        t = time.time()
        if t - self._last_on < 1:
            return

        self._state = True
        self._attrs[ATTR_LAST_TRIGGERED] = now().isoformat(timespec='seconds')
        self._last_on = t

        # handle available change
        self.schedule_update_ha_state()

        if self._unsub_set_no_motion:
            self._unsub_set_no_motion()

        custom = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        # if customize of any entity will be changed from GUI - default value
        # for all motion sensors will be erased
        timeout = custom.get(CONF_OCCUPANCY_TIMEOUT, self._default_delay)
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

            self.hass.add_job(self._start_no_motion_timer, delay)

        # repeat event from Aqara integration
        self.hass.bus.fire('xiaomi_aqara.motion', {
            'entity_id': self.entity_id
        })
