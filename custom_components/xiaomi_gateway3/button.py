from homeassistant.components.button import ButtonEntity

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "button"] = async_add_entities


class XButton(XEntity, ButtonEntity):
    async def async_press(self):
        self.device.write({self.attr: True})


XEntity.NEW["button"] = XButton
