from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .core.const import DOMAIN, source_hash
from .core.gate.base import XGateway


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    try:
        devices = {device.uid: device.as_dict() for device in XGateway.devices.values()}
    except Exception as e:
        devices = repr(e)

    info = get_info(hass, config_entry)
    info["devices"] = devices
    return info


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
):
    try:
        uid = next(i[1] for i in device_entry.identifiers if i[0] == DOMAIN)
        device = next(i for i in XGateway.devices.values() if i.uid == uid)
        device = device.as_dict()
    except Exception as e:
        device = repr(e)

    info = get_info(hass, config_entry)
    info["device"] = device
    return info


def get_info(hass: HomeAssistant, config_entry: ConfigEntry) -> dict:
    try:
        errors = [
            entry.to_dict()
            for key, entry in hass.data["system_log"].records.items()
            if DOMAIN in str(key)
        ]
    except Exception as e:
        errors = repr(e)

    return {
        "version": source_hash(),
        "options": config_entry.options.copy(),
        "errors": errors,
    }
