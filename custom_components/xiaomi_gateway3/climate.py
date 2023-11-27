from homeassistant.components.climate import *
from homeassistant.components.climate.const import *
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity, setup_entity
from .core.gateway import XGateway

ACTIONS = {
    HVAC_MODE_OFF: CURRENT_HVAC_OFF,
    HVAC_MODE_COOL: CURRENT_HVAC_COOL,
    HVAC_MODE_HEAT: CURRENT_HVAC_HEAT,
    HVAC_MODE_DRY: CURRENT_HVAC_DRY,
    HVAC_MODE_FAN_ONLY: CURRENT_HVAC_FAN,
}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    def new_entity(gateway: XGateway, device: XDevice, conv: Converter) -> XEntity:
        if conv.mi == "14.2.85":
            return XiaomiClimateS2(gateway, device, conv)
        if conv.mi == "4.21.85":
            return AqaraE1(gateway, device, conv)
        else:
            return XiaomiClimate(gateway, device, conv)

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup_entity(hass, config_entry, add_entities, new_entity))


class XiaomiClimate(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_AUTO, HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_max_temp = 32
    _attr_min_temp = 16
    _attr_target_temperature_step = 1

    _enabled = None
    _mode = None
    @callback
    def async_set_state(self, data: dict):
        if "climate" in data:
            self._enabled = data["climate"]
        if "hvac_mode" in data:
            self._mode = data["hvac_mode"]
        if "fan_mode" in data:
            self._attr_fan_mode = data["fan_mode"]
        if "current_temp" in data:
            self._attr_current_temperature = data["current_temp"]
        if "target_temp" in data:
            self._attr_target_temperature = data["target_temp"]

        if self._enabled is None or self._mode is None:
            return

        self._attr_hvac_mode = self._mode if self._enabled else HVAC_MODE_OFF
    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    async def async_set_temperature(self, **kwargs) -> None:
        if kwargs[ATTR_TEMPERATURE] == 0:
            return
        await self.device_send({"target_temp": kwargs[ATTR_TEMPERATURE]})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if not self._enabled:
            await self.device_send({"climate": True})
            self._attr_hvac_mode = self._mode
        await self.device_send({"fan_mode": fan_mode})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode == HVAC_MODE_OFF:
            await self.device_send({"climate": False})
        else:
            if not self._enabled:
                await self.device_send({"climate": True})
            # better support HomeKit
            if hvac_mode == HVAC_MODE_AUTO:
                hvac_mode = self._mode
            await self.device_send({"hvac_mode": hvac_mode})

# noinspection PyAbstractClass
class XiaomiClimateS2(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
    _attr_temperature_unit = TEMP_CELSIUS
    # support only KTWKQ03ES for now
    _attr_max_temp = 30
    _attr_min_temp = 17
    _attr_target_temperature_step = 1

    @callback
    def async_set_state(self, data: dict):
        self._attr_current_temperature = data.get("current_temp")
        self._attr_fan_mode = data.get("fan_mode")
        self._attr_hvac_mode = data.get("hvac_mode")
        # better support HomeKit
        # https://github.com/AlexxIT/XiaomiGateway3/issues/707#issuecomment-1099109552
        self._attr_hvac_action = ACTIONS.get(self._attr_hvac_mode)
        # fix scenes with turned off climate
        # https://github.com/AlexxIT/XiaomiGateway3/issues/101#issuecomment-757781988
        self._attr_target_temperature = data.get("target_temp", 0)

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    async def async_set_temperature(self, **kwargs) -> None:
        if kwargs[ATTR_TEMPERATURE] == 0:
            return
        payload = {"target_temp": kwargs[ATTR_TEMPERATURE]}
        await self.device_send({self.attr: payload})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        payload = {"fan_mode": fan_mode}
        await self.device_send({self.attr: payload})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        payload = {"hvac_mode": hvac_mode}
        await self.device_send({self.attr: payload})


# noinspection PyAbstractClass
class AqaraE1(XEntity, ClimateEntity):
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_AUTO]
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_max_temp = 30
    _attr_min_temp = 5
    _attr_target_temperature_step = 0.5

    _enabled = None
    _mode = None

    @callback
    def async_set_state(self, data: dict):
        if "climate" in data:
            self._enabled = data["climate"]
        if "mode" in data:
            self._mode = data["mode"]
        if "current_temp" in data:
            self._attr_current_temperature = data["current_temp"]
        if "target_temp" in data:
            self._attr_target_temperature = data["target_temp"]

        if self._enabled is None or self._mode is None:
            return

        self._attr_hvac_mode = self._mode if self._enabled else HVAC_MODE_OFF

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    async def async_set_temperature(self, **kwargs) -> None:
        await self.device_send({"target_temp": kwargs[ATTR_TEMPERATURE]})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode in (HVAC_MODE_HEAT, HVAC_MODE_AUTO):
            payload = {"mode": hvac_mode}
        elif hvac_mode == HVAC_MODE_OFF:
            payload = {"climate": False}
        else:
            return
        await self.device_send(payload)
