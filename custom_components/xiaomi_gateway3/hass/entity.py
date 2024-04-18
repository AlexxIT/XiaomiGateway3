import logging
from datetime import datetime, timezone
from functools import cached_property
from typing import TYPE_CHECKING, Callable

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    CONNECTION_NETWORK_MAC,
    CONNECTION_ZIGBEE,
)
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoredExtraData
from homeassistant.helpers.template import Template

from .entity_description import setup_entity_description
from ..core.const import DOMAIN, GATEWAY, ZIGBEE, BLE, MESH
from ..core.converters.base import BaseConv

if TYPE_CHECKING:
    from ..core.converters.base import BaseConv
    from ..core.device import XDevice

_LOGGER = logging.getLogger(__package__)


def attr_human_name(attr: str):
    # this words always uppercase
    if attr in ("ble", "led", "rssi", "usb"):
        return attr.upper()
    return attr.replace("_", " ").title()


class XEntity(Entity):
    ADD: dict[str, AddEntitiesCallback] = {}  # key: "config_entry_id+domain"
    NEW: dict[str, Callable] = {}  # key: "domain.attr" or "domain"

    def __init__(self, device: "XDevice", conv: "BaseConv"):
        self.device = device
        self.attr = conv.attr

        self.listen_attrs: set = {conv.attr}

        if device.type == GATEWAY:
            connections = {(CONNECTION_NETWORK_MAC, device.extra["mac"])}
            if mac2 := device.extra.get("mac2"):
                connections.add((CONNECTION_NETWORK_MAC, mac2))
        elif device.type == ZIGBEE:
            connections = {(CONNECTION_ZIGBEE, device.extra["ieee"])}
        elif device.type in (BLE, MESH):
            connections = {(CONNECTION_BLUETOOTH, device.extra["mac"])}
        else:
            connections = None

        if device.type != GATEWAY:
            via_device = (DOMAIN, device.gateways[0].device.uid)
        else:
            via_device = None

        self._attr_available = device.available
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.uid)},
            connections=connections,
            manufacturer=device.extra.get("market_brand"),
            name=device.human_name,
            model=device.human_model,
            sw_version=device.firmware,
            hw_version=device.extra.get("hw_ver"),
            via_device=via_device,
        )
        self._attr_has_entity_name = True
        self._attr_name = attr_human_name(conv.attr)
        self._attr_should_poll = False
        self._attr_unique_id = f"{device.uid}_{conv.attr}"

        setup_entity_description(self, conv)

        if entity_name := device.extra.get("entity_name"):
            if entity_name.endswith(conv.attr):
                self.entity_id = f"{conv.domain}.{entity_name}"
            else:
                self.entity_id = f"{conv.domain}.{entity_name}_{conv.attr}"
        else:
            self.entity_id = f"{conv.domain}.{device.uid}_{conv.attr}"

        self.on_init()

    @cached_property
    def domain(self) -> str:
        return type(self).__module__.rsplit(".", 1)[1]

    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        # filter None values
        if state := {k: v for k, v in self.get_state().items() if v is not None}:
            return RestoredExtraData(state)
        return None

    def debug(self, msg: str):
        _LOGGER.debug({"msg": msg, "entity": self.entity_id})

    async def async_added_to_hass(self) -> None:
        # self.debug("async_added_to_hass")
        self.device.add_listener(self.on_device_update)

        if hasattr(self, "attributes_template"):
            self.render_attributes_template()

        if hasattr(self, "async_get_last_extra_data"):
            data: RestoredExtraData = await self.async_get_last_extra_data()
            if data and self.listen_attrs & data.as_dict().keys():
                self.set_state(data.as_dict())

    def render_attributes_template(self):
        try:
            template: Template = getattr(self, "attributes_template")
            gw = self.device.gateways[0]
            attrs = template.async_render(
                {"attr": self.attr, "device": self.device, "gateway": gw.device}
            )
            if not isinstance(attrs, dict):
                return
            if hasattr(self, "_attr_extra_state_attributes"):
                self._attr_extra_state_attributes.update(attrs)
            else:
                self._attr_extra_state_attributes = attrs
        except Exception as e:
            _LOGGER.warning("Can't render attributes", exc_info=e)

    async def async_will_remove_from_hass(self) -> None:
        # self.debug("async_will_remove_from_hass")
        self.device.remove_listener(self.on_device_update)

    # async def async_removed_from_registry(self) -> None:
    #     self.debug("async_removed_from_registry")

    async def async_update(self):
        # for manual update via service `homeassistant.update_entity`
        # or via converter `entity={"poll": True}`
        self.device.read(self.listen_attrs)

    def on_init(self):
        """Run on class init."""

    def on_device_update(self, data: dict):
        state_change = False

        if "available" in data:
            self._attr_available = data["available"]
            state_change = True

        if self.listen_attrs & data.keys():
            self.set_state(data)
            state_change = True

        if state_change and self.hass:
            # _LOGGER.debug(f"{self.entity_id} | async_write_ha_state")
            self._async_write_ha_state()

    def set_state(self, data: dict):
        """Run on data from device."""
        self._attr_state = data[self.attr]

    def get_state(self) -> dict:
        """Run before entity remove if entity is subclass from RestoreEntity."""


class XStatsEntity(XEntity):
    _unrecorded_attributes = {"device", "msg_received", "msg_missed"}

    # binary_sensor and sensor support simultaneously
    _attr_is_on: bool
    _attr_native_value: datetime

    last_seq: int = None

    def on_init(self):
        self._attr_available = True
        self._attr_is_on = self.device.available
        self._attr_extra_state_attributes = {"device": self.device.as_dict()}

    def on_device_update(self, data: dict):
        state_change = False

        if "available" in data:
            self._attr_is_on = data["available"]
            state_change = True

        if ts := data.get(self.attr):
            self._attr_native_value = datetime.fromtimestamp(ts, timezone.utc)

            if "msg_received" in self._attr_extra_state_attributes:
                self._attr_extra_state_attributes["msg_received"] += 1
            else:
                self._attr_extra_state_attributes["msg_received"] = 1

            if (seq := self.device.extra.get("seq")) is not None:
                if self.last_seq is not None:
                    miss = (seq - self.last_seq - 1) & 0xFF
                    if 0 < miss < 0xF0:
                        self._attr_extra_state_attributes["msg_missed"] += 1
                else:
                    self._attr_extra_state_attributes["msg_missed"] = 0
                self.last_seq = seq

            state_change = True

        elif ts == 0:
            state_change = True

        if state_change and self.hass:
            self._attr_extra_state_attributes["device"] = self.device.as_dict()
            self._async_write_ha_state()
