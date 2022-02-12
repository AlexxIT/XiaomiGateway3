from homeassistant.components.climate import *
from homeassistant.components.climate.const import *
from homeassistant.core import callback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        else:
            entity = XiaomiClimate(gateway, device, conv)
        async_add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiClimate(XEntity, ClimateEntity):
    _attr_fan_mode = None
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_hvac_mode = None
    _attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT]
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
    _attr_temperature_unit = TEMP_CELSIUS

    @callback
    def async_set_state(self, data: dict):
        self._attr_current_temperature = data.get("current_temp")
        self._attr_fan_mode = data.get("fan_mode")
        self._attr_hvac_mode = data.get("hvac_mode")
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
