from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ALARM_TRIGGERED
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity, setup_entity
from .core.gateway import XGateway


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    def new_entity(gateway: XGateway, device: XDevice, conv: Converter) -> XEntity:
        return XiaomiAlarm(gateway, device, conv)

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup_entity(hass, config_entry, add_entities, new_entity))


# noinspection PyAbstractClass
class XiaomiAlarm(XEntity, AlarmControlPanelEntity):
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_state = data[self.attr]
        if data.get("alarm_trigger") is True:
            self._attr_state = STATE_ALARM_TRIGGERED

    async def async_alarm_disarm(self, code=None):
        await self.device_send({self.attr: "disarmed"})

    async def async_alarm_arm_home(self, code=None):
        await self.device_send({self.attr: "armed_home"})

    async def async_alarm_arm_away(self, code=None):
        await self.device_send({self.attr: "armed_away"})

    async def async_alarm_arm_night(self, code=None):
        await self.device_send({self.attr: "armed_night"})

    async def async_alarm_trigger(self, code=None):
        # example: code="5,3"  # 5 seconds, volume 3
        if code:
            await self.gw.alarm(code)
        else:
            await self.device_send({"alarm_trigger": True})

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)
