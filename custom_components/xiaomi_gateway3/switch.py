from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "switch"] = async_add_entities


class XSwitch(XEntity, SwitchEntity, RestoreEntity):
    def set_state(self, data: dict):
        self._attr_is_on = bool(data[self.attr])

    def get_state(self) -> dict:
        return {self.attr: self._attr_is_on}

    async def async_turn_on(self):
        self.device.write({self.attr: True})

    async def async_turn_off(self):
        self.device.write({self.attr: False})


XEntity.NEW["switch"] = XSwitch
