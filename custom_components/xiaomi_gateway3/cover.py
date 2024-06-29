from homeassistant.components.cover import CoverEntity
from homeassistant.const import STATE_OPENING, STATE_CLOSING
from homeassistant.helpers.restore_state import RestoreEntity

from .core.gate.base import XGateway
from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "cover"] = async_add_entities


class XCover(XEntity, CoverEntity, RestoreEntity):
    _attr_is_closed = None

    def on_init(self):
        # update state only for this attrs
        self.listen_attrs = {"position", "run_state"}

    def set_state(self, data: dict):
        if "position" in data:
            self._attr_current_cover_position = data["position"]
            # https://github.com/AlexxIT/XiaomiGateway3/issues/771
            self._attr_is_closed = self._attr_current_cover_position <= 2

        if "run_state" in data:
            self._attr_state = data["run_state"]
            self._attr_is_opening = self._attr_state == STATE_OPENING
            self._attr_is_closing = self._attr_state == STATE_CLOSING

    def get_state(self) -> dict:
        return {
            "position": self._attr_current_cover_position,
            "run_state": self._attr_state,
        }

    async def async_open_cover(self, **kwargs):
        self.device.write({self.attr: "open"})

    async def async_close_cover(self, **kwargs):
        self.device.write({self.attr: "close"})

    async def async_stop_cover(self, **kwargs):
        self.device.write({self.attr: "stop"})

    async def async_set_cover_position(self, position: int, **kwargs):
        self.device.write({"position": position})


class XCoverGroup(XCover):
    def childs(self):
        return [
            XGateway.devices[did]
            for did in self.device.extra.get("childs", [])
            if did in XGateway.devices
        ]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for child in self.childs():
            child.add_listener(self.device.dispatch)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        for child in self.childs():
            child.remove_listener(self.device.dispatch)


XEntity.NEW["cover"] = XCover
XEntity.NEW["cover.type.group"] = XCoverGroup
