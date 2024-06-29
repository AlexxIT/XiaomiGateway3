from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    HVACMode,
    HVACAction,
)
from homeassistant.const import PRECISION_WHOLE, UnitOfTemperature

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "climate"] = async_add_entities


ACTIONS = {
    HVACMode.OFF: HVACAction.OFF,
    HVACMode.COOL: HVACAction.COOLING,
    HVACMode.HEAT: HVACAction.HEATING,
    HVACMode.DRY: HVACAction.DRYING,
    HVACMode.FAN_ONLY: HVACAction.FAN,
}


class XAqaraS2(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_target_temperature = 0
    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    # support only KTWKQ03ES for now
    _attr_max_temp = 30
    _attr_min_temp = 17

    _enabled = None
    _mode = None

    def on_init(self):
        self.listen_attrs |= {"power", "current_temp", "hvac_mode", "target_temp"}

    def set_state(self, data: dict):
        if "power" in data:
            self._enabled = data["power"]
        if "current_temp" in data:
            self._attr_current_temperature = data["current_temp"]
        if "fan_mode" in data:
            self._attr_fan_mode = data["fan_mode"]
        if "hvac_mode" in data:
            self._attr_hvac_mode = data["hvac_mode"]
            self._mode = data["hvac_mode"]
            # better support HomeKit
            # https://github.com/AlexxIT/XiaomiGateway3/issues/707#issuecomment-1099109552
            self._attr_hvac_action = ACTIONS.get(self._attr_hvac_mode)
        if "target_temp" in data:
            # fix scenes with turned off climate
            # https://github.com/AlexxIT/XiaomiGateway3/issues/101#issuecomment-757781988
            self._attr_target_temperature = data["target_temp"]

        self._attr_hvac_mode = self._mode if self._enabled else HVACMode.OFF

    async def async_set_temperature(self, temperature: int, **kwargs) -> None:
        if temperature:
            self.device.write({self.attr: {"target_temp": temperature}})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self.device.write({self.attr: {"fan_mode": fan_mode}})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        self.device.write({self.attr: {"hvac_mode": hvac_mode}})


class XAqaraE1(XEntity, ClimateEntity):
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_temp = 30
    _attr_min_temp = 5
    _attr_target_temperature_step = 0.5

    _enabled = None
    _mode = None

    def on_init(self):
        self.listen_attrs = {"climate", "mode", "current_temp", "target_temp"}

    def set_state(self, data: dict):
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

    async def async_set_temperature(self, temperature: int, **kwargs) -> None:
        self.device.write({"target_temp": temperature})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode in (HVACMode.HEAT, HVACMode.AUTO):
            payload = {"mode": hvac_mode}
        elif hvac_mode == HVACMode.OFF:
            payload = {"climate": False}
        else:
            return
        self.device.write(payload)


class XScdvbHAVC(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_temp = 32
    _attr_min_temp = 16
    _attr_target_temperature_step = 1

    _enabled = None
    _mode = None

    def on_init(self):
        self.listen_attrs |= {"current_temp", "fan_mode", "hvac_mode", "target_temp"}

    def set_state(self, data: dict):
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

        self._attr_hvac_mode = self._mode if self._enabled else HVACMode.OFF

    async def async_set_temperature(self, temperature: int, **kwargs) -> None:
        if temperature:
            self.device.write({"target_temp": temperature})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if not self._enabled:
            self.device.write({"climate": True})
            self._attr_hvac_mode = self._mode
        self.device.write({"fan_mode": fan_mode})

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode == HVACMode.OFF:
            self.device.write({"climate": False})
        else:
            if not self._enabled:
                self.device.write({"climate": True})
            # better support HomeKit
            if hvac_mode == HVACMode.AUTO:
                hvac_mode = self._mode
            self.device.write({"hvac_mode": hvac_mode})


XEntity.NEW["climate.model.lumi.airrtc.tcpecn02"] = XAqaraS2
XEntity.NEW["climate.model.lumi.airrtc.agl001"] = XAqaraE1
XEntity.NEW["climate.model.14050"] = XScdvbHAVC
