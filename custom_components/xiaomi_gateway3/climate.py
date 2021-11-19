from homeassistant.components.climate import *
from homeassistant.components.climate.const import *
from homeassistant.core import callback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice, XEntity
from .core.gateway import XGateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        async_add_entities([XiaomiClimate(gateway, device, conv)])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiClimate(XEntity, ClimateEntity):
    _state: dict = None

    @property
    def precision(self) -> float:
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        return self._state.get("hvac_mode") if self._state else None

    @property
    def current_temperature(self):
        return self._state.get("current_temp") if self._state else None

    @property
    def target_temperature(self):
        # fix scenes with turned off climate
        # https://github.com/AlexxIT/XiaomiGateway3/issues/101#issuecomment-757781988
        return self._state.get("target_temp") if self._state else 0

    @property
    def fan_mode(self):
        return self._state.get("fan_mode")

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT]

    @property
    def fan_modes(self):
        return [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    @callback
    def async_set_state(self, data: dict):
        self._state = data

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
