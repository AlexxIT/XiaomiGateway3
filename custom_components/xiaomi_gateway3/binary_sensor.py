import asyncio
import time
from datetime import timedelta

from homeassistant.components.automation import ATTR_LAST_TRIGGERED
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import now

from . import DOMAIN
from .core.converters import Converter, GATEWAY
from .core.device import XDevice, XEntity
from .core.gateway import XGateway

SCAN_INTERVAL = timedelta(seconds=60)

CONF_INVERT_STATE = "invert_state"
CONF_OCCUPANCY_TIMEOUT = "occupancy_timeout"


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr == "motion" and device.model != "MS01":
            cls = XiaomiMotionSensor
        elif conv.attr == GATEWAY:
            cls = XiaomiGateway
        else:
            cls = XiaomiBinarySensor

        async_add_entities([cls(gateway, device, conv)])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


class XiaomiBinaryBase(XEntity, BinarySensorEntity):
    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            # support invert_state for sensor
            self._attr_is_on = not data[self.attr] \
                if self.customize.get(CONF_INVERT_STATE, False) \
                else data[self.attr]

        for k, v in data.items():
            if k in self.subscribed_attrs and k != self.attr:
                self._attr_extra_state_attributes[k] = v


class XiaomiBinarySensor(XiaomiBinaryBase, RestoreEntity):
    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        self._attr_is_on = state == STATE_ON
        for k, v in attrs.items():
            if k in self.subscribed_attrs:
                self._attr_extra_state_attributes[k] = v


class XiaomiGateway(XiaomiBinaryBase):
    @callback
    def async_update_available(self):
        # sensor state=connected when whole gateway available
        self._attr_is_on = self.gw.available


class XiaomiMotionSensor(XEntity, BinarySensorEntity):
    _default_delay = None
    _last_on = 0
    _last_off = 0
    _timeout_pos = 0
    _clear_task: asyncio.Task = None

    async def async_clear_state(self, delay: float):
        await asyncio.sleep(delay)

        self._last_off = time.time()
        self._timeout_pos = 0

        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def async_set_state(self, data: dict):
        assert data[self.attr] == True

        # don't trigger motion right after illumination
        ts = time.time()
        if ts - self._last_on < 1:
            return

        if self._clear_task:
            self._clear_task.cancel()

        self._attr_is_on = True
        self._attr_extra_state_attributes[ATTR_LAST_TRIGGERED] = \
            now().isoformat(timespec="seconds")
        self._last_on = ts

        # if customize of any entity will be changed from GUI - default value
        # for all motion sensors will be erased
        timeout = self.customize.get(CONF_OCCUPANCY_TIMEOUT, 90)
        if timeout:
            if isinstance(timeout, list):
                pos = min(self._timeout_pos, len(timeout) - 1)
                delay = timeout[pos]
                self._timeout_pos += 1
            else:
                delay = timeout

            if delay < 0 and ts + delay < self._last_off:
                delay *= 2

            self.debug(f"Extend delay: {delay} seconds")

            self._clear_task = self.hass.async_create_task(
                self.async_clear_state(abs(delay))
            )

        # repeat event from Aqara integration
        self.hass.bus.async_fire("xiaomi_aqara.motion", {
            "entity_id": self.entity_id
        })
