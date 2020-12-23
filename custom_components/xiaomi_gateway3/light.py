import logging

from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS, SUPPORT_COLOR_TEMP, ATTR_COLOR_TEMP
from homeassistant.util import color

from . import DOMAIN, Gateway3Device
from .core.gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if device['type'] == 'zigbee':
            async_add_entities([Gateway3Light(gateway, device, attr)])
        elif 'childs' in device:
            async_add_entities([Gateway3MeshGroup(gateway, device, attr)])
        else:
            async_add_entities([Gateway3MeshLight(gateway, device, attr)],
                               True)

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('light', setup)


async def async_unload_entry(hass, entry):
    return True


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
            self._state = bool(data[self._attr])
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


class Gateway3MeshLight(Gateway3Device, LightEntity):
    _brightness = None
    _color_temp = None

    @property
    def should_poll(self) -> bool:
        return False

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
            self.gw.mesh_force_update()
            return

        self.device['online'] = True

        if self._attr in data:
            self._state = bool(data[self._attr])
        if 'brightness' in data:
            # 0...65535
            self._brightness = data['brightness'] / 65535.0 * 255.0
        if 'color_temp' in data and data['color_temp']:
            # 2700..6500 => 370..153
            self._color_temp = \
                color.color_temperature_kelvin_to_mired(data['color_temp'])

        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        # instantly change the HA state, and after 2 seconds check the actual
        # state of the lamp (optimistic change state)
        payload = {}

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            payload['brightness'] = int(self._brightness / 255.0 * 65535)

        if ATTR_COLOR_TEMP in kwargs:
            self._color_temp = kwargs[ATTR_COLOR_TEMP]
            payload['color_temp'] = \
                color.color_temperature_mired_to_kelvin(self._color_temp)

        if not payload:
            payload[self._attr] = self._state = True

        self.gw.send_mesh(self.device, payload)

        self.async_write_ha_state()

    def turn_off(self):
        # instantly change the HA state, and after 2 seconds check the actual
        # state of the lamp (optimistic change state)
        self._state = False

        self.gw.send_mesh(self.device, {self._attr: False})

        self.async_write_ha_state()


class Gateway3MeshGroup(Gateway3MeshLight):
    async def async_added_to_hass(self):
        if 'childs' in self.device:
            for did in self.device['childs']:
                self.gw.add_update(did, self.update)

    async def async_will_remove_from_hass(self) -> None:
        if 'childs' in self.device:
            for did in self.device['childs']:
                self.gw.remove_update(did, self.update)

    @property
    def should_poll(self):
        return False

    @property
    def icon(self):
        return 'mdi:lightbulb-group'
