import logging
import time
from datetime import timedelta

from homeassistant.const import *
from homeassistant.util.dt import now

from . import DOMAIN, Gateway3Device
from .binary_sensor import DT_FORMAT
from .core.gateway3 import Gateway3

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
}

ICONS = {
    'conductivity': 'mdi:flower',
    'consumption': 'mdi:flash',
    'gas density': 'mdi:google-circles-communities',
    'moisture': 'mdi:water-percent',
    'smoke density': 'mdi:google-circles-communities',
}

INFO = ['ieee', 'nwk', 'msg_received', 'msg_missed', 'unresponsive',
        'link_quality', 'rssi', 'last_seen']


async def async_setup_entry(hass, entry, add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if attr == 'action':
            add_entities([Gateway3Action(gateway, device, attr)])
        elif attr in INFO:
            add_entities([Gateway3Info(gateway, device, attr)])
        else:
            add_entities([Gateway3Sensor(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][entry.entry_id]
    gw.add_setup('sensor', setup)


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


CLUSTERS = {
    0x0000: 'Basic',
    0x0001: 'PowerCfg',
    0x0003: 'Identify',
    0x0006: 'OnOff',
    0x0008: 'LevelCtrl',
    0x000A: 'Time',
    0x000C: 'AnalogInput',  # cube, gas
    0x0012: 'Multistate',
    0x0019: 'OTA',  # illuminance sensor
    0x0101: 'DoorLock',
    0x0400: 'Illuminance',
    0x0402: 'Temperature',
    0x0403: 'Pressure',
    0x0405: 'Humidity',
    0x0406: 'Occupancy',
    0x0500: 'IasZone',
    0x0B04: 'ElectrMeasur',
    0xFCC0: 'Xiaomi'
}


class Gateway3Info(Gateway3Device):
    last_seq = None

    def __init__(self, gateway: Gateway3, device: dict, attr: str):
        self.gw = gateway
        self.device = device

        self._attr = attr

        ieee = '0x' + device['did'][5:].rjust(16, '0').upper()
        self._attrs = {
            'ieee': ieee,
            'nwk': None,
            'msg_received': 0,
            'msg_missed': 0,
            'unresponsive': 0
        }

        self._unique_id = None
        self._name = device['device_name']
        self.entity_id = f"{DOMAIN}.{device['mac']}"

    @property
    def state(self):
        return self._state

    async def async_added_to_hass(self):
        self.gw.add_info(self._attrs['ieee'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        self.gw.remove_info(self._attrs['ieee'], self.update)

    def update(self, data: dict = None):
        if 'sourceAddress' in data:
            self._attrs['nwk'] = data['sourceAddress']
            self._attrs['link_quality'] = data['linkQuality']
            self._attrs['rssi'] = data['rssi']
            self._attrs['last_seen'] = now().strftime(DT_FORMAT)

            cid = int(data['clusterId'], 0)
            self._attrs['last_msg'] = CLUSTERS.get(cid, cid)

            self._attrs['msg_received'] += 1

            new_seq = int(data['APSCounter'], 0)
            if self.last_seq is not None:
                miss = new_seq - self.last_seq - 1
                if miss < 0:  # 0xFF => 0x00
                    miss += 256
                if miss:
                    self._attrs['msg_missed'] += miss
            self.last_seq = new_seq

            self._state = self._attrs[self._attr]

        elif 'parent' in data:
            ago = timedelta(seconds=data.pop('ago'))
            data['last_seen'] = (now() - ago).strftime(DT_FORMAT)
            self._attrs.update(data)

        elif data.get('deviceState') == 17:
            self._attrs['unresponsive'] += 1

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
                data[self._attr] = BUTTON[v]
                break
            elif k.startswith('button_both'):
                data[self._attr] = k + '_' + BUTTON_BOTH[v]
                break
            elif k.startswith('button'):
                data[self._attr] = k + '_' + BUTTON[v]
                break
            elif k == 'vibration' and v != 2:  # skip tilt and wait tilt_angle
                data[self._attr] = VIBRATION[v]
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
