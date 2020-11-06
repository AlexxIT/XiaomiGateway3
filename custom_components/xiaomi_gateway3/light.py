import logging
import time

from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS, SUPPORT_COLOR_TEMP, ATTR_COLOR_TEMP
from homeassistant.util import color

from . import DOMAIN, Gateway3Device
from .core import bluetooth
from .core.gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if device['type'] == 'zigbee':
            async_add_entities([Gateway3Light(gateway, device, attr)])
        else:
            async_add_entities([Gateway3MeshLight(gateway, device, attr)],
                               True)

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('light', setup)


class Gateway3Light(Gateway3Device, LightEntity):
    _brightness = None
    _color_temp = None

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def color_temp(self):
        return self._color_temp

    @property
    def supported_features(self):
        """Flag supported features."""
        features = 0
        if self._brightness is not None:
            features |= SUPPORT_BRIGHTNESS
        if self._color_temp is not None:
            features |= SUPPORT_COLOR_TEMP
        return features

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = data[self._attr] == 1
        if 'brightness' in data:
            self._brightness = data['brightness'] / 100.0 * 255.0
        if 'color_temp' in data:
            self._color_temp = data['color_temp']

        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            payload['brightness'] = \
                int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)

        if ATTR_COLOR_TEMP in kwargs:
            payload['color_temp'] = kwargs[ATTR_COLOR_TEMP]

        if not payload:
            payload[self._attr] = 1

        self.gw.send(self.device, payload)

    def turn_off(self):
        self.gw.send(self.device, {self._attr: 0})

# mesh light properties: name with (siid & piid)
MESH_LIGHT_PROPS = {
	'light': (2,1),
	'brightness': (2,2),
	'color_temp': (2,3),
}

class Gateway3MeshLight(Gateway3Device, LightEntity):
    _brightness = None
    _color_temp = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        if 'childs' in self.device:
            for did in self.device['childs']:
                self.gw.add_update(did, self.update)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()

        if 'childs' in self.device:
            for did in self.device['childs']:
                self.gw.remove_update(did, self.update)

    @property
    def should_poll(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def color_temp(self):
        return self._color_temp

    @property
    def min_mireds(self):
        return 153

    @property
    def max_mireds(self):
        return 370

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP

    def update(self, data: dict = None):
        if data is None:
            did = (self.device['childs'][0]
                   if 'childs' in self.device
                   else self.device['did'])
            try:
                payload = [{'did': did, 'siid': p[0], 'piid': p[1]}
                           for p in MESH_LIGHT_PROPS.values()]
                resp = self.gw.miio.send('get_properties', payload)
                data = bluetooth.parse_xiaomi_mesh_raw(resp)[did]
                _LOGGER.debug(f'{self.gw.host} | {did} data = {data} ')
            except:
                _LOGGER.debug(f"{self.gw.host} | {did} poll error")
                self.device['online'] = False
                return

            # _LOGGER.debug(f"{self.gw.host} | {did} poll mesh <= {data}")
            self._update(data)

        else:
            self._update(data)
            self.async_write_ha_state()

    def _update(self, data: dict):
        self.device['online'] = True

        if MESH_LIGHT_PROPS[self._attr] in data:
            self._state = data[MESH_LIGHT_PROPS[self._attr]]
        if MESH_LIGHT_PROPS['brightness'] in data:
            # 0...65535
            self._brightness = data[MESH_LIGHT_PROPS['brightness']] / 65535.0 * 255.0
        if MESH_LIGHT_PROPS['color_temp'] in data:
            # 2700..6500 => 370..153
            self._color_temp = \
                color.color_temperature_kelvin_to_mired(data[MESH_LIGHT_PROPS['color_temp']])

    def turn_on(self, **kwargs):
        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            payload[MESH_LIGHT_PROPS['brightness']] = \
                int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 65535)

        if ATTR_COLOR_TEMP in kwargs:
            payload[MESH_LIGHT_PROPS['color_temp']] = color.color_temperature_mired_to_kelvin(
                kwargs[ATTR_COLOR_TEMP])

        if not payload:
            payload[MESH_LIGHT_PROPS[self._attr]] = True

        self.gw.send_mesh_raw(self.device, payload)
        time.sleep(.5)  # delay before poll actual status

    def turn_off(self):
        self.gw.send_mesh_raw(self.device, {MESH_LIGHT_PROPS[self._attr]: False})
        time.sleep(.5)  # delay before poll actual status