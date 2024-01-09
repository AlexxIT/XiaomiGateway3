import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import (
    CONF_TYPE,
    CONF_DEVICE_ID,
    CONF_PLATFORM,
    CONF_STATE,
    CONF_ENTITY_ID,
    CONF_DEVICE,
    CONF_DOMAIN,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import DOMAIN
from .core import converters
from .core.converters.base import BUTTON

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): cv.string, vol.Required("action"): cv.string}
)


async def async_attach_trigger(hass, config, action, automation_info):
    entity_registry = er.async_get(hass)

    device_id = config[CONF_DEVICE_ID]
    entry = next(
        (
            entry
            for entry in entity_registry.entities.values()
            if entry.device_id == device_id and entry.unique_id.endswith("action")
        ),
        None,
    )

    if not entry:
        return None

    to_state = (
        config["action"]
        if config[CONF_TYPE] == "button"
        else f"{config[CONF_TYPE]}_{config['action']}"
    )

    state_config = {
        CONF_PLATFORM: CONF_STATE,
        CONF_ENTITY_ID: entry.entity_id,
        state_trigger.CONF_TO: to_state,
    }

    state_config = state_trigger.TRIGGER_STATE_SCHEMA(state_config)
    return await state_trigger.async_attach_trigger(
        hass, state_config, action, automation_info, platform_type="device"
    )


async def async_get_triggers(hass, device_id):
    device_registry = dr.async_get(hass)
    device: dr.DeviceEntry = device_registry.async_get(device_id)
    buttons = converters.get_buttons(device.model)
    if not buttons:
        return None

    return [
        {
            CONF_PLATFORM: CONF_DEVICE,
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: button,
        }
        for button in buttons
    ]


# noinspection PyUnusedLocal
async def async_get_trigger_capabilities(hass, config):
    return {
        "extra_fields": vol.Schema(
            {
                vol.Required("action"): vol.In(BUTTON.values()),
            }
        )
    }
