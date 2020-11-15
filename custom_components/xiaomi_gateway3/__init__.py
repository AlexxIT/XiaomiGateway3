import logging

import voluptuous as vol
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store
from homeassistant.util import sanitize_filename

from .core import utils
from .core.gateway3 import Gateway3
from .core.utils import DOMAIN
from .core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__name__)

CONF_DEVICES = 'devices'
CONF_DEBUG = 'debug'
CONF_BUZZER = 'buzzer'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_DEVICES): {
            cv.string: vol.Schema({
                vol.Optional('occupancy_timeout'): cv.positive_int,
            }, extra=vol.ALLOW_EXTRA),
        },
        vol.Optional(CONF_BUZZER): cv.boolean,
        vol.Optional(CONF_DEBUG): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    config = hass_config.get(DOMAIN) or {}

    config.setdefault('devices', {})

    if 'debug' in config:
        debug = utils.XiaomiGateway3Debug(hass)
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.addHandler(debug)

    hass.data[DOMAIN] = {'config': config}

    await _handle_device_remove(hass)

    # utils.migrate_unique_id(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry):
    """Support two kind of enties - MiCloud and Gateway."""

    # entry for MiCloud login
    if 'servers' in config_entry.data:
        return await _setup_micloud_entry(hass, config_entry)

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

async def _setup_micloud_entry(hass: HomeAssistant, config_entry):
    data: dict = config_entry.data.copy()

    session = async_create_clientsession(hass)
    cloud = MiCloud(session)

    if 'service_token' in data:
        # load devices with saved MiCloud auth
        cloud.auth = data
        devices = await cloud.get_total_devices(data['servers'])
    else:
        devices = None

    if devices is None:
        _LOGGER.debug(f"Login to MiCloud for {config_entry.title}")
        if await cloud.login(data['username'], data['password']):
            # update MiCloud auth in .storage
            data.update(cloud.auth)
            hass.config_entries.async_update_entry(config_entry, data=data)

            devices = await cloud.get_total_devices(data['servers'])
            if devices is None:
                _LOGGER.error("Can't load devices from MiCloud")

        else:
            _LOGGER.error("Can't login to MiCloud")

    # load devices from or save to .storage
    filename = sanitize_filename(data['username'])
    store = Store(hass, 1, f"{DOMAIN}/{filename}.json")
    if devices is None:
        _LOGGER.debug("Loading a list of devices from the .storage")
        devices = await store.async_load()
    else:
        _LOGGER.debug(f"Loaded from MiCloud {len(devices)} devices")
        await store.async_save(devices)

    if devices is None:
        _LOGGER.debug("No devices in .storage")
        return False

    # TODO: Think about a bunch of devices
    if 'devices' not in hass.data[DOMAIN]:
        hass.data[DOMAIN]['devices'] = devices
    else:
        hass.data[DOMAIN]['devices'] += devices

    default_devices = hass.data[DOMAIN]['config']['devices']
    for device in devices:
        default_devices[device['did']] = {'device_name': device['name']}

    return True


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
        if not hass_device or not hass_device.identifiers:
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
            _LOGGER.debug(f"{gw.host} | Remove device: {gw_device['did']}")
            gw.miio.send('remove_device', [gw_device['did']])
            break

        # remove from Hass
        registry.async_remove_device(hass_device.id)

    hass.bus.async_listen('device_registry_updated', device_registry_updated)


class Gateway3Device(Entity):
    _ignore_offline = None
    _state = None

    def __init__(self, gateway: Gateway3, device: dict, attr: str):
        self.gw = gateway
        self.device = device

        self._attr = attr
        self._attrs = {}

        self._unique_id = f"{self.device['mac']}_{self._attr}"
        self._name = (self.device['device_name'] + ' ' +
                      self._attr.replace('_', ' ').title())

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

    def debug(self, message: str):
        _LOGGER.debug(f"{self.entity_id} | {message}")

    async def async_added_to_hass(self):
        """Also run when rename entity_id"""
        custom: dict = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        self._ignore_offline = custom.get('ignore_offline')

        if 'init' in self.device and self._state is None:
            self.update(self.device['init'])

        self.gw.add_update(self.device['did'], self.update)

    async def async_will_remove_from_hass(self) -> None:
        """Also run when rename entity_id"""
        self.gw.remove_update(self.device['did'], self.update)

    # @property
    # def entity_registry_enabled_default(self):
    #     return False

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
        return self.device.get('online', True) or self._ignore_offline

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
        else:  # ble and mesh
            return {
                'connections': {('bluetooth', self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device.get('device_manufacturer'),
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }

    def update(self, data: dict):
        pass
