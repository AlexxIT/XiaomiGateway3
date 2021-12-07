import asyncio
import logging
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from homeassistant.components.binary_sensor import DEVICE_CLASS_DOOR, \
    DEVICE_CLASS_CONNECTIVITY, DEVICE_CLASS_MOISTURE, DEVICE_CLASS_LOCK
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
from homeassistant.config import DATA_CUSTOMIZE
from homeassistant.const import *
from homeassistant.core import callback, State
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, \
    CONNECTION_ZIGBEE
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.template import Template

from . import converters
from .converters import Converter, LUMI_GLOBALS, GATEWAY, ZIGBEE, \
    BLE, MESH, MESH_GROUP_MODEL
from .converters.stats import STAT_GLOBALS
from .utils import DOMAIN

if TYPE_CHECKING:
    from .gateway import XGateway
    from .gateway.base import GatewayBase

_LOGGER = logging.getLogger(__name__)

RE_DID = re.compile(r"^lumi.[1-9a-f][0-9a-f]{,15}$")
RE_ZIGBEE_MAC = re.compile(r"^0x[0-9a-f]{16}$")
RE_NETWORK_MAC = re.compile(r"^[0-9a-f]{12}$")
RE_NWK = re.compile(r"^0x[0-9a-z]{4}$")


class XDevice:
    converters: List[Converter] = None
    last_seen: int = 0

    _available: bool = True

    def __init__(self, type: str, model: Union[str, int] = None,
                 did: str = None, mac: str = None, nwk: str = None):
        """Base class to handle device of any type."""
        assert type in (GATEWAY, ZIGBEE, BLE, MESH)
        if type == ZIGBEE:
            assert isinstance(model, str)
            assert RE_DID.match(did)
            assert RE_ZIGBEE_MAC.match(mac)
            assert RE_NWK.match(nwk)
        elif type == BLE:
            assert isinstance(model, int)
            assert did.startswith("blt.")
            assert RE_NETWORK_MAC.match(mac)
        elif model == MESH_GROUP_MODEL:
            assert did.startswith("group.")
        else:
            assert isinstance(model, str if type == GATEWAY else int)
            assert did.isdecimal()
            assert RE_NETWORK_MAC.match(mac), mac

        # TODO: assert mac
        self.type = type
        self.model = model
        self.did = did
        self.mac = mac
        self.nwk = nwk

        # device brand, model, name and converters
        self.info = converters.get_device_info(model, type)
        # all device entities
        self.entities: Dict[str, 'XEntity'] = {}
        # device gateways (one for GW and Zigbee), multiple for BLE and Mesh
        self.gateways: List['GatewayBase'] = []

        # internal device storage from any useful data
        self.extra: Dict[str, Any] = {}
        self.lazy_setup = set()

    @property
    def available(self):
        return self._available

    @available.setter
    def available(self, value: bool):
        if self._available == value:
            return
        self._available = value
        if self.entities:
            self.async_update_available()

    @property
    def fw_ver(self) -> Any:
        return self.extra.get("fw_ver")

    @property
    def ieee(self) -> str:
        """For Hass device connections."""
        return ":".join([self.mac[i:i + 2] for i in range(2, 18, 2)])

    @property
    def has_zigbee_conv(self) -> bool:
        if not self.converters:
            return False
        return any(True for conv in self.converters if conv.zigbee)

    def zigbee_config(self) -> list:
        return [conv for conv in self.converters if hasattr(conv, "config")]

    def update_model(self, value: str):
        # xiaomi soft adds tail to some models: .v1 or .v2 or .v3
        self.model = value[:-3] if value[-3:-1] == ".v" else value
        self.info = converters.get_device_info(self.model, self.type)

    def unique_id(self, attr: str):
        # backward compatibility
        if attr in ("plug", "outlet"):
            attr = "switch"
        return f"{self.mac}_{attr}"

    def name(self, attr: str):
        # this words always uppercase
        if attr in ("ble", "led", "rssi", "usb"):
            return self.info.name + " " + attr.upper()

        attr = attr.replace("_", " ").title()

        # skip second attr in name if exists
        if attr in self.info.name:
            return self.info.name

        return self.info.name + " " + attr

    def entity_id(self, conv: Converter):
        name = self.extra.get("entity_name", self.mac)
        return f"{conv.domain}.{name}_{conv.attr}"

    # TODO: rename
    def subscribe_attrs(self, conv: Converter):
        attrs = {conv.attr}
        if conv.childs:
            attrs |= set(conv.childs)
        attrs.update(c.attr for c in self.converters if c.parent == conv.attr)
        return attrs

    def __str__(self):
        s = f"XDevice({self.type}, {self.model}, {self.mac}"
        s += f", {self.nwk})" if self.nwk else ")"
        return s

    def setup_entitites(self, gateway: 'GatewayBase', entities: list = None):
        kwargs: Dict[str, Any] = {"entities": entities} if entities else {}
        for key in ("global", self.model, self.mac, self.did):
            if key in gateway.defaults:
                update(kwargs, gateway.defaults[key])

        if "model" in kwargs:
            # support change device model in config
            self.update_model(kwargs["model"])

        if "device_name" in kwargs:
            # support set device name in config
            self.info.name = kwargs["device_name"]

        if "entity_name" in kwargs:
            # support change entity name in config
            self.extra["entity_name"] = kwargs["entity_name"]

        self.setup_converters(kwargs.get("entities"))

        # if self.lazy_setup:
        #     return

        for conv in self.converters:
            # support change attribute domain in config
            domain = kwargs.get(conv.attr, conv.domain)
            if domain is None or conv.attr in self.entities:
                continue
            if conv.enabled is None:
                self.lazy_setup.add(conv.attr)
                continue
            gateway.setups[domain](gateway, self, conv)

    def setup_converters(self, entities: list = None):
        """If no entities - use only required converters. Otherwise search for
        converters in:
           - LUMI_GLOBALS list
           - STAT_GLOBALS list
           - converters childs list (always sensor)
        """
        if not entities:
            self.converters = self.info.spec
            return

        self.converters = self.info.spec.copy()

        for attr in entities:
            if attr in LUMI_GLOBALS:
                self.converters.append(LUMI_GLOBALS[attr])

            if attr == self.type and attr in STAT_GLOBALS:
                self.converters.append(STAT_GLOBALS[attr])

            for conv in self.info.spec:
                if conv.childs and attr in conv.childs:
                    conv = Converter(attr, "sensor")
                    self.converters.append(conv)

    def decode(self, attr_name: str, value: Any) -> Optional[dict]:
        """Find converter by attr_name and decode value."""
        for conv in self.converters:
            if conv.attr == attr_name:
                payload = {}
                conv.decode(self, payload, value)
                return payload
        return None

    def decode_lumi(self, value: list) -> dict:
        """Decode value from Zigbee Lumi/MIoT spec."""
        payload = {}

        for param in value:
            if param.get("error_code", 0) != 0:
                continue

            v = param["value"] if "value" in param else param["arguments"]

            # res_name is Lumi format
            if "res_name" in param:
                prop = param["res_name"]
                conv: Converter = LUMI_GLOBALS.get(prop)
                if conv:
                    conv.decode(self, payload, v)

            # piid or eiid is MIoT format
            elif "piid" in param:
                prop = f"{param['siid']}.p.{param['piid']}"
            elif "eiid" in param:
                prop = f"{param['siid']}.e.{param['eiid']}"
            else:
                raise RuntimeError

            for conv in self.converters:
                if conv.mi == prop:
                    conv.decode(self, payload, v)

        return payload

    def decode_miot(self, value: list):
        """Decode value from Mesh MIoT spec."""
        for item in value:
            item["error_code"] = item.pop("code", 0)
        return self.decode_lumi(value)

    def decode_zigbee(self, value: dict) -> Optional[dict]:
        """Decode value from Zigbee spec."""
        payload = {}
        for conv in self.converters:
            if conv.zigbee == value["cluster"]:
                conv.decode(self, payload, value)
        return payload

    def encode(self, value: dict) -> dict:
        """Encode payload to supported spec, depends on attrs.

        @param value: dict with {attr: value} pairs
        @return: dict with `params` (lumi spec), `mi_spec` (miot spec),
            `commands` (zigbee spec)
        """
        payload = {}
        for k, v in value.items():
            for conv in self.converters:
                if conv.attr == k:
                    conv.encode(self, payload, v)
        return payload

    def encode_read(self, attrs: set) -> dict:
        payload = {}
        for conv in self.converters:
            if conv.attr in attrs:
                conv.read(self, payload)
        return payload

    @property
    def powered(self) -> bool:
        return "sensor" not in self.converters[0].domain

    @callback
    def update(self, value: dict):
        """Push new state to Hass entities."""
        if not value:
            return

        attrs = value.keys()

        if self.lazy_setup:
            for attr in self.lazy_setup & attrs:
                self.lazy_setup.remove(attr)
                conv = next(c for c in self.converters if c.attr == attr)
                gateway = self.gateways[0]
                gateway.setups[conv.domain](gateway, self, conv)

        for entity in self.entities.values():
            if entity.subscribed_attrs & attrs:
                entity.async_set_state(value)
                if entity.hass:
                    entity.async_write_ha_state()

    @callback
    def async_update_available(self):
        for entity in self.entities.values():
            entity.async_update_available()
            if entity.hass:
                entity.async_write_ha_state()


DEVICE_CLASSES = {
    BLE: DEVICE_CLASS_TIMESTAMP,
    GATEWAY: DEVICE_CLASS_CONNECTIVITY,
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
    ZIGBEE: "mdi:zigbee",
    "action": "mdi:bell",
    "alarm": "mdi:shield-home",
    "conductivity": "mdi:flower",
    "gas_density": "mdi:google-circles-communities",
    "group": "mdi:lightbulb-group",
    "idle_time": "mdi:timer",
    "led": "mdi:led-off",
    "moisture": "mdi:water-percent",
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

# Config: An entity which allows changing the configuration of a device
ENTITY_CATEGORY_CONFIG: Final = "config"
# Diagnostic: An entity exposing some configuration parameter or diagnostics of a device
ENTITY_CATEGORY_DIAGNOSTIC: Final = "diagnostic"

ENTITY_CATEGORIES = {
    BLE: ENTITY_CATEGORY_DIAGNOSTIC,
    GATEWAY: ENTITY_CATEGORY_DIAGNOSTIC,
    ZIGBEE: ENTITY_CATEGORY_DIAGNOSTIC,
    "baby_mode": ENTITY_CATEGORY_CONFIG,
    "battery": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_charging": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_low": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_percent": ENTITY_CATEGORY_DIAGNOSTIC,
    "battery_voltage": ENTITY_CATEGORY_DIAGNOSTIC,
    "blind_time": ENTITY_CATEGORY_CONFIG,
    "charge_protect": ENTITY_CATEGORY_CONFIG,
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
    "smart": ENTITY_CATEGORY_CONFIG,
    "smart_1": ENTITY_CATEGORY_CONFIG,
    "smart_2": ENTITY_CATEGORY_CONFIG,
}

STATE_TIMEOUT = timedelta(minutes=10)


class XEntity(Entity):
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
        self._attr_device_class = DEVICE_CLASSES.get(attr, attr)
        self._attr_entity_registry_enabled_default = conv.enabled != False
        self._attr_extra_state_attributes = {}
        self._attr_icon = ICONS.get(attr)
        self._attr_name = device.name(attr)
        self._attr_should_poll = conv.poll
        self._attr_unique_id = device.unique_id(attr)
        self._attr_entity_category = ENTITY_CATEGORIES.get(attr)
        self.entity_id = device.entity_id(conv)

        if conv.domain == "sensor":  # binary_sensor moisture problem
            self._attr_unit_of_measurement = UNITS.get(attr)

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
            via_device = (DOMAIN, gateway.device.mac)
        else:
            via_device = None

        # https://developers.home-assistant.io/docs/device_registry_index/
        self._attr_device_info = DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, device.mac)},
            manufacturer=device.info.manufacturer,
            model=device.info.model,
            name=device.info.name,
            sw_version=device.fw_ver,
            via_device=via_device,
            configuration_url=device.info.url
        )

        # stats sensors always available
        if attr in (GATEWAY, ZIGBEE, BLE):
            self.__dict__["available"] = True

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
        self.device.entities[self.attr] = self  # fix rename entity_id

        self.render_attributes_template()

        if hasattr(self, "async_get_last_state"):
            state: State = await self.async_get_last_state()
            if state:
                self.async_restore_last_state(state.state, state.attributes)
                return

        if hasattr(self, "async_update"):
            await self.async_device_update(warning=False)

    async def async_will_remove_from_hass(self) -> None:
        """Also run when rename entity_id"""
        # self.device.setup_attrs.remove(self.attr)
        self.device.entities.pop(self.attr)

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
                self.device.available or self.customize.get('ignore_offline')
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


def update(orig_dict: dict, new_dict: dict):
    for k, v in new_dict.items():
        if isinstance(v, dict):
            orig_dict[k] = update(orig_dict.get(k, {}), v)
        elif isinstance(v, list):
            orig_dict[k] = orig_dict.get(k, []) + v
        else:
            orig_dict[k] = new_dict[k]
    return orig_dict
