import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .core.const import DOMAIN, source_hash
from .core.converters import GATEWAY
from .core.device import logger
from .core.gateway import XGateway


async def async_get_config_entry_diagnostics(
        hass: HomeAssistant, entry: ConfigEntry
):
    options = {
        k: "***" if k in ("host", "token") else v
        for k, v in entry.options.items()
    }

    try:
        ts = time.time()
        devices = {
            device.unique_id: device.as_dict(ts)
            for device in XGateway.devices.values()
        }
    except Exception as e:
        devices = f"{type(e).__name__}: {e}"

    try:
        errors = [
            entry.to_dict()
            for key, entry in hass.data["system_log"].records.items()
            if DOMAIN in key
        ]
    except Exception as e:
        errors = f"{type(e).__name__}: {e}"

    return {
        "version": source_hash(),
        "options": options,
        "errors": errors,
        "devices": devices,
    }


async def async_get_device_diagnostics(
        hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
):
    info = await async_get_config_entry_diagnostics(hass, entry)
    try:
        uid = next(i[1] for i in device.identifiers if i[0] == DOMAIN)
        info["device"] = info.pop("devices")[uid]
        info["device"]["unique_id"] = uid

        if device.model.startswith(GATEWAY):
            gw: XGateway = hass.data[DOMAIN][entry.entry_id]
            info["data.tar.gz.b64"] = await gw.tar_data()
        else:
            device = next(
                d for d in XGateway.devices.values() if d.unique_id == uid
            )
            info["logger"] = logger(device)

    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"

    return info
