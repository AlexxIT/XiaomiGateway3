import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .core import logger
from .core.const import DOMAIN
from .core.device import XDevice
from .core.gate.base import EVENT_MQTT_CONNECT
from .core.gateway import MultiGateway
from .hass import hass_utils
from .hass.add_entitites import handle_add_entities
from .hass.entity import XEntity

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "climate",
    "cover",
    "light",
    "number",
    "select",
    "sensor",
    "switch",
    "text",
]

CONF_DEVICES = "devices"
CONF_ATTRIBUTES_TEMPLATE = "attributes_template"
CONF_OPENMIIO = "openmiio"
CONF_LOGGER = "logger"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                CONF_LOGGER: logger.CONFIG_SCHEMA,
                vol.Optional(CONF_ATTRIBUTES_TEMPLATE): cv.template,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    if config := config.get(DOMAIN):
        if devices_config := config.get(CONF_DEVICES):
            XDevice.configs = hass_utils.fix_yaml_devices_config(devices_config)

        if logger_config := config.get(CONF_LOGGER):
            logger.init(__name__, logger_config, hass.config.config_dir)

        if template := config.get(CONF_ATTRIBUTES_TEMPLATE):
            template.hass = hass
            XEntity.attributes_template = template

    hass.data[DOMAIN] = {}

    await hass_utils.store_devices(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    if config_entry.data:
        return await hass_utils.setup_cloud(hass, config_entry)

    await hass_utils.store_gateway_key(hass, config_entry)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    gw = MultiGateway(**config_entry.options)
    handle_add_entities(hass, config_entry, gw)
    gw.start()

    hass.data[DOMAIN][config_entry.entry_id] = gw

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    async def hass_stop(event):
        await gw.stop()

    config_entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hass_stop)
    )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    if config_entry.data:
        return True  # skip unload for cloud config entry

    # remove all stats entities if disable stats
    hass_utils.remove_stats_entities(hass, config_entry)

    # important to remove entities before stop gateway
    ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    gw: MultiGateway = hass.data[DOMAIN][config_entry.entry_id]
    await gw.stop()
    gw.remove_all_devices()

    return ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if config_entry.version == 1:
        hass_utils.migrate_legacy_devices_unique_id(hass)
        hass_utils.migrate_legacy_entitites_unique_id(hass)
        hass_utils.migrate_devices_store()

        try:
            # fix support Hass 2023.12 and earlier - no version arg
            hass.config_entries.async_update_entry(config_entry, version=4)
        except TypeError:
            pass
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Supported from Hass v2022.3"""
    device_registry.async_get(hass).async_remove_device(device_entry.id)
    return True
