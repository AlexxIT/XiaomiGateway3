import asyncio

from homeassistant.components.light import *
from homeassistant.const import STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN
from .core.converters import ZIGBEE, MESH_GROUP_MODEL, Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway

CONF_DEFAULT_TRANSITION = 'default_transition'


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        elif device.type == ZIGBEE:
            entity = XiaomiZigbeeLight(gateway, device, conv)
        elif device.model == MESH_GROUP_MODEL:
            entity = XiaomiMeshGroup(gateway, device, conv)
        else:
            entity = XiaomiMeshLight(gateway, device, conv)
        async_add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiLight(XEntity, LightEntity, RestoreEntity):
    _attr_is_on = None

    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        for conv in device.converters:
            if conv.attr == ATTR_BRIGHTNESS:
                self._attr_supported_features |= (
                        SUPPORT_BRIGHTNESS | SUPPORT_TRANSITION
                )
            elif conv.attr == ATTR_COLOR_TEMP:
                self._attr_supported_features |= SUPPORT_COLOR_TEMP
                if hasattr(conv, "minm") and hasattr(conv, "maxm"):
                    self._attr_min_mireds = conv.minm
                    self._attr_max_mireds = conv.maxm
                elif hasattr(conv, "mink") and hasattr(conv, "maxk"):
                    self._attr_min_mireds = int(1000000 / conv.maxk)
                    self._attr_max_mireds = int(1000000 / conv.mink)

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_is_on = data[self.attr]
        # sometimes brightness and color_temp stored as string in Xiaomi DB
        if ATTR_BRIGHTNESS in data:
            self._attr_brightness = data[ATTR_BRIGHTNESS]
        if ATTR_COLOR_TEMP in data:
            self._attr_color_temp = data[ATTR_COLOR_TEMP]

    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        self._attr_is_on = state == STATE_ON
        self._attr_brightness = attrs.get(ATTR_BRIGHTNESS)
        self._attr_color_temp = attrs.get(ATTR_COLOR_TEMP)

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)


# noinspection PyAbstractClass
class XiaomiZigbeeLight(XiaomiLight):
    async def async_turn_on(self, **kwargs):
        if ATTR_TRANSITION in kwargs:
            tr = kwargs.pop(ATTR_TRANSITION)
        elif CONF_DEFAULT_TRANSITION in self.customize:
            tr = self.customize[CONF_DEFAULT_TRANSITION]
        else:
            tr = None

        if tr is not None:
            if kwargs:
                # For the Aqara bulb, it is important that the brightness
                # parameter comes before the color_temp parameter. Only this
                # way transition will work. So we use `kwargs.pop` func to set
                # the exact order of parameters.
                for k in (ATTR_BRIGHTNESS, ATTR_COLOR_TEMP):
                    if k in kwargs:
                        kwargs[k] = (kwargs.pop(k), tr)
            else:
                kwargs[ATTR_BRIGHTNESS] = (255, tr)

        if not kwargs:
            kwargs[self.attr] = True

        await self.device_send(kwargs)

    async def async_turn_off(self, **kwargs):
        if ATTR_TRANSITION in kwargs:
            tr = kwargs[ATTR_TRANSITION]
        elif CONF_DEFAULT_TRANSITION in self.customize:
            tr = self.customize[CONF_DEFAULT_TRANSITION]
        else:
            tr = None

        if tr is not None:
            await self.device_send({ATTR_BRIGHTNESS: (0, tr)})
        else:
            await self.device_send({self.attr: False})


# noinspection PyAbstractClass
class XiaomiMeshBase(XiaomiLight):
    async def async_turn_on(self, **kwargs):
        kwargs[self.attr] = True
        await self.device_send(kwargs)

    async def async_turn_off(self, **kwargs):
        kwargs[self.attr] = False
        await self.device_send(kwargs)


# noinspection PyAbstractClass
class XiaomiMeshLight(XiaomiMeshBase):
    @callback
    def async_set_state(self, data: dict):
        super().async_set_state(data)

        if "group" not in self.device.entities:
            return
        # convert light attr to group attr
        if self.attr in data:
            data["group"] = data.pop(self.attr)
        group = self.device.entities["group"]
        group.async_set_state(data)
        group.async_write_ha_state()


# noinspection PyAbstractClass
class XiaomiMeshGroup(XiaomiMeshBase):
    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        if not device.extra["childs"]:
            device.available = False
            return

        for did in device.extra["childs"]:
            child = gateway.devices[did]
            child.entities[self.attr] = self

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        if not self.device.extra["childs"]:
            return
        for did in self.device.extra["childs"]:
            child = self.gw.devices[did]
            child.entities.pop(self.attr)

    async def async_update(self):
        # To update a group - request an update of its children
        # update_ha_state for all child light entities
        try:
            childs = []
            for did in self.device.extra["childs"]:
                light = self.gw.devices[did].entities.get("light")
                childs.append(light.async_update_ha_state(True))
            if childs:
                await asyncio.gather(*childs)

        except Exception as e:
            self.debug("Can't update child states", exc_info=e)
