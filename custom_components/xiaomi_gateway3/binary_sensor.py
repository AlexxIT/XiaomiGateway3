import asyncio
import time
from functools import cached_property

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.script import ATTR_LAST_TRIGGERED
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import utcnow

from .hass.entity import XEntity, XStatsEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "binary_sensor"] = async_add_entities


class XBinarySensor(XEntity, BinarySensorEntity, RestoreEntity):
    """Basic binary_sensor with invert_state support."""

    def set_state(self, data: dict):
        self._attr_is_on = not data[self.attr] if self.invert else data[self.attr]

    def get_state(self) -> dict:
        return {self.attr: not self._attr_is_on if self.invert else self._attr_is_on}

    @cached_property
    def invert(self) -> bool:
        return self.device.extra.get("invert_state", False)


class XGatewaySensor(XEntity, BinarySensorEntity):
    """Gateway connection available sensor with useful extra attributes."""

    def on_init(self):
        self.listen_attrs.add("available")
        self._attr_is_on = True
        self._attr_extra_state_attributes = {}

    def set_state(self, data: dict):
        if self.attr in data:
            self._attr_extra_state_attributes.update(data[self.attr])
        if "available" in data:
            self._attr_is_on = data["available"]

    @property
    def available(self):
        return True


class XBinaryStatsSensor(XStatsEntity, BinarySensorEntity):
    pass


class XMotionSensor(XEntity, BinarySensorEntity):
    """Smart motion sensor with custom occupancy_timeout."""
    _unrecorded_attributes = {ATTR_LAST_TRIGGERED}

    _attr_is_on: bool = False
    _last_on: float = 0
    _last_off: float = 0
    _timeout_pos: int = 0
    _clear_task: asyncio.Task = None

    def on_init(self):
        self._attr_extra_state_attributes = {}

    @cached_property
    def occupancy_timeout(self) -> list[float] | float:
        return self.device.extra.get("occupancy_timeout", 90)

    def set_state(self, data: dict):
        # fix 1.4.7_0115 heartbeat error (has motion in heartbeat)
        if "battery" in data:
            return

        assert data[self.attr] is True

        # don't trigger motion right after illumination
        ts = time.time()
        if ts - self._last_on < 1:
            return

        if self._clear_task:
            self._clear_task.cancel()

        self._attr_is_on = True
        self._attr_extra_state_attributes[ATTR_LAST_TRIGGERED] = utcnow()
        self._last_on = ts

        if timeout := self.occupancy_timeout:
            if isinstance(timeout, list):
                pos = min(self._timeout_pos, len(timeout) - 1)
                delay = timeout[pos]
                self._timeout_pos += 1
            else:
                delay = timeout

            if delay < 0 and ts + delay < self._last_off:
                delay *= 2

            self._clear_task = self.hass.loop.create_task(
                self.async_clear_state(abs(delay))
            )

        # repeat event from Aqara integration
        self.hass.bus.async_fire("xiaomi_aqara.motion", {"entity_id": self.entity_id})

    async def async_clear_state(self, delay: float):
        await asyncio.sleep(delay)

        self._last_off = time.time()
        self._timeout_pos = 0

        self._attr_is_on = False
        self._async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._clear_task:
            self._clear_task.cancel()

        if self._attr_is_on:
            self._attr_is_on = False
            self._async_write_ha_state()

        await super().async_will_remove_from_hass()


XEntity.NEW["binary_sensor"] = XBinarySensor
XEntity.NEW["binary_sensor.attr.gateway"] = XGatewaySensor
XEntity.NEW["binary_sensor.attr.motion"] = XMotionSensor
XEntity.NEW["binary_sensor.attr.ble"] = XBinaryStatsSensor
XEntity.NEW["binary_sensor.attr.matter"] = XBinaryStatsSensor
XEntity.NEW["binary_sensor.attr.mesh"] = XBinaryStatsSensor
XEntity.NEW["binary_sensor.attr.zigbee"] = XBinaryStatsSensor
