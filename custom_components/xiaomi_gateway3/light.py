import logging

from homeassistant.components.light import LightEntity, SUPPORT_BRIGHTNESS, \
    ATTR_BRIGHTNESS

from . import DOMAIN, Gateway3Device
from .gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Light(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.unique_id]
    gw.add_setup('light', setup)


class Gateway3Light(Gateway3Device, LightEntity):
    _brightness = None

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        features = 0
        if self._brightness is not None:
            features |= SUPPORT_BRIGHTNESS
        return features

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = data[self._attr] == 1
        if 'brightness' in data:
            self._brightness = data['brightness'] / 100.0 * 255.0

        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            br = int(kwargs[ATTR_BRIGHTNESS] / 255.0 * 100.0)
            self.gw.send(self.device, 'brightness', br)
        else:
            self.gw.send(self.device, self._attr, 1)

    def turn_off(self):
        self.gw.send(self.device, self._attr, 0)
