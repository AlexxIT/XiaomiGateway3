import asyncio

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .hass.entity import XEntity, XStatsEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "sensor"] = async_add_entities


class XSensor(XEntity, SensorEntity, RestoreEntity):
    def set_state(self, data: dict):
        self._attr_native_value = data[self.attr]

    def get_state(self) -> dict:
        return {self.attr: self._attr_native_value}


class XStatsSensor(XStatsEntity, SensorEntity):
    pass


class XActionSensor(XEntity, SensorEntity):
    _attr_native_value = ""
    native_attrs: dict = None
    clear_task: asyncio.Task = None

    def set_state(self, data: dict):
        # fix 1.4.7_0115 heartbeat error (has button in heartbeat)
        if "battery" in data or not self.hass:
            return

        if self.clear_task:
            self.clear_task.cancel()

        self._attr_native_value = data[self.attr]
        self._attr_extra_state_attributes = data

        # repeat event from Aqara integration
        self.hass.bus.async_fire(
            "xiaomi_aqara.click",
            {"entity_id": self.entity_id, "click_type": self._attr_native_value},
        )

        self.clear_task = self.hass.loop.create_task(self.clear_state())

    async def clear_state(self):
        await asyncio.sleep(0.5)
        self._attr_native_value = ""
        self._async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self.clear_task:
            self.clear_task.cancel()

        if self._attr_native_value:
            self._attr_native_value = ""
            self._async_write_ha_state()

        await super().async_will_remove_from_hass()


XEntity.NEW["sensor"] = XSensor
XEntity.NEW["sensor.attr.action"] = XActionSensor
XEntity.NEW["sensor.attr.ble"] = XStatsSensor
XEntity.NEW["sensor.attr.matter"] = XStatsSensor
XEntity.NEW["sensor.attr.mesh"] = XStatsSensor
XEntity.NEW["sensor.attr.zigbee"] = XStatsSensor
