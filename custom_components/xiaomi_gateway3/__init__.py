import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import CONNECTION_ZIGBEE
from homeassistant.helpers.entity import Entity

from . import utils
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'xiaomi_gateway3'

CONF_DEVICES = 'devices'
CONF_DEBUG = 'debug'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_DEVICES): {
            cv.string: vol.Schema({
                vol.Optional('occupancy_timeout'): cv.positive_int,
            }, extra=vol.ALLOW_EXTRA),
        },
        vol.Optional(CONF_DEBUG): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    config = hass_config.get(DOMAIN) or {}
    if 'debug' in config:
        debug = utils.XiaomiGateway3Debug(hass)
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.addHandler(debug)

    hass.data[DOMAIN] = {'config': config}

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    config = hass.data[DOMAIN]['config']

    hass.data[DOMAIN][config_entry.unique_id] = \
        gw = Gateway3(**config_entry.data, config=config)

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

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

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
        did: str = self.device['did']
        if did == 'lumi.0':
            return {
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name']
            }
        elif not did.startswith('blt'):
            return {
                'connections': {(CONNECTION_ZIGBEE, self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'sw_version': self.device['zb_ver'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }
        else:
            return {
                'connections': {('bluetooth', self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'name': self.device['device_name'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }

    def update(self, data: dict):
        pass
