import logging

import voluptuous as vol
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.storage import Store
from homeassistant.util import sanitize_filename

from .core import utils
from .core.gateway3 import Gateway3
from .core.utils import DOMAIN
from .core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__name__)

DOMAINS = ['binary_sensor', 'climate', 'cover', 'light', 'remote', 'sensor',
           'switch']

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

    if 'disabled' in config:
        # for dev purposes
        return False

    hass.data[DOMAIN] = {
        'config': config,
        'debug': _LOGGER.level > 0  # default debug from Hass config
    }

    config.setdefault('devices', {})

    await _handle_device_remove(hass)

    # utils.migrate_unique_id(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Support two kind of enties - MiCloud and Gateway."""

    # entry for MiCloud login
    if 'servers' in entry.data:
        return await _setup_micloud_entry(hass, entry)

    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data={},
                                               options=entry.data)

    await _setup_logger(hass)

    config = hass.data[DOMAIN]['config']

    hass.data[DOMAIN][entry.entry_id] = \
        gw = Gateway3(**entry.options, config=config)

    # add options handler
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    # init setup for each supported domains
    for domain in DOMAINS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(
            entry, domain))

    gw.start()

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # remove all stats entities if disable stats
    if not entry.options.get('stats'):
        suffix = ('_gateway', '_zigbee')
        registry: EntityRegistry = hass.data['entity_registry']
        remove = [
            entity.entity_id
            for entity in list(registry.entities.values())
            if entity.config_entry_id == entry.entry_id and
               entity.unique_id.endswith(suffix)
        ]
        for entity_id in remove:
            registry.async_remove(entity_id)

    gw = hass.data[DOMAIN][entry.entry_id]
    gw.stop()

    return all([
        await hass.config_entries.async_forward_entry_unload(entry, domain)
        for domain in DOMAINS
    ])


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


async def _setup_logger(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    any_debug = any(e.options.get('debug') for e in entries)

    # only if global logging don't set
    if not hass.data[DOMAIN]['debug']:
        # disable log to console
        _LOGGER.propagate = not any_debug
        # set debug if any of integrations has debug
        _LOGGER.setLevel(logging.DEBUG if any_debug else logging.NOTSET)

    # if don't set handler yet
    if any_debug and not _LOGGER.handlers:
        handler = utils.XiaomiGateway3Debug(hass)
        _LOGGER.addHandler(handler)

        info = await hass.helpers.system_info.async_get_system_info()
        info.pop('timezone')
        _LOGGER.debug(f"SysInfo: {info}")


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
    def device_state_attributes(self):
        return self._attrs

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
