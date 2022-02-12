from homeassistant.components.alarm_control_panel import \
    SUPPORT_ALARM_ARM_AWAY, SUPPORT_ALARM_ARM_HOME, SUPPORT_ALARM_ARM_NIGHT, \
    SUPPORT_ALARM_TRIGGER, AlarmControlPanelEntity
from homeassistant.const import STATE_ALARM_TRIGGERED
from homeassistant.core import callback

from . import DOMAIN
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        else:
            entity = XiaomiAlarm(gateway, device, conv)
        async_add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiAlarm(XEntity, AlarmControlPanelEntity):
    _attr_code_arm_required = False
    _attr_supported_features = (
            SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY |
            SUPPORT_ALARM_ARM_NIGHT | SUPPORT_ALARM_TRIGGER
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
        await self.device_send({"alarm_trigger": True})

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)
