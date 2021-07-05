import logging
import time
from datetime import timedelta

from homeassistant.const import *
from homeassistant.util.dt import now

from . import DOMAIN
from .core import zigbee, utils
from .core.gateway3 import Gateway3
from .core.helpers import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

UNITS = {
    DEVICE_CLASS_BATTERY: '%',
    DEVICE_CLASS_HUMIDITY: '%',
    DEVICE_CLASS_ILLUMINANCE: 'lx',  # zb light and motion and ble flower - lux
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_PRESSURE: 'hPa',
    DEVICE_CLASS_TEMPERATURE: TEMP_CELSIUS,
    'conductivity': "µS/cm",
    'consumption': ENERGY_WATT_HOUR,
    'gas density': '% LEL',
    'supply': '%',
    'smoke density': '% obs/ft',
    'moisture': '%',
    'tvoc': CONCENTRATION_PARTS_PER_BILLION,
    # 'link_quality': 'lqi',
    # 'rssi': 'dBm',
    # 'msg_received': 'msg',
    # 'msg_missed': 'msg',
    # 'unresponsive': 'times'
}

ICONS = {
    'conductivity': 'mdi:flower',
    'consumption': 'mdi:flash',
    'gas density': 'mdi:google-circles-communities',
    'moisture': 'mdi:water-percent',
    'smoke density': 'mdi:google-circles-communities',
    'gateway': 'mdi:router-wireless',
    'zigbee': 'mdi:zigbee',
    'ble': 'mdi:bluetooth',
    'tvoc': 'mdi:cloud',
}

INFO = ['ieee', 'nwk', 'msg_received', 'msg_missed', 'unresponsive',
        'link_quality', 'rssi', 'last_seen']


async def async_setup_entry(hass, entry, add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if attr == 'action':
            add_entities([XiaomiAction(gateway, device, attr)])
        elif attr == 'gateway':
            add_entities([GatewayStats(gateway, device, attr)])
        elif attr == 'zigbee':
            add_entities([ZigbeeStats(gateway, device, attr)])
        elif attr == 'ble':
            add_entities([BLEStats(gateway, device, attr)])
        else:
            add_entities([XiaomiSensor(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][entry.entry_id]
    gw.add_setup('sensor', setup)


class XiaomiSensor(XiaomiEntity):
    @property
    def state(self):
        return self._state

    @property
    def device_class(self):
        return self.attr

    @property
    def unit_of_measurement(self):
        return UNITS.get(self.attr)

    @property
    def icon(self):
        return ICONS.get(self.attr)

    def update(self, data: dict = None):
        if self.attr in data:
            self._state = data[self.attr]
        self.schedule_update_ha_state()


class GatewayStats(XiaomiSensor):
    @property
    def device_class(self):
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        return True

    async def async_added_to_hass(self):
        self.gw.set_stats(self.device['did'], self)
        # update available when added to Hass
        self.update()

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats(self.device['did'], self)

    def update(self, data: dict = None):
        # empty data - update state to available time
        if not data:
            self._state = now().isoformat(timespec='seconds') \
                if self.gw.available else None
        else:
            self._attrs.update(data)

        self.schedule_update_ha_state()


class ZigbeeStats(XiaomiSensor):
    last_seq1 = None
    last_seq2 = None

    @property
    def device_class(self):
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        return True

    async def async_added_to_hass(self):
        if not self._attrs:
            ieee = '0x' + self.device['did'][5:].rjust(16, '0').upper()
            self._attrs = {
                'ieee': ieee,
                'nwk': None,
                'msg_received': 0,
                'msg_missed': 0,
                'unresponsive': 0,
                'last_missed': 0,
            }
            self.render_attributes_template()

        self.gw.set_stats(self._attrs['ieee'], self)

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats(self._attrs['ieee'], self)

    def update(self, data: dict = None):
        if 'sourceAddress' in data:
            self._attrs['nwk'] = data['sourceAddress']
            self._attrs['link_quality'] = data['linkQuality']
            self._attrs['rssi'] = data['rssi']

            cid = int(data['clusterId'], 0)
            self._attrs['last_msg'] = cluster = zigbee.CLUSTERS.get(cid, cid)

            self._attrs['msg_received'] += 1

            # For some devices better works APSCounter, for other - sequence
            # number in payload. Sometimes broken messages arrived.
            try:
                new_seq1 = int(data['APSCounter'], 0)
                raw = data['APSPlayload']
                manufact_spec = int(raw[2:4], 16) & 4
                new_seq2 = int(raw[8:10] if manufact_spec else raw[4:6], 16)
                if self.last_seq1 is not None:
                    miss = min(
                        (new_seq1 - self.last_seq1 - 1) & 0xFF,
                        (new_seq2 - self.last_seq2 - 1) & 0xFF
                    )
                    self._attrs['msg_missed'] += miss
                    self._attrs['last_missed'] = miss
                    if miss:
                        self.debug(
                            f"Msg missed: {self.last_seq1} => {new_seq1}, "
                            f"{self.last_seq2} => {new_seq2}, {cluster}"
                        )
                self.last_seq1 = new_seq1
                self.last_seq2 = new_seq2

            except:
                pass

            self._state = now().isoformat(timespec='seconds')

        elif 'parent' in data:
            ago = timedelta(seconds=data.pop('ago'))
            self._state = (now() - ago).isoformat(timespec='seconds')
            self._attrs.update(data)

        elif data.get('deviceState') == 17:
            self._attrs['unresponsive'] += 1

        self.schedule_update_ha_state()


class BLEStats(XiaomiSensor):
    @property
    def device_class(self):
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        return True

    async def async_added_to_hass(self):
        if not self._attrs:
            self._attrs = {
                'mac': self.device['mac'],
                'msg_received': 0,
            }
            self.render_attributes_template()

        self.gw.set_stats(self.device['mac'], self)

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats(self.device['mac'], self)

    def update(self, data: dict = None):
        self._attrs['msg_received'] += 1
        self._state = now().isoformat(timespec='seconds')
        self.schedule_update_ha_state()


# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L4738
BUTTON = {
    1: 'single',
    2: 'double',
    3: 'triple',
    4: 'quadruple',
    5: 'quintuple',  # only Yeelight Dimmer
    16: 'hold',
    17: 'release',
    18: 'shake',
    128: 'many',
}

BUTTON_BOTH = {
    4: 'single',
    5: 'double',
    6: 'triple',
    16: 'hold',
    17: 'release',
}

VIBRATION = {
    1: 'vibration',
    2: 'tilt',
    3: 'drop',
}


class XiaomiAction(XiaomiEntity):
    _state = ''
    _action_attrs = None

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return 'mdi:bell'

    @property
    def device_state_attributes(self):
        return self._action_attrs or self._attrs

    def update(self, data: dict = None):
        for k, v in data.items():
            if k == 'button':
                # fix 1.4.7_0115 heartbeat error (has button in heartbeat)
                if 'battery' in data:
                    return
                data[self.attr] = BUTTON.get(v, 'unknown')
                break
            elif k.startswith('button_both'):
                data[self.attr] = k + '_' + BUTTON_BOTH.get(v, 'unknown')
                break
            elif k.startswith('button'):
                data[self.attr] = k + '_' + BUTTON.get(v, 'unknown')
                break
            elif k == 'vibration' and v != 2:  # skip tilt and wait tilt_angle
                data[self.attr] = VIBRATION.get(v, 'unknown')
                break
            elif k == 'tilt_angle':
                data = {'vibration': 2, 'angle': v, self.attr: 'tilt'}
                break

        if self.attr in data:
            self._action_attrs = {**self._attrs, **data}
            self._state = data[self.attr]
            self.schedule_update_ha_state()

            # repeat event from Aqara integration
            self.hass.bus.fire('xiaomi_aqara.click', {
                'entity_id': self.entity_id, 'click_type': self._state
            })

            time.sleep(.3)

            self._state = ''

        self.schedule_update_ha_state()
