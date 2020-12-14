import logging
import time

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


class Gateway3Info(Gateway3Device):
    counter = None

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
        self._attrs['nwk'] = data['sourceAddress']
        self._attrs['link_quality'] = data['linkQuality']
        self._attrs['rssi'] = data['rssi']
        self._attrs['last_seen'] = now().strftime(DT_FORMAT)

        self._attrs['msg_received'] += 1

        cnt = int(data['APSCounter'], 0)
        if self.counter is not None and cnt - self.counter not in (1, 255):
            self._attrs['msg_missed'] += 1
        self.counter = cnt

        self._state = self._attrs[self._attr]

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
