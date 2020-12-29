import logging
import time
from datetime import timedelta

from homeassistant.const import *
from homeassistant.util.dt import now

from . import DOMAIN, Gateway3Device
from .core.gateway3 import Gateway3
from .core.utils import CLUSTERS

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
    'smoke density': '% obs/ft',
    'moisture': '%',
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
    'ble': 'mdi:bluetooth'
}

INFO = ['ieee', 'nwk', 'msg_received', 'msg_missed', 'unresponsive',
        'link_quality', 'rssi', 'last_seen']


async def async_setup_entry(hass, entry, add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if attr == 'action':
            add_entities([Gateway3Action(gateway, device, attr)])
        elif attr == 'gateway':
            add_entities([GatewayStats(gateway, device, attr)])
        elif attr == 'zigbee':
            add_entities([ZigbeeStats(gateway, device, attr)])
        elif attr == 'ble':
            add_entities([BLEStats(gateway, device, attr)])
        else:
            add_entities([Gateway3Sensor(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][entry.entry_id]
    gw.add_setup('sensor', setup)


async def async_unload_entry(hass, entry):
    return True


class Gateway3Sensor(Gateway3Device):
    @property
    def state(self):
        return self._state

    @property
    def device_class(self):
        return self._attr

    @property
    def unit_of_measurement(self):
        return UNITS.get(self._attr)

    @property
    def icon(self):
        return ICONS.get(self._attr)

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = data[self._attr]
        self.async_write_ha_state()


class GatewayStats(Gateway3Sensor):
    @property
    def device_class(self):
        # don't use const to support older Hass version
        return 'timestamp'

    @property
    def available(self):
        return True

    async def async_added_to_hass(self):
        self.gw.add_stats('lumi.0', self.update)
        # update available when added to Hass
        self.update()

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats('lumi.0', self.update)

    def update(self, data: dict = None):
        # empty data - update state to available time
        if not data:
            self._state = now().isoformat(timespec='seconds') \
                if self.gw.available else None
        else:
            self._attrs.update(data)

        self.async_write_ha_state()


class ZigbeeStats(Gateway3Sensor):
    last_seq = None

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

        self.gw.add_stats(self._attrs['ieee'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats(self._attrs['ieee'], self.update)

    def update(self, data: dict = None):
        if 'sourceAddress' in data:
            self._attrs['nwk'] = data['sourceAddress']
            self._attrs['link_quality'] = data['linkQuality']
            self._attrs['rssi'] = data['rssi']

            cid = int(data['clusterId'], 0)
            self._attrs['last_msg'] = cluster = CLUSTERS.get(cid, cid)

            self._attrs['msg_received'] += 1

            new_seq = int(data['APSCounter'], 0)
            if self.last_seq is not None:
                miss = new_seq - self.last_seq - 1
                if miss < 0:  # 0xFF => 0x00
                    miss += 256
                self._attrs['msg_missed'] += miss
                self._attrs['last_missed'] = miss
                if miss:
                    self.debug(f"Msg missed: {self.last_seq} => {new_seq} "
                               f"({cluster})")
            self.last_seq = new_seq

            self._state = now().isoformat(timespec='seconds')

        elif 'parent' in data:
            ago = timedelta(seconds=data.pop('ago'))
            self._state = (now() - ago).isoformat(timespec='seconds')
            self._attrs.update(data)

        elif data.get('deviceState') == 17:
            self._attrs['unresponsive'] += 1

        self.async_write_ha_state()


class BLEStats(Gateway3Sensor):
    last_seq = None

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

        self.gw.add_stats(self.device['did'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_stats(self.device['did'], self.update)

    def update(self, data: dict = None):
        self._attrs['msg_received'] += 1
        self._state = now().isoformat(timespec='seconds')
        self.async_write_ha_state()


# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L4738
BUTTON = {
    1: 'single',
    2: 'double',
    3: 'triple',
    4: 'quadruple',
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


class Gateway3Action(Gateway3Device):
    _state = ''

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return 'mdi:bell'

    def update(self, data: dict = None):
        for k, v in data.items():
            if k == 'button':
                # fix 1.4.7_0115 heartbeat error (has button in heartbeat)
                if 'voltage' in data:
                    return
                data[self._attr] = BUTTON.get(v, 'unknown')
                break
            elif k.startswith('button_both'):
                data[self._attr] = k + '_' + BUTTON_BOTH.get(v, 'unknown')
                break
            elif k.startswith('button'):
                data[self._attr] = k + '_' + BUTTON.get(v, 'unknown')
                break
            elif k == 'vibration' and v != 2:  # skip tilt and wait tilt_angle
                data[self._attr] = VIBRATION.get(v, 'unknown')
                break
            elif k == 'tilt_angle':
                data = {'vibration': 2, 'angle': v, self._attr: 'tilt'}
                break

        if self._attr in data:
            # TODO: fix me
            self._attrs = data
            self._state = data[self._attr]
            self.async_write_ha_state()

            # repeat event from Aqara integration
            self.hass.bus.async_fire('xiaomi_aqara.click', {
                'entity_id': self.entity_id, 'click_type': self._state
            })

            time.sleep(.1)

            self._state = ''

        self.async_write_ha_state()
