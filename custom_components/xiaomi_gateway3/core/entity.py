import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DEVICE_CLASS_DOOR, \
    DEVICE_CLASS_CONNECTIVITY, DEVICE_CLASS_MOISTURE, DEVICE_CLASS_LOCK
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.const import *
from homeassistant.core import callback, State
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, \
    CONNECTION_ZIGBEE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.template import Template

from .backward import ENTITY_CATEGORY_CONFIG, ENTITY_CATEGORY_DIAGNOSTIC, \
    XEntityBase
from .const import DOMAIN
from .converters import Converter, GATEWAY, ZIGBEE, BLE, MESH, MESH_GROUP_MODEL
from .device import XDevice

if TYPE_CHECKING:
    from .gateway import XGateway

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASSES = {
    BLE: DEVICE_CLASS_TIMESTAMP,
    GATEWAY: DEVICE_CLASS_CONNECTIVITY,
    MESH: DEVICE_CLASS_TIMESTAMP,
    ZIGBEE: DEVICE_CLASS_TIMESTAMP,
    "cloud_link": DEVICE_CLASS_CONNECTIVITY,
    "contact": DEVICE_CLASS_DOOR,
    "latch": DEVICE_CLASS_LOCK,
    "reverse": DEVICE_CLASS_LOCK,
    "square": DEVICE_CLASS_LOCK,
    "water_leak": DEVICE_CLASS_MOISTURE,
}

# support for older versions of the Home Assistant
ELECTRIC_POTENTIAL_VOLT = "V"
ELECTRIC_CURRENT_AMPERE = "A"

UNITS = {
    DEVICE_CLASS_BATTERY: PERCENTAGE,
    DEVICE_CLASS_HUMIDITY: PERCENTAGE,
    # zb light and motion and ble flower - lux
    DEVICE_CLASS_ILLUMINANCE: LIGHT_LUX,
    DEVICE_CLASS_POWER: POWER_WATT,
    DEVICE_CLASS_VOLTAGE: ELECTRIC_POTENTIAL_VOLT,
    DEVICE_CLASS_CURRENT: ELECTRIC_CURRENT_AMPERE,
    DEVICE_CLASS_PRESSURE: PRESSURE_HPA,
    DEVICE_CLASS_TEMPERATURE: TEMP_CELSIUS,
    DEVICE_CLASS_ENERGY: ENERGY_KILO_WATT_HOUR,
    "chip_temperature": TEMP_CELSIUS,
    "conductivity": CONDUCTIVITY,
    "gas_density": "% LEL",
    "idle_time": TIME_SECONDS,
    "linkquality": "lqi",
    "max_power": POWER_WATT,
    "moisture": PERCENTAGE,
    "msg_received": "msg",
    "msg_missed": "msg",
    "new_resets": "rst",
    "resets": "rst",
    "rssi": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    "smoke_density": "% obs/ft",
    "supply": PERCENTAGE,
    "tvoc": CONCENTRATION_PARTS_PER_BILLION,
    # "link_quality": "lqi",
    # "rssi": "dBm",
    # "msg_received": "msg",
    # "msg_missed": "msg",
    # "unresponsive": "times"
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
    "switch": "mdi:light-switch",
    "tvoc": "mdi:cloud",
}

# The state represents a measurement in present time
STATE_CLASS_MEASUREMENT: Final = "measurement"
# The state represents a total amount, e.g. net energy consumption
STATE_CLASS_TOTAL: Final = "total"
# The state represents a monotonically increasing total, e.g. an amount of consumed gas
STATE_CLASS_TOTAL_INCREASING: Final = "total_increasing"

# https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
STATE_CLASSES = {
    DEVICE_CLASS_ENERGY: STATE_CLASS_TOTAL_INCREASING,
}

ENTITY_CATEGORIES = {
    BLE: ENTITY_CATEGORY_DIAGNOSTIC,
    GATEWAY: ENTITY_CATEGORY_DIAGNOSTIC,
    MESH: ENTITY_CATEGORY_DIAGNOSTIC,
    ZIGBEE: ENTITY_CATEGORY_DIAGNOSTIC,
    "battery": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_charging": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_low": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_percent": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_voltage": ENTITY_CATEGORY_DIAGNOSTIC,
    "blind_time": ENTITY_CATEGORY_CONFIG,
    "charge_protect": ENTITY_CATEGORY_CONFIG,
    "child_mode": ENTITY_CATEGORY_CONFIG,
    "chip_temperature": ENTITY_CATEGORY_DIAGNOSTIC,
    "cloud_link": ENTITY_CATEGORY_DIAGNOSTIC,
    "display_unit": ENTITY_CATEGORY_CONFIG,
    "fault": ENTITY_CATEGORY_DIAGNOSTIC,
    "flex_switch": ENTITY_CATEGORY_CONFIG,
    "led": ENTITY_CATEGORY_CONFIG,
    "idle_time": ENTITY_CATEGORY_DIAGNOSTIC,
    "max_power": ENTITY_CATEGORY_DIAGNOSTIC,
    "mode": ENTITY_CATEGORY_CONFIG,
    "motor_reverse": ENTITY_CATEGORY_CONFIG,
    "motor_speed": ENTITY_CATEGORY_CONFIG,
    "occupancy_timeout": ENTITY_CATEGORY_CONFIG,
    "power_on_state": ENTITY_CATEGORY_CONFIG,
    "sensitivity": ENTITY_CATEGORY_CONFIG,
    "wireless": ENTITY_CATEGORY_CONFIG,
    "wireless_1": ENTITY_CATEGORY_CONFIG,
    "wireless_2": ENTITY_CATEGORY_CONFIG,
    "wireless_3": ENTITY_CATEGORY_CONFIG,
}

STATE_TIMEOUT = timedelta(minutes=10)


class XEntity(XEntityBase):
    # duplicate here because typing problem
    _attr_extra_state_attributes: dict = None

    attributes_template: Template = None

    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
        attr = conv.attr

        self.gw = gateway
        self.device = device
        self.attr = attr

        self.subscribed_attrs = device.subscribe_attrs(conv)

        # minimum support version: Hass v2021.6
        self._attr_available = device.available
        self._attr_device_class = DEVICE_CLASSES.get(attr, attr)
        self._attr_entity_registry_enabled_default = conv.enabled != False
        self._attr_extra_state_attributes = {}
        self._attr_icon = ICONS.get(attr)
        self._attr_name = device.attr_name(attr)
        self._attr_should_poll = conv.poll
        self._attr_unique_id = device.attr_unique_id(attr)
        self._attr_entity_category = ENTITY_CATEGORIES.get(attr)
        self.entity_id = device.entity_id(conv)

        if conv.domain == "sensor":  # binary_sensor moisture problem
            self._attr_native_unit_of_measurement = UNITS.get(attr)

            if attr in STATE_CLASSES:
                self._attr_state_class = STATE_CLASSES[attr]
            elif attr in UNITS:
                # by default all sensors with units is measurement sensors
                self._attr_state_class = STATE_CLASS_MEASUREMENT

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
            configuration_url=device.info.url
        )

        # fix don't enabled by default entities
        device.entities[attr] = self

    @property
    def customize(self) -> dict:
        if not self.hass:
            return {}
        return self.hass.data[DATA_CUSTOMIZE].get(self.entity_id)

    def debug(self, msg: str, exc_info=None):
        self.gw.debug(f"{self.entity_id} | {msg}", exc_info=exc_info)

    async def async_added_to_hass(self):
        """Also run when rename entity_id"""
        # self.platform._async_add_entity => self.add_to_platform_finish
        #   => self.async_internal_added_to_hass => self.async_added_to_hass
        #   => self.async_write_ha_state
        # self.device.entities[self.attr] = self  # fix rename entity_id

        self.render_attributes_template()

        if hasattr(self, "async_get_last_state"):
            state: State = await self.async_get_last_state()
            if state:
                self.async_restore_last_state(state.state, state.attributes)
                return

        if hasattr(self, "async_update"):
            await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Also run when rename entity_id"""
        # self.device.setup_attrs.remove(self.attr)
        # self.device.entities.pop(self.attr)

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
                self.device.available or
                self.customize.get('ignore_offline', False)
        )

    @callback
    def render_attributes_template(self):
        try:
            attrs = self.attributes_template.async_render({
                "attr": self.attr,
                "device": self.device,
                "gateway": self.gw.device
            })
            if isinstance(attrs, dict):
                self._attr_extra_state_attributes.update(attrs)
        except AttributeError:
            pass
        except:
            _LOGGER.exception("Can't render attributes")

    ############################################################################

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
                await asyncio.sleep(.5)
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
