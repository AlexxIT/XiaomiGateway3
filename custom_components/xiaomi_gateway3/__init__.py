import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_ZIGBEE
from homeassistant.helpers.entity import Entity

from . import utils
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'xiaomi_gateway3'


async def async_setup(hass: HomeAssistant, hass_config: dict):
    hass.data[DOMAIN] = {}

    if DOMAIN in hass_config and 'log' in hass_config[DOMAIN]:
        Gateway3.log = hass.config.path(hass_config[DOMAIN]['log'])

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data[DOMAIN][config_entry.unique_id] = \
        gw = Gateway3(**config_entry.data)

    # init setup for each supported domains
    for domain in ('binary_sensor', 'light', 'remote', 'sensor', 'switch'):
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(
            config_entry, domain))

    gw.start()

    return True


class Gateway3Device(Entity):
    _state = STATE_UNKNOWN

    def __init__(self, gateway: Gateway3, device: dict, attr: str):
        self.gw = gateway
        self.device = device

        self._attr = attr

        self._unique_id = f"{self.device['mac']}_{self._attr}"
        self._name = self.device['device_name'] + ' ' + self._attr.title()

        self.entity_id = '.' + self._unique_id

        gateway.add_update(device['did'], self.update)

    async def async_added_to_hass(self):
        if 'init' in self.device:
            self.update(self.device['init'])

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def device_info(self):
        if self.device['did'] == 'lumi.0':
            return {
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name']
            }
        else:
            return {
                'connections': {(CONNECTION_ZIGBEE, self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                # 'sw_version': None,
                'via_device': (DOMAIN, self.gw.device['mac'])
            }

    def update(self, data: dict):
        pass
