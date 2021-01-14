import logging

from homeassistant.components import persistent_notification
from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN, Gateway3Device
from .core.gateway3 import Gateway3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        if attr == 'firmware lock':
            async_add_entities([FirmwareLock(gateway, device, attr)])
        elif device['type'] == 'mesh':
            async_add_entities([Gateway3MeshSwitch(gateway, device, attr)])
        else:
            async_add_entities([Gateway3Switch(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('switch', setup)


async def async_unload_entry(hass, entry):
    return True


class Gateway3Switch(Gateway3Device, ToggleEntity):
    @property
    def is_on(self):
        return self._state

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = bool(data[self._attr])
        self.async_write_ha_state()

    def turn_on(self):
        self.gw.send(self.device, {self._attr: 1})

    def turn_off(self):
        self.gw.send(self.device, {self._attr: 0})


class Gateway3MeshSwitch(Gateway3Device, ToggleEntity):
    @property
    def should_poll(self):
        return False

    @property
    def is_on(self):
        return self._state

    def update(self, data: dict = None):
        if data is None:
            self.gw.mesh_force_update()
            return

        self.device['online'] = True

        if self._attr in data:
            self._state = bool(data[self._attr])

        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        self._state = True

        self.gw.send_mesh(self.device, {self._attr: True})

        self.async_write_ha_state()

    def turn_off(self, **kwargs):
        self._state = False

        self.gw.send_mesh(self.device, {self._attr: False})

        self.async_write_ha_state()


class FirmwareLock(Gateway3Switch):
    @property
    def icon(self):
        return 'mdi:cloud-lock'

    def turn_on(self):
        if self.gw.lock_firmware(enable=True):
            self._state = True
            self.async_write_ha_state()

            persistent_notification.async_create(
                self.hass, "Firmware update is locked. You can sleep well.",
                "Xiaomi Gateway 3"
            )

    def turn_off(self):
        if self.gw.lock_firmware(enable=False):
            self._state = False
            self.async_write_ha_state()
