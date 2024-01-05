from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity, setup_entity
from .core.gateway import XGateway

ACTIONS = {
    HVACMode.OFF: HVACAction.OFF,
    HVACMode.COOL: HVACAction.COOLING,
    HVACMode.HEAT: HVACAction.HEATING,
}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    def new_entity(gateway: XGateway, device: XDevice, conv: Converter) -> XEntity:
        if conv.mi == "4.21.85":
            return AqaraE1(gateway, device, conv)
        else:
            return XiaomiClimate(gateway, device, conv)

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup_entity(hass, config_entry, add_entities, new_entity))


# noinspection PyAbstractClass
class XiaomiClimate(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE_RANGE | ClimateEntityFeature.FAN_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
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
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
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

        self._attr_hvac_mode = self._mode if self._enabled else HVACMode.OFF

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)

    async def async_set_temperature(self, **kwargs) -> None:
        await self.device_send({"target_temp": kwargs[ATTR_TEMPERATURE]})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode in (HVACMode.HEAT, HVACMode.AUTO):
            payload = {"mode": hvac_mode}
        elif hvac_mode == HVACMode.OFF:
            payload = {"climate": False}
        else:
            return
        await self.device_send(payload)
