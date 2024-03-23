from homeassistant.components.text import TextEntity

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "text"] = async_add_entities


class XText(XEntity, TextEntity):
    _attr_native_value = None

    def set_state(self, data: dict):
        self._attr_native_value = data[self.attr]

    def get_state(self) -> dict:
        return {self.attr: self._attr_native_value}

    async def async_set_value(self, value: str):
        self.device.write({self.attr: value})


XEntity.NEW["text"] = XText
