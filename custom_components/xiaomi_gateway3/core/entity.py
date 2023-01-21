import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.const import *
from homeassistant.core import callback, State
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    CONNECTION_ZIGBEE,
)
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.template import Template

from .const import DOMAIN
from .converters import Converter, GATEWAY, ZIGBEE, BLE, MESH, MESH_GROUP_MODEL
from .device import XDevice

if TYPE_CHECKING:
    from .gateway import XGateway

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASSES = {
    BLE: SensorDeviceClass.TIMESTAMP,
    GATEWAY: BinarySensorDeviceClass.CONNECTIVITY,
    MESH: SensorDeviceClass.TIMESTAMP,
    ZIGBEE: SensorDeviceClass.TIMESTAMP,
    "cloud_link": BinarySensorDeviceClass.CONNECTIVITY,
    "contact": BinarySensorDeviceClass.DOOR,
    "latch": BinarySensorDeviceClass.LOCK,
    "reverse": BinarySensorDeviceClass.LOCK,
    "square": BinarySensorDeviceClass.LOCK,
    "water_leak": BinarySensorDeviceClass.MOISTURE,
}

ICONS = {
    BLE: "mdi:bluetooth",
    GATEWAY: "mdi:router-wireless",
    MESH: "mdi:bluetooth",
    ZIGBEE: "mdi:zigbee",
    "action": "mdi:bell",
    "child_mode": "mdi:baby-carriage",
    "conductivity": "mdi:flower",
    "gas_density": "mdi:google-circles-communities",
    "group": "mdi:lightbulb-group",
    "idle_time": "mdi:timer",
    "led": "mdi:led-off",
    "outlet": "mdi:power-socket-us",
    "pair": "mdi:zigbee",
    "plug": "mdi:power-plug",
    "smoke_density": "mdi:google-circles-communities",
    "supply": "mdi:gauge",
    "tvoc": "mdi:cloud",
}

ENTITY_CATEGORIES = {
    BLE: EntityCategory.DIAGNOSTIC,
    GATEWAY: EntityCategory.DIAGNOSTIC,
    MESH: EntityCategory.DIAGNOSTIC,
    ZIGBEE: EntityCategory.DIAGNOSTIC,
    "battery": EntityCategory.DIAGNOSTIC,
    "battery_charging": EntityCategory.DIAGNOSTIC,
    "battery_low": EntityCategory.DIAGNOSTIC,
    "battery_percent": EntityCategory.DIAGNOSTIC,
    "battery_voltage": EntityCategory.DIAGNOSTIC,
    "blind_time": EntityCategory.CONFIG,
    "charge_protect": EntityCategory.CONFIG,
    "child_mode": EntityCategory.CONFIG,
    "chip_temperature": EntityCategory.DIAGNOSTIC,
    "cloud_link": EntityCategory.DIAGNOSTIC,
    "display_unit": EntityCategory.CONFIG,
    "fault": EntityCategory.DIAGNOSTIC,
    "flex_switch": EntityCategory.CONFIG,
    "led": EntityCategory.CONFIG,
    "idle_time": EntityCategory.DIAGNOSTIC,
    "max_power": EntityCategory.DIAGNOSTIC,
    "mode": EntityCategory.CONFIG,
    "motor_reverse": EntityCategory.CONFIG,
    "motor_speed": EntityCategory.CONFIG,
    "occupancy_timeout": EntityCategory.CONFIG,
    "power_on_state": EntityCategory.CONFIG,
    "sensitivity": EntityCategory.CONFIG,
    "wireless": EntityCategory.CONFIG,
    "wireless_1": EntityCategory.CONFIG,
    "wireless_2": EntityCategory.CONFIG,
    "wireless_3": EntityCategory.CONFIG,
}

STATE_TIMEOUT = timedelta(minutes=10)


class XEntity(Entity):
    # duplicate here because typing problem
    _attr_extra_state_attributes: dict = None

    added = False
    attributes_template: Template = None

    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        attr = conv.attr

        self.gw = gateway
        self.device = device
        self.attr = attr

        self.subscribed_attrs = device.subscribe_attrs(conv)

        # minimum support version: Hass v2021.6
        self._attr_available = device.available
        self._attr_device_class = DEVICE_CLASSES.get(attr, attr)
        self._attr_entity_registry_enabled_default = conv.enabled is not False
        self._attr_extra_state_attributes = {}
        self._attr_icon = ICONS.get(attr)
        self._attr_name = device.attr_name(attr)
        self._attr_should_poll = conv.poll
        self._attr_unique_id = device.attr_unique_id(attr)
        self._attr_entity_category = ENTITY_CATEGORIES.get(attr)
        self.entity_id = device.entity_id(conv)

        if device.model == MESH_GROUP_MODEL:
            connections = None
        elif device.type in (GATEWAY, BLE, MESH):
            connections = {(CONNECTION_NETWORK_MAC, device.mac)}
        else:
            connections = {(CONNECTION_ZIGBEE, device.ieee)}

        if device.type != GATEWAY and gateway.device:
            via_device = (DOMAIN, gateway.device.unique_id)
        else:
            via_device = None

        # https://developers.home-assistant.io/docs/device_registry_index/
        self._attr_device_info = DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, device.unique_id)},
            manufacturer=device.info.manufacturer,
            model=device.info.model,
            name=device.info.name,
            sw_version=device.fw_ver,
            via_device=via_device,
        )

        # fix don't enabled by default entities
        device.entities[attr] = self

    @property
    def customize(self) -> dict:
        if not self.hass:
            return {}
        return self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)

    @property
    def hass_state(self):
        if self.hass:
            state = self.hass.states.get(self.entity_id)
            hass_state = state.state if state else "NO_STATE"
        else:
            hass_state = "DISABLED"
        entity_state = getattr(self, "native_value", self.state)
        if hass_state == entity_state:
            return hass_state
        return {
            "state": hass_state,
            "value": entity_state,
        }

    def debug(self, msg: str, exc_info=None):
        self.gw.debug(f"{self.entity_id} | {msg}", exc_info=exc_info)

    async def async_added_to_hass(self):
        self.added = True

        # also run when rename entity_id
        self.render_attributes_template()

        if hasattr(self, "async_get_last_state"):
            state: State = await self.async_get_last_state()
            if state:
                self.async_restore_last_state(state.state, state.attributes)
                return

        if hasattr(self, "async_update"):
            await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        # also run when rename entity_id
        self.added = False

    @callback
    def async_set_state(self, data: dict):
        """Handle state update from gateway."""
        self._attr_state = data[self.attr]

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        """Restore previous state."""
        self._attr_state = state

    @callback
    def async_update_available(self):
        gw_available = any(gw.available for gw in self.device.gateways)
        self._attr_available = gw_available and (
            self.device.available or self.customize.get("ignore_offline", False)
        )

    @callback
    def render_attributes_template(self):
        try:
            attrs = self.attributes_template.async_render(
                {"attr": self.attr, "device": self.device, "gateway": self.gw.device}
            )
            if isinstance(attrs, dict):
                self._attr_extra_state_attributes.update(attrs)
        except AttributeError:
            pass
        except Exception as e:
            _LOGGER.error("Can't render attributes", exc_info=e)

    ###########################################################################

    async def device_send(self, value: dict):
        # GATEWAY support lumi_send in lumi spec and miot_send in miot spec
        # ZIGBEE support lumi_send in lumi and miot spec and silabs_send
        # MESH support only miot_send in miot spec
        payload = self.device.encode(value)
        if not payload:
            return

        if self.device.type == GATEWAY:
            assert "params" in payload or "mi_spec" in payload, payload

            if "mi_spec" in payload:
                await self.gw.miot_send(self.device, payload)
            else:
                await self.gw.lumi_send(self.device, payload)

        elif self.device.type == ZIGBEE:
            if "commands" in payload:
                await self.gw.silabs_send(self.device, payload)
            else:
                await self.gw.lumi_send(self.device, payload)

        elif self.device.type == MESH:
            assert "mi_spec" in payload, payload

            ok = await self.gw.miot_send(self.device, payload)
            if not ok or self.attr == "group":
                return

            payload = self.device.encode_read(self.subscribed_attrs)
            for _ in range(10):
                await asyncio.sleep(0.5)
                data = await self.gw.miot_read(self.device, payload)
                # check that all read attrs are equal to send attrs
                if not data or any(data.get(k) != v for k, v in value.items()):
                    continue
                self.async_set_state(data)
                self._async_write_ha_state()
                break

    async def device_read(self, attrs: set):
        payload = self.device.encode_read(attrs)
        if not payload:
            return

        if self.device.type == GATEWAY:
            assert "params" in payload or "mi_spec" in payload, payload
            if "mi_spec" in payload:
                data = await self.gw.miot_read(self.device, payload)
                if data:
                    self.async_set_state(data)
            else:
                await self.gw.lumi_read(self.device, payload)

        elif self.device.type == ZIGBEE:
            if "commands" in payload:
                await self.gw.silabs_read(self.device, payload)
            else:
                await self.gw.lumi_read(self.device, payload)

        elif self.device.type == MESH:
            assert "mi_spec" in payload, payload
            data = await self.gw.miot_read(self.device, payload)
            if data:
                # support instant update state
                self.async_set_state(data)

    async def update_state(self):
        if hasattr(self, "async_update"):
            await self.async_update()
        if self.added:
            self.async_write_ha_state()
