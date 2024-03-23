from homeassistant.components.number import NumberEntity, DEFAULT_STEP, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "number"] = async_add_entities


class XNumber(XEntity, NumberEntity, RestoreEntity):
    _attr_mode = NumberMode.BOX

    def on_init(self):
        conv = next(i for i in self.device.converters if i.attr == self.attr)

        multiply: float = getattr(conv, "multiply", 1)

        if hasattr(conv, "min"):
            self._attr_native_min_value = conv.min * multiply
        if hasattr(conv, "max"):
            self._attr_native_max_value = conv.max * multiply
        if hasattr(conv, "step") or hasattr(conv, "multiply"):
            self._attr_native_step = getattr(conv, "step", DEFAULT_STEP) * multiply

    def set_state(self, data: dict):
        self._attr_native_value = data[self.attr]

    def get_state(self) -> dict:
        return {self.attr: self._attr_native_value}

    async def async_set_native_value(self, value: float) -> None:
        self.device.write({self.attr: value})


XEntity.NEW["number"] = XNumber
