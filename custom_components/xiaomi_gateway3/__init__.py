import asyncio
import json
import logging
import time

import voluptuous as vol
from homeassistant.components.system_log import CONF_LOGGER
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.storage import Store

from .core import backward, logger, utils
from .core.const import DOMAIN
from .core.entity import XEntity
from .core.gateway import XGateway
from .core.utils import XiaomiGateway3Debug
from .core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__name__)

DOMAINS = [
    'alarm_control_panel', 'binary_sensor', 'climate', 'cover', 'light',
    'number', 'select', 'sensor', 'switch'
]

CONF_DEVICES = 'devices'
CONF_ATTRIBUTES_TEMPLATE = 'attributes_template'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_DEVICES): {
            cv.string: vol.Schema({
                vol.Optional('occupancy_timeout'): cv.positive_int,
            }, extra=vol.ALLOW_EXTRA),
        },
        CONF_LOGGER: logger.CONFIG_SCHEMA,
        vol.Optional(CONF_ATTRIBUTES_TEMPLATE): cv.template
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    if not backward.hass_version_supported:
        _LOGGER.error("Support Hass version 2021.7 and more")
        return False

    config = hass_config.get(DOMAIN) or {}

    if CONF_LOGGER in config:
        logger.init(__name__, config[CONF_LOGGER], hass.config.config_dir)

        info = await hass.helpers.system_info.async_get_system_info()
        _LOGGER.debug(f"SysInfo: {info}")

        # update global debug_mode for all gateways
        if 'debug_mode' in config[CONF_LOGGER]:
            setattr(XGateway, 'debug_mode', config[CONF_LOGGER]['debug_mode'])

    if CONF_ATTRIBUTES_TEMPLATE in config:
        XEntity.attributes_template = config[CONF_ATTRIBUTES_TEMPLATE]
        XEntity.attributes_template.hass = hass

    hass.data[DOMAIN] = {}

    await utils.load_devices(hass, config.get(CONF_DEVICES))

    _register_send_command(hass)

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

    # add options handler
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    hass.data[DOMAIN][entry.entry_id] = XGateway(**entry.options)

    hass.async_create_task(_setup_domains(hass, entry))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # check unload cloud integration
    if entry.entry_id not in hass.data[DOMAIN]:
        return

    # TODO: delete entities if they have been removed from options
    # remove all stats entities if disable stats
    # if not entry.options.get('stats'):
    #     suffix = ('_gateway', '_zigbee', '_ble')
    #     registry: EntityRegistry = hass.data['entity_registry']
    #     remove = [
    #         entity.entity_id
    #         for entity in list(registry.entities.values())
    #         if (entity.config_entry_id == entry.entry_id and
    #             entity.unique_id.endswith(suffix))
    #     ]
    #     for entity_id in remove:
    #         registry.async_remove(entity_id)

    gw: XGateway = hass.data[DOMAIN][entry.entry_id]
    await gw.stop()

    await asyncio.gather(*[
        hass.config_entries.async_forward_entry_unload(entry, domain)
        for domain in DOMAINS
    ])

    return True


# noinspection PyUnusedLocal
async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    return True


async def _setup_domains(hass: HomeAssistant, entry: ConfigEntry):
    # init setup for each supported domains
    await asyncio.gather(*[
        hass.config_entries.async_forward_entry_setup(entry, domain)
        for domain in DOMAINS
    ])

    gw: XGateway = hass.data[DOMAIN][entry.entry_id]
    gw.start()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, gw.stop)
    )


async def _setup_micloud_entry(hass: HomeAssistant, config_entry):
    data: dict = config_entry.data.copy()

    session = async_create_clientsession(hass)
    hass.data[DOMAIN]['cloud'] = cloud = MiCloud(session, data['servers'])

    if 'service_token' in data:
        # load devices with saved MiCloud auth
        cloud.auth = data
        devices = await cloud.get_devices()
    else:
        devices = None

    if devices is None:
        _LOGGER.debug(f"Login to MiCloud for {config_entry.title}")
        if await cloud.login(data['username'], data['password']):
            # update MiCloud auth in .storage
            data.update(cloud.auth)
            hass.config_entries.async_update_entry(config_entry, data=data)

            devices = await cloud.get_devices()
            if devices is None:
                _LOGGER.error("Can't load devices from MiCloud")

        else:
            _LOGGER.error("Can't login to MiCloud")

    # load devices from or save to .storage
    store = Store(hass, 1, f"{DOMAIN}/{data['username']}.json")
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

    for device in devices:
        # key - mac for BLE, and did for others
        did = device['did'] if device['pid'] not in '6' else \
            device['mac'].replace(':', '').lower()
        XGateway.defaults.setdefault(did, {})
        # don't override name if exists
        XGateway.defaults[did].setdefault('name', device['name'])

    return True


# async def _handle_device_remove(hass: HomeAssistant):
#     """Remove device from Hass and Mi Home if the device is renamed to
#     `delete`.
#     """
#
#     async def device_registry_updated(event: Event):
#         if event.data['action'] != 'update':
#             return
#
#         registry = hass.data['device_registry']
#         hass_device = registry.async_get(event.data['device_id'])
#
#         # check empty identifiers
#         if not hass_device or not hass_device.identifiers:
#             return
#
#         # handle only our devices
#         for hass_did in hass_device.identifiers:
#             if hass_did[0] == DOMAIN and hass_device.name_by_user == 'delete':
#                 break
#         else:
#             return
#
#         # remove from Mi Home
#         # if multiple gateways - will try remove from all of them
#         for gw in hass.data[DOMAIN].values():
#             if isinstance(gw, XGateway):
#                 await gw.remove_device(hass_did[1])
#
#         # remove from Hass
#         registry.async_remove_device(hass_device.id)
#
#     hass.bus.async_listen('device_registry_updated', device_registry_updated)


async def _setup_logger(hass: HomeAssistant):
    if not hasattr(_LOGGER, 'defaul_level'):
        # default level from Hass config
        _LOGGER.defaul_level = _LOGGER.level

    entries = hass.config_entries.async_entries(DOMAIN)
    web_logs = any(e.options.get('debug') for e in entries)

    # only if global logging don't set
    if _LOGGER.defaul_level == logging.NOTSET:
        # disable log to console
        _LOGGER.propagate = web_logs is False
        # set debug if any of integrations has debug
        _LOGGER.setLevel(logging.DEBUG if web_logs else logging.NOTSET)

    # if don't set handler yet
    if web_logs:
        # skip if already added
        if any(isinstance(h, XiaomiGateway3Debug) for h in _LOGGER.handlers):
            return

        handler = XiaomiGateway3Debug(hass)
        _LOGGER.addHandler(handler)

        if _LOGGER.defaul_level == logging.NOTSET:
            info = await hass.helpers.system_info.async_get_system_info()
            _LOGGER.debug(f"SysInfo: {info}")


def _register_send_command(hass: HomeAssistant):
    async def send_command(call: ServiceCall):
        host = call.data["host"]
        gw = next(
            gw for gw in hass.data[DOMAIN].values()
            if isinstance(gw, XGateway) and gw.host == host
        )
        cmd = call.data["command"].split(" ")
        if cmd[0] == "miio":
            raw = json.loads(call.data["data"])
            resp = await gw.miio.send(raw['method'], raw.get('params'))
            hass.components.persistent_notification.async_create(
                str(resp), utils.TITLE
            )
        elif cmd[0] == "set_state":  # for debug purposes
            device = gw.devices.get(cmd[1])
            raw = json.loads(call.data["data"])
            device.available = True
            device.decode_ts = time.time()
            device.update(raw)

    hass.services.async_register(DOMAIN, "send_command", send_command)
