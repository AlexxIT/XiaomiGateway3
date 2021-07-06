import logging

from homeassistant.components.alarm_control_panel import \
    SUPPORT_ALARM_ARM_AWAY, SUPPORT_ALARM_ARM_HOME, SUPPORT_ALARM_ARM_NIGHT, \
    SUPPORT_ALARM_TRIGGER, AlarmControlPanelEntity
from homeassistant.const import STATE_ALARM_ARMED_AWAY, \
    STATE_ALARM_ARMED_HOME, STATE_ALARM_ARMED_NIGHT, STATE_ALARM_DISARMED, \
    STATE_ALARM_TRIGGERED

from . import DOMAIN
from .core.gateway3 import Gateway3
from .core.helpers import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

ALARM_STATES = [STATE_ALARM_DISARMED, STATE_ALARM_ARMED_HOME,
                STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_NIGHT]


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([XiaomiAlarm(gateway, device, attr)], True)

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('alarm_control_panel', setup)


class XiaomiAlarm(XiaomiEntity, AlarmControlPanelEntity):
    @property
    def miio_did(self):
        return self.device['did']

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return "mdi:shield-home"

    @property
    def supported_features(self):
        return (SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY |
                SUPPORT_ALARM_ARM_NIGHT | SUPPORT_ALARM_TRIGGER)

    @property
    def code_arm_required(self):
        return False

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

    def alarm_trigger(self, code=None):
        self.gw.miio.send('set_properties', [{
            'did': self.miio_did, 'siid': 3, 'piid': 22, 'value': 1
        }])

    def update(self, data: dict = None):
        if data:
            if self.attr in data:
                state = data[self.attr]
                self._state = ALARM_STATES[state]
            elif data.get('alarm_trigger'):
                self._state = STATE_ALARM_TRIGGERED

        else:
            try:
                resp = self.gw.miio.send('get_properties', [{
                    'did': self.miio_did, 'siid': 3, 'piid': 22
                }])
                if resp[0]['value'] == 1:
                    self._state = STATE_ALARM_TRIGGERED
                else:
                    resp = self.gw.miio.send('get_properties', [{
                        'did': self.miio_did, 'siid': 3, 'piid': 1
                    }])
                    state = resp[0]['value']
                    self._state = ALARM_STATES[state]
            except:
                pass

        self.schedule_update_ha_state()
