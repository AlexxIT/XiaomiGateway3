import logging

import voluptuous as vol
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers import config_validation as cv
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

    await _handle_device_remove(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry):
    config = hass.data[DOMAIN]['config']

    hass.data[DOMAIN][config_entry.entry_id] = \
        gw = Gateway3(**config_entry.data, config=config)

    # init setup for each supported domains
    for domain in (
            'binary_sensor', 'cover', 'light', 'remote', 'sensor', 'switch'
    ):
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(
            config_entry, domain))

    gw.start()

    return True


# async def async_unload_entry(hass: HomeAssistant, config_entry):
#     return True


async def _handle_device_remove(hass: HomeAssistant):
    """Remove device from Hass and Mi Home if the device is renamed to
    `delete`.
    """

    async def device_registry_updated(event: Event):
        if event.data['action'] != 'update':
            return

        registry = hass.data['device_registry']
        hass_device = registry.async_get(event.data['device_id'])

        # check empty identifiers
        if not hass_device.identifiers:
            return

        domain, mac = next(iter(hass_device.identifiers))
        # handle only our devices
        if domain != DOMAIN or hass_device.name_by_user != 'delete':
            return

        # remove from Mi Home
        for gw in hass.data[DOMAIN].values():
            if not isinstance(gw, Gateway3):
                continue
            gw_device = gw.get_device(mac)
            if not gw_device:
                continue
            gw.miio.send('remove_device', [gw_device['did']])
            break

        # remove from Hass
        registry.async_remove_device(hass_device.id)

    hass.bus.async_listen('device_registry_updated', device_registry_updated)


class Gateway3Device(Entity):
    _state = STATE_UNKNOWN

    def __init__(self, gateway: Gateway3, device: dict, attr: str):
        self.gw = gateway
        self.device = device

        self._attr = attr
        self._attrs = {}

        self._unique_id = f"{self.device['mac']}_{self._attr}"
        self._name = self.device['device_name'] + ' ' + self._attr.title()

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

    async def async_added_to_hass(self):
        if 'init' in self.device:
            self.update(self.device['init'])

        self.gw.add_update(self.device['did'], self.update)

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
    def available(self) -> bool:
        return self.device.get('online', True)

    @property
    def device_info(self):
        """
        https://developers.home-assistant.io/docs/device_registry_index/
        """
        type_ = self.device['type']
        if type_ == 'gateway':
            return {
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name']
            }
        elif type_ == 'zigbee':
            return {
                'connections': {(type_, self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'sw_version': self.device['zb_ver'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }
        elif type_ == 'ble':
            return {
                'connections': {(type_, self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device.get('device_manufacturer'),
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }

    def update(self, data: dict):
        pass
