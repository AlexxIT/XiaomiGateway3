from homeassistant.components.climate import *
from homeassistant.components.climate.const import *

from . import DOMAIN, Gateway3Device
from .core.gateway3 import Gateway3

HVAC_MODES = [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

AC_STATE_HVAC = {
    HVAC_MODE_OFF: 0x01,
    HVAC_MODE_HEAT: 0x10,
    HVAC_MODE_COOL: 0x11
}
AC_STATE_FAN = {
    FAN_LOW: 0x00,
    FAN_MEDIUM: 0x10,
    FAN_HIGH: 0x20,
    FAN_AUTO: 0x30
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([
            Gateway3Climate(gateway, device, attr)
        ])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('climate', setup)


class Gateway3Climate(Gateway3Device, ClimateEntity):
    _current_hvac = None
    _current_temp = None
    _fan_mode = None
    _hvac_mode = None
    _is_on = None
    _state: Optional[bytearray] = None
    _target_temp = None

    @property
    def precision(self) -> float:
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        return self._hvac_mode if self._is_on else HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT]

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def fan_modes(self):
        return FAN_MODES

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    def update(self, data: dict = None):
        if 'power' in data:  # 0 - off, 1 - on
            self._is_on = data['power']
        if 'mode' in data:  # 0 - heat, 1 - cool
            self._hvac_mode = HVAC_MODES[data['mode']]
        if 'fan_mode' in data:  # 0 - low, 3 - auto
            self._fan_mode = FAN_MODES[data['fan_mode']]
        if 'current_temperature' in data:
            self._current_temp = data['current_temperature']
        if 'target_temperature' in data:
            self._target_temp = data['target_temperature']
        if self._attr in data:
            self._state = bytearray(data[self._attr].to_bytes(4, 'big'))
        self.async_write_ha_state()

    def set_temperature(self, **kwargs) -> None:
        if not self._state:
            return
        self._state[2] = int(kwargs[ATTR_TEMPERATURE])
        state = int.from_bytes(self._state, 'big')
        self.gw.send(self.device, {self._attr: state})

    def set_fan_mode(self, fan_mode: str) -> None:
        if not self._state:
            return
        self._state[1] = AC_STATE_FAN[fan_mode]
        state = int.from_bytes(self._state, 'big')
        self.gw.send(self.device, {self._attr: state})

    def set_hvac_mode(self, hvac_mode: str) -> None:
        if not self._state:
            return
        self._state[0] = AC_STATE_HVAC[hvac_mode]
        state = int.from_bytes(self._state, 'big')
        self.gw.send(self.device, {self._attr: state})
