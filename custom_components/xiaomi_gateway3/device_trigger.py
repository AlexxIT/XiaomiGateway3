import re

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_STATE,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.device_registry import DeviceEntry

from .core.const import DOMAIN
from .core.converters.base import BaseConv, ConstConv, MapConv
from .core.converters.const import (
    BUTTON_SINGLE,
    BUTTON_DOUBLE,
    BUTTON_TRIPLE,
    BUTTON_HOLD,
    BUTTON_RELEASE,
)
from .core.converters.mibeacon import BLEMapConv
from .core.devices import DEVICES

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): str,
        vol.Required(CONF_STATE): str,
    }
)

BUTTONS = [BUTTON_SINGLE, BUTTON_DOUBLE, BUTTON_TRIPLE, BUTTON_HOLD, BUTTON_RELEASE]


def get_actions(human_model: str) -> list[str] | None:
    """Gets a list of actions (buttons) using the device human model."""
    if m := re.search(": ([^,]+)", human_model):
        first_model = m[1]
        for desc in DEVICES:
            for v in desc.values():
                if isinstance(v, list) and first_model in v:
                    actions = []

                    converters: list[BaseConv] = desc["spec"]
                    for conv in converters:
                        if conv.attr == "action":
                            if isinstance(conv, ConstConv):
                                actions.append(conv.value)
                            elif isinstance(conv, MapConv):
                                actions += list(conv.map.values())
                            elif isinstance(conv, BLEMapConv):
                                actions += list(conv.map.values())
                        elif conv.attr == "button":
                            actions += BUTTONS
                        elif conv.attr.startswith("button"):
                            actions += [f"{conv.attr}_{i}" for i in BUTTONS]

                    return actions


DEVICE_ACTIONS = {}


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    if device_id not in DEVICE_ACTIONS:
        registry = device_registry.async_get(hass)
        device_entry: DeviceEntry = registry.async_get(device_id)
        DEVICE_ACTIONS[device_id] = get_actions(device_entry.model)

    if not DEVICE_ACTIONS[device_id]:
        return []

    return [
        {
            CONF_PLATFORM: CONF_DEVICE,
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: "action",
        }
    ]


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: dict
) -> dict[str, vol.Schema]:
    device_id = config[CONF_DEVICE_ID]
    if actions := DEVICE_ACTIONS.get(device_id):
        return {"extra_fields": vol.Schema({vol.Required(CONF_STATE): vol.In(actions)})}
    return {}


async def async_attach_trigger(hass: HomeAssistant, config: dict, action, trigger_info):
    device_id = config[CONF_DEVICE_ID]

    registry = entity_registry.async_get(hass)
    for entry in registry.entities.values():
        if entry.device_id == device_id and entry.unique_id.endswith("action"):
            config = state_trigger.TRIGGER_STATE_SCHEMA(
                {
                    CONF_PLATFORM: CONF_STATE,
                    CONF_ENTITY_ID: entry.entity_id,
                    state_trigger.CONF_TO: config[CONF_STATE],
                }
            )
            return await state_trigger.async_attach_trigger(
                hass, config, action, trigger_info, platform_type=CONF_DEVICE
            )

    return None
