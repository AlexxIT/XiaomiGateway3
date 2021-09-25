from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.util.dt import now

from .binary_sensor import XiaomiMotionBase
from .core import utils
from .core.gateway3 import Gateway3
from .core.utils import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([XiaomiTracker(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('device_tracker', setup)


DEFAULT_TS = now()


class XiaomiTracker(XiaomiMotionBase, TrackerEntity):
    _state_off = STATE_NOT_HOME

    best_mac = None
    best_rssi = -999
    best_ts = DEFAULT_TS

    @property
    def location_name(self):
        return self._state

    @property
    def source_type(self):
        # with GPS source type location name can be custom area name
        return SOURCE_TYPE_GPS

    @property
    def latitude(self):
        return None

    @property
    def longitude(self):
        return None

    def update(self, data: dict = None):
        if self.attr in data:
            mac = data[self.attr]
            ts = now()
            if (
                    (ts - self.best_ts).total_seconds() > 30 or
                    data['rssi'] > self.best_rssi or
                    mac == self.best_mac
            ):
                self.best_rssi = self._attrs['rssi'] = data['rssi']
                self.best_ts = ts
                if mac != self.best_mac:
                    self.best_mac = self._attrs['source'] = mac
                self._state = utils.get_area(self.hass, mac) or STATE_HOME

                self._trigger_motion()

        self.schedule_update_ha_state()
