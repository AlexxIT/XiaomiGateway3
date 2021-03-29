from dataclasses import dataclass, field
from typing import *

from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import Entity

from .utils import DOMAIN


# TODO: rewrite all usage to dataclass
@dataclass
class XiaomiDevice:
    did: str  # unique Xiaomi did
    model: str  # Xiaomi model
    mac: str
    type: str  # gateway, zigbee, ble, mesh
    online: bool

    device_info: Dict[str, Any]

    extra: Dict[str, Any] = field(default_factory=dict)

    # all device entities except stats
    entities: Dict[str, 'XiaomiEntity'] = field(default_factory=dict)

    gateways: List['Gateway3'] = field(default_factory=list)


class DevicesRegistry:
    """Global registry for all gateway devices. Because BLE devices updates
    from all gateway simultaniosly.

    Key - device did, `numb` for wifi and mesh devices, `lumi.ieee` for zigbee
    devices, `blt.3.alphanum` for ble devices, `group.numb` for mesh groups.
    """
    devices: Dict[str, dict] = {}
    setups: Dict[str, Callable] = None

    def add_setup(self, domain: str, handler):
        """Add hass device setup funcion."""
        self.setups[domain] = handler

    def add_entity(self, domain: str, device: dict, attr: str):
        if self not in device['gateways']:
            device['gateways'].append(self)

        if domain is None or attr in device['entities']:
            return

        # instant add entity to prevent double setup
        device['entities'][attr] = None

        self.setups[domain](self, device, attr)

    def set_entity(self, entity: 'XiaomiEntity'):
        entity.device['entities'][entity.attr] = entity

    def remove_entity(self, entity: 'XiaomiEntity'):
        entity.device['entities'].pop(entity.attr)


class XiaomiEntity(Entity):
    _ignore_offline = None
    _state = None

    def __init__(self, gateway: 'Gateway3', device: dict, attr: str):
        self.gw = gateway
        self.device = device

        self.attr = attr
        self._attrs = {}

        self._unique_id = f"{self.device['mac']}_{self.attr}"
        self._name = (self.device['device_name'] + ' ' +
                      self.attr.replace('_', ' ').title())

        self.entity_id = f"{DOMAIN}.{self._unique_id}"

    def debug(self, message: str):
        self.gw.debug(f"{self.entity_id} | {message}")

    async def async_added_to_hass(self):
        """Also run when rename entity_id"""
        custom: dict = self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)
        self._ignore_offline = custom.get('ignore_offline')

        if 'init' in self.device and self._state is None:
            self.update(self.device['init'])

        self.gw.set_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Also run when rename entity_id"""
        self.gw.remove_entity(self)

    # @property
    # def entity_registry_enabled_default(self):
    #     return False

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def available(self) -> bool:
        gw_available = any(
            gateway.available for gateway in self.device['gateways']
        )
        return gw_available and (self.device.get('online', True) or
                                 self._ignore_offline)

    @property
    def device_state_attributes(self):
        return self._attrs

    @property
    def device_info(self):
        """
        https://developers.home-assistant.io/docs/device_registry_index/
        """
        type_ = self.device['type']
        if type_ == 'gateway':
            return {
                'connections': {
                    (CONNECTION_NETWORK_MAC, self.device['wlan_mac'])
                },
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device['device_manufacturer'],
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'sw_version': self.device['fw_ver'],
            }
        elif type_ == 'zigbee':
            return {
                'connections': {(type_, self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device.get('device_manufacturer'),
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'sw_version': self.device.get('fw_ver'),
                'via_device': (DOMAIN, self.gw.device['mac'])
            }
        else:  # ble and mesh
            return {
                'connections': {('bluetooth', self.device['mac'])},
                'identifiers': {(DOMAIN, self.device['mac'])},
                'manufacturer': self.device.get('device_manufacturer'),
                'model': self.device['device_model'],
                'name': self.device['device_name'],
                'via_device': (DOMAIN, self.gw.device['mac'])
            }

    def update(self, data: dict):
        pass
