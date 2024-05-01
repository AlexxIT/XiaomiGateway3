import asyncio
import time
from functools import cached_property

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .core.gate.base import XGateway
from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "light"] = async_add_entities


class XLight(XEntity, LightEntity, RestoreEntity):
    def on_init(self):
        self._attr_color_mode = ColorMode.ONOFF
        modes = set()

        for conv in self.device.converters:
            if conv.attr == ATTR_BRIGHTNESS:
                self.listen_attrs.add(conv.attr)
                self._attr_color_mode = ColorMode.BRIGHTNESS
            elif conv.attr == ATTR_COLOR_TEMP:
                self.listen_attrs.add(conv.attr)
                self._attr_color_mode = ColorMode.COLOR_TEMP
                modes.add(ColorMode.COLOR_TEMP)
                if hasattr(conv, "minm") and hasattr(conv, "maxm"):
                    self._attr_min_mireds = conv.minm
                    self._attr_max_mireds = conv.maxm
                elif hasattr(conv, "mink") and hasattr(conv, "maxk"):
                    self._attr_min_mireds = int(1000000 / conv.maxk)
                    self._attr_max_mireds = int(1000000 / conv.mink)
            elif conv.attr == ATTR_HS_COLOR:
                self.listen_attrs.add(conv.attr)
                modes.add(ColorMode.HS)
            elif conv.attr == ATTR_COLOR_MODE:
                self.listen_attrs.add(conv.attr)
            elif conv.attr == ATTR_EFFECT and hasattr(conv, "map"):
                self.listen_attrs.add(conv.attr)
                self._attr_supported_features |= LightEntityFeature.EFFECT
                self._attr_effect_list = list(conv.map.values())

        self._attr_supported_color_modes = modes if modes else {self._attr_color_mode}

    def set_state(self, data: dict):
        # we turn_on light on any brightness or color_temp data without light state
        # fix https://github.com/AlexxIT/XiaomiGateway3/issues/1335
        if ATTR_BRIGHTNESS in data:
            self._attr_brightness = data[ATTR_BRIGHTNESS]
            data.setdefault(self.attr, True)
        if ATTR_COLOR_TEMP in data:
            self._attr_color_temp = data[ATTR_COLOR_TEMP]
            self._attr_color_mode = ColorMode.COLOR_TEMP
            data.setdefault(self.attr, True)
        if self.attr in data:
            self._attr_is_on = bool(data[self.attr])
        if ATTR_HS_COLOR in data:
            self._attr_hs_color = data[ATTR_HS_COLOR]
            self._attr_color_mode = ColorMode.HS
        if ATTR_COLOR_MODE in data:
            self._attr_color_mode = ColorMode(data[ATTR_COLOR_MODE])
        if ATTR_EFFECT in data:
            self._attr_effect = data[ATTR_EFFECT]

    def get_state(self) -> dict:
        return {
            self.attr: self._attr_is_on,
            ATTR_BRIGHTNESS: self._attr_brightness,
            ATTR_COLOR_TEMP: self._attr_color_temp,
        }

    async def async_turn_on(self, **kwargs):
        self.device.write(kwargs if kwargs else {self.attr: True})

    async def async_turn_off(self, **kwargs):
        self.device.write({self.attr: False})


class XZigbeeLight(XLight):
    def on_init(self):
        super().on_init()

        for conv in self.device.converters:
            if conv.attr == ATTR_TRANSITION:
                self._attr_supported_features |= LightEntityFeature.TRANSITION

    @cached_property
    def default_transition(self) -> float | None:
        return self.device.extra.get("default_transition")

    async def async_turn_on(self, transition: int = None, **kwargs):
        if self.default_transition is not None and transition is None:
            transition = self.default_transition

        if transition is not None:
            # important to sort args in right order, transition should be first
            kwargs = {ATTR_TRANSITION: transition} | kwargs

        self.device.write(kwargs if kwargs else {self.attr: True})

        # fix Philips Hue with polling
        if self._attr_should_poll and (not kwargs or transition):
            await asyncio.sleep(transition or 1)

    async def async_turn_off(self, transition: int = None, **kwargs):
        if self.default_transition is not None and transition is None:
            transition = self.default_transition

        if transition is not None:
            kwargs.setdefault(ATTR_BRIGHTNESS, 0)
            kwargs = {ATTR_TRANSITION: transition} | kwargs

        self.device.write(kwargs if kwargs else {self.attr: False})

        # fix Philips Hue with polling
        if self._attr_should_poll and (not kwargs or transition):
            await asyncio.sleep(transition or 1)


class XLightGroup(XLight):
    wait_update: bool = False

    def childs(self):
        return [
            XGateway.devices[did]
            for did in self.device.extra.get("childs", [])
            if did in XGateway.devices
        ]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for child in self.childs():
            child.add_listener(self.forward_child_update)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        for child in self.childs():
            child.remove_listener(self.forward_child_update)

    def forward_child_update(self, data: dict):
        self.wait_update = False
        self.on_device_update(data)

    async def wait_update_with_timeout(self, delay: float):
        # thread safe wait logic, because `forward_child_update` and `async_turn_on`
        # can be called from different threads and we can't use asyncio.Event here
        wait_unil = time.time() + delay
        while self.wait_update:
            await asyncio.sleep(0.5)
            if time.time() > wait_unil:
                break

    async def async_turn_on(self, **kwargs):
        self.wait_update = True
        await super().async_turn_on(**kwargs)
        await self.wait_update_with_timeout(10.0)

    async def async_turn_off(self, **kwargs):
        self.wait_update = True
        await super().async_turn_off(**kwargs)
        await self.wait_update_with_timeout(10.0)


XEntity.NEW["light"] = XLight
XEntity.NEW["light.type.zigbee"] = XZigbeeLight
XEntity.NEW["light.type.group"] = XLightGroup
