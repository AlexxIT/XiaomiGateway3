import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, State, HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    CONNECTION_ZIGBEE,
)
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    "plug_detection": BinarySensorDeviceClass.PLUG,
    "reverse": BinarySensorDeviceClass.LOCK,
    "square": BinarySensorDeviceClass.LOCK,
    "water_leak": BinarySensorDeviceClass.MOISTURE,
    "realtime_current_in": SensorDeviceClass.CURRENT,
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
    # Linptech Presence Sensor ES1
    "occupancy_duration": "mdi:timer",
}

ENTITY_CATEGORIES = {
    BLE: EntityCategory.DIAGNOSTIC,
    # GATEWAY: EntityCategory.DIAGNOSTIC,
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
    # Linptech Presence Sensor ES1
    "distance_00_08": EntityCategory.CONFIG,
    "distance_08_15": EntityCategory.CONFIG,
    "distance_15_23": EntityCategory.CONFIG,
    "distance_23_30": EntityCategory.CONFIG,
    "distance_30_38": EntityCategory.CONFIG,
    "distance_38_45": EntityCategory.CONFIG,
    "distance_45_53": EntityCategory.CONFIG,
    "distance_53_60": EntityCategory.CONFIG,
    "approach_distance": EntityCategory.CONFIG,
    "occupancy_duration": EntityCategory.DIAGNOSTIC,
    # Aqara Triple Wall Switch E1 (with N)
    "led_inverted": EntityCategory.CONFIG,
    "led_no_disturb": EntityCategory.CONFIG,
    "led_no_disturb_start": EntityCategory.CONFIG,
    "led_no_disturb_end": EntityCategory.CONFIG,
    # GranwinIoT Mesh Light V5
    "turn_on_state": EntityCategory.CONFIG,
    "default_brightness": EntityCategory.CONFIG,
    "default_temp": EntityCategory.CONFIG,
    "sleep_aid_minutes": EntityCategory.CONFIG,
    "sleep_aid_use_custom": EntityCategory.CONFIG,
    "sleep_aid_custom_init_brightness": EntityCategory.CONFIG,
    "sleep_aid_custom_init_temp": EntityCategory.CONFIG,
    "wakeup_minutes": EntityCategory.CONFIG,
    "wakeup_use_custom": EntityCategory.CONFIG,
    "wakeup_custom_final_brightness": EntityCategory.CONFIG,
    "wakeup_custom_final_temp": EntityCategory.CONFIG,
    "night_light": EntityCategory.CONFIG,
    "night_light_start": EntityCategory.CONFIG,
    "night_light_end": EntityCategory.CONFIG,
    "turn_on_transit_sec": EntityCategory.CONFIG,
    "turn_off_transit_sec": EntityCategory.CONFIG,
    "change_transit_sec": EntityCategory.CONFIG,
    "min_brightness": EntityCategory.CONFIG,
    # Linptech Mesh Triple Wall Switch (no N)
    "compatible_mode": EntityCategory.CONFIG,
    # Linptech Sliding Window Driver WD1
    "security_mode": EntityCategory.CONFIG,
    "power_replenishment": EntityCategory.DIAGNOSTIC,
    "realtime_current_in": EntityCategory.DIAGNOSTIC,
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

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.unique_id)},
        )

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
            if state and state.state not in ("unavailable", "unknown"):
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
                ok = await self.gw.miot_send(self.device, payload)
                if ok:
                    await self.miot_after_send(value)
            else:
                await self.gw.lumi_send(self.device, payload)

        elif self.device.type == ZIGBEE:
            if "commands" in payload:
                await self.gw.silabs_send(self.device, payload)
            else:
                await self.gw.lumi_send(self.device, payload)

        elif self.device.type == MESH:
            assert "mi_spec" in payload, payload

            if not await self.gw.miot_send(self.device, payload):
                return

            if self.attr != "group":
                await self.miot_after_send(value)
            else:
                await self.miot_group_after_send(value)

    async def miot_after_send(self, value: dict):
        # TODO: rewrite me
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

    async def miot_group_after_send(self, value: dict):
        try:
            childs = []
            for did in self.device.extra["childs"]:
                light = self.gw.devices[did].entities.get("light")
                childs.append(light.miot_after_send(value))
            if childs:
                await asyncio.gather(*childs)

        except Exception as e:
            self.debug("Can't update child states", exc_info=e)

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


def setup_entity(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    new_entity: Callable[["XGateway", XDevice, Converter], XEntity],
) -> "SetupHandler":
    def setup(gateway: "XGateway", device: XDevice, conv: Converter):
        """Setup process three situations:
        1. Add new entity first time
        2. Add existing entity without gateway to new gateway and new config entry
        3. Add existing entity with gateway to new config entry
        """

        # get existing entity
        entity = device.entities.get(conv.attr)
        if entity and entity.gw:
            gateway = entity.gw

        if device.model == MESH_GROUP_MODEL:
            connections = None
        elif device.type in (GATEWAY, BLE, MESH):
            connections = {(CONNECTION_NETWORK_MAC, device.mac)}
            if mac2 := device.extra.get("mac2"):
                connections.add((CONNECTION_NETWORK_MAC, mac2))
        else:
            connections = {(CONNECTION_ZIGBEE, device.ieee)}

        if device.type != GATEWAY and gateway.device:
            via_device = (DOMAIN, gateway.device.unique_id)
        else:
            via_device = None

        # https://developers.home-assistant.io/docs/device_registry_index/
        reg = device_registry.async_get(hass)
        reg.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, device.unique_id)},
            connections=connections,
            manufacturer=device.info.manufacturer,
            model=device.info.model,
            name=device.info.name,
            sw_version=device.fw_ver,
            via_device=via_device,
        )

        if not entity:
            # create new entity if not exists
            entity = new_entity(gateway, device, conv)
            device.entities[conv.attr] = entity
        elif entity.gw:
            # ignore entity with gateway
            return
        else:
            # bind entity to this gateway
            entity.gw = gateway

        add_entities([entity])

    return setup
