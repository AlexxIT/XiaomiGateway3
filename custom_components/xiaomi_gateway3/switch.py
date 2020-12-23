import logging
import time

from functools import partial
from homeassistant.components import persistent_notification
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN, Gateway3Device
from .core import bluetooth
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


class Gateway3Switch(Gateway3Device, ToggleEntity):
    @property
    def state(self):
        return self._state

    @property
    def is_on(self):
        return self._state == STATE_ON

    def update(self, data: dict = None):
        if self._attr in data:
            self._state = STATE_ON if data[self._attr] else STATE_OFF
        self.async_write_ha_state()

    def turn_on(self):
        self.gw.send(self.device, {self._attr: 1})

    def turn_off(self):
        self.gw.send(self.device, {self._attr: 0})


class Gateway3MeshSwitch(Gateway3Device, ToggleEntity):

    _siid = 0
    _piid = 0
    _on_value = None
    _off_value = None

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

    def __init__(self, gateway: Gateway3, device: dict, attr: str):
        super(Gateway3MeshSwitch, self).__init__(gateway, device, attr)

        mesh_prop = device['mesh_prop']

        self._siid = mesh_prop[0]
        self._piid = mesh_prop[1]
        self._on_value = mesh_prop[3]
        self._off_value = mesh_prop[4]
        
        self._unique_id = f"{self.device['mac']}_{self._siid}_{self._piid}"
        self._name = (self.device['device_name'] + ' ' +
                      mesh_prop[2].title()) if mesh_prop[2] is not None else self.device['device_name']

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

    @property
    def should_poll(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self._state

    def update(self, data: dict = None):
        if data is None:
            did = self.device['did']
            try:
                payload = [{'did': did,'siid': self._siid,'piid': self._piid,}]
                resp = self.gw.miio.send('get_properties', payload)
                # _LOGGER.debug(f"{self.gw.host} | {did} resp = {resp}")
                self.gw.process_mesh_data(resp)

            except Exception as e:
                _LOGGER.debug(f"{self.gw.host} | {did} poll error: {e}")
                self.device['online'] = False
                self.async_write_ha_state()
            return

        self._update(data)


    def _update(self, data: dict):
        self.device['online'] = True
        # _LOGGER.debug(f"{self.gw.host} | {self.device['did']}_{self._siid}_{self._piid} _update: {data}")
        key = (self._siid, self._piid)
        if key in data:
            self._state = data[key] == self._on_value
        
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        self.gw.send_mesh(self.device, {(self._siid, self._piid): self._on_value})
        time.sleep(.5)  # delay before poll actual status
    
    def turn_off(self, **kwargs):
        self.gw.send_mesh(self.device, {(self._siid, self._piid): self._off_value})
        time.sleep(.5)  # delay before poll actual status


class FirmwareLock(Gateway3Switch):
    @property
    def icon(self):
        return 'mdi:cloud-lock'

    def turn_on(self):
        if self.gw.lock_firmware(enable=True):
            self._state = STATE_ON
            self.async_write_ha_state()

            persistent_notification.async_create(
                self.hass, "Firmware update is locked. You can sleep well.",
                "Xiaomi Gateway 3"
            )

    def turn_off(self):
        if self.gw.lock_firmware(enable=False):
            self._state = STATE_OFF
            self.async_write_ha_state()
