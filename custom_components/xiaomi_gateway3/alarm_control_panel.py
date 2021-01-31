import logging

from homeassistant.components.alarm_control_panel import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    AlarmControlPanelEntity,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
)

from . import Gateway3Device
from .core.gateway3 import Gateway3
from .core.utils import DOMAIN

_LOGGER = logging.getLogger(__name__)

ALARM_STATES = [STATE_ALARM_DISARMED, STATE_ALARM_ARMED_HOME,
                STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_NIGHT]


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Alarm(gateway, device, attr)], True)

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('alarm_control_panel', setup)


async def async_unload_entry(hass, entry):
    return True


class Gateway3Alarm(Gateway3Device, AlarmControlPanelEntity):
    @property
    def miio_did(self):
        return self.device['init']['alarm_did']

    @property
    def should_poll(self):
        return True

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return "mdi:shield-home"

    @property
    def supported_features(self):
        return (SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY |
                SUPPORT_ALARM_ARM_NIGHT)

    @property
    def code_arm_required(self):
        return False

    async def async_added_to_hass(self):
        pass

    async def async_will_remove_from_hass(self) -> None:
        pass

    def alarm_disarm(self, code=None):
        self.gw.miio.send('set_properties', [{
            'did': self.miio_did, 'siid': 3, 'piid': 1, 'value': 0
        }])

    def alarm_arm_home(self, code=None):
        self.gw.miio.send('set_properties', [{
            'did': self.miio_did, 'siid': 3, 'piid': 1, 'value': 1
        }])

    def alarm_arm_away(self, code=None):
        self.gw.miio.send('set_properties', [{
            'did': self.miio_did, 'siid': 3, 'piid': 1, 'value': 2
        }])

    def alarm_arm_night(self, code=None):
        self.gw.miio.send('set_properties', [{
            'did': self.miio_did, 'siid': 3, 'piid': 1, 'value': 3
        }])

    def update(self, *args):
        try:
            resp = self.gw.miio.send('get_properties', [{
                'did': self.miio_did, 'siid': 3, 'piid': 1
            }])
            state = resp[0]['value']
            self._state = ALARM_STATES[state]
        except:
            pass
