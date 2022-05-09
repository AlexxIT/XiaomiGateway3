import asyncio
from asyncio import Task
from datetime import datetime, timedelta, timezone

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import *
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


UNITS = {
    "battery": PERCENTAGE,
    "humidity": PERCENTAGE,
    # zb light and motion and ble flower - lux
    "illuminance": LIGHT_LUX,
    "power": POWER_WATT,
    "voltage": ELECTRIC_POTENTIAL_VOLT,
    "current": ELECTRIC_CURRENT_AMPERE,
    "pressure": PRESSURE_HPA,
    "temperature": TEMP_CELSIUS,
    "energy": ENERGY_KILO_WATT_HOUR,
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

# https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
STATE_CLASSES = {
    "energy": SensorStateClass.TOTAL_INCREASING,
}


class XiaomiBaseSensor(XEntity, SensorEntity):
    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
        XEntity.__init__(self, gateway, device, conv)

        if self.attr in UNITS:
            # by default all sensors with units is measurement sensors
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UNITS[self.attr]

        if self.attr in STATE_CLASSES:
            self._attr_state_class = STATE_CLASSES[self.attr]

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_native_value = data[self.attr]
        for k, v in data.items():
            if k in self.subscribed_attrs and k != self.attr:
                self._attr_extra_state_attributes[k] = v


class XiaomiSensor(XiaomiBaseSensor, RestoreEntity):
    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_extra_state_attributes["native_value"] = data[self.attr]
        XiaomiBaseSensor.async_set_state(self, data)

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        """Restore previous state."""
        self._attr_native_value = attrs.get("native_value", state)
        for k, v in attrs.items():
            if k in self.subscribed_attrs or k == "native_value":
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
        self._attr_extra_state_attributes["available"] = self.available

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        data = {"available": self.available}
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


class XiaomiAction(XiaomiBaseSensor):
    _attr_native_value = ""
    orig_attrs: dict = None
    clear_task: Task = None

    async def clear_state(self):
        await asyncio.sleep(.3)

        self._attr_native_value = ""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await XEntity.async_added_to_hass(self)
        self.orig_attrs = self._attr_extra_state_attributes

    async def async_will_remove_from_hass(self):
        if self.clear_task:
            self.clear_task.cancel()

        if self.native_value != "":
            self._attr_native_value = ""
            self.async_write_ha_state()

        await XEntity.async_will_remove_from_hass(self)

    @callback
    def async_set_state(self, data: dict):
        # fix 1.4.7_0115 heartbeat error (has button in heartbeat)
        if "battery" in data or self.attr not in data or not self.hass:
            return

        if self.clear_task:
            self.clear_task.cancel()

        self._attr_native_value = data[self.attr]
        self._attr_extra_state_attributes = {**self.orig_attrs, **data}

        # repeat event from Aqara integration
        self.hass.bus.async_fire("xiaomi_aqara.click", {
            "entity_id": self.entity_id, "click_type": self._attr_state
        })

        self.clear_task = self.hass.loop.create_task(self.clear_state())
