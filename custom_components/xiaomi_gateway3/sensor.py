import asyncio
from asyncio import Task
from datetime import datetime, timedelta, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN
from .core.converters import Converter, STAT_GLOBALS
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass, entry, add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        elif conv.attr == "action":
            entity = XiaomiAction(gateway, device, conv)
        elif conv.attr in STAT_GLOBALS:
            entity = XiaomiStats(gateway, device, conv)
        else:
            entity = XiaomiSensor(gateway, device, conv)
        add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][entry.entry_id]
    gw.add_setup(__name__, setup)


# this class do nothing in Hass 2021.9 and more, and fix sensors in Hass 2021.7
class Support20217:
    @property
    def _attr_native_value(self):
        return self._attr_state

    @_attr_native_value.setter
    def _attr_native_value(self, value):
        self._attr_state = value


class XiaomiBaseSensor(XEntity, SensorEntity, Support20217):
    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_native_value = data[self.attr]
        for k, v in data.items():
            if k in self.subscribed_attrs and k != self.attr:
                self._attr_extra_state_attributes[k] = v


class XiaomiSensor(XiaomiBaseSensor, RestoreEntity):
    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        """Restore previous state."""
        self._attr_native_value = state
        for k, v in attrs.items():
            if k in self.subscribed_attrs:
                self._attr_extra_state_attributes[k] = v

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)


class XiaomiStats(XiaomiBaseSensor):
    @property
    def available(self):
        return True

    @callback
    def async_update_available(self):
        super().async_update_available()

        self._attr_extra_state_attributes["available"] = self._attr_available

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        data = {"available": self._attr_available}
        if self.device.decode_ts:
            data[self.attr] = datetime.fromtimestamp(
                self.device.decode_ts, timezone.utc
            )
        if self.device.nwk:
            data["ieee"] = self.device.mac
            data["nwk"] = self.device.nwk
        else:
            data["mac"] = self.device.mac

        self.async_set_state(data)


class XiaomiAction(XEntity):
    _attr_state = ""
    _combined_attrs: dict = None
    _clear_task: Task = None

    @property
    def extra_state_attributes(self):
        return self._combined_attrs or self._attr_extra_state_attributes

    async def async_clear_state(self):
        await asyncio.sleep(.3)

        self._attr_state = ""
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._clear_task:
            self._clear_task.cancel()

        if self._attr_state != "":
            self._attr_state = ""
            self.async_write_ha_state()

        await super().async_will_remove_from_hass()

    @callback
    def async_set_state(self, data: dict):
        # fix 1.4.7_0115 heartbeat error (has button in heartbeat)
        if "battery" in data or self.attr not in data or not self.hass:
            return

        if self._clear_task:
            self._clear_task.cancel()

        self._attr_state = data[self.attr]
        self._combined_attrs = {**self._attr_extra_state_attributes, **data}

        # repeat event from Aqara integration
        self.hass.bus.async_fire("xiaomi_aqara.click", {
            "entity_id": self.entity_id, "click_type": self._attr_state
        })

        self._clear_task = self.hass.loop.create_task(self.async_clear_state())
