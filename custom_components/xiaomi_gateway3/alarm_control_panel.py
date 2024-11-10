import re

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.restore_state import RestoreEntity

from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "alarm_control_panel"] = async_add_entities


if (MAJOR_VERSION, MINOR_VERSION) >= (2024, 11):
    from homeassistant.components.alarm_control_panel import AlarmControlPanelState

    class XAlarmControlBase(XEntity, AlarmControlPanelEntity):
        mode: str = None
        trigger: bool = False

        def set_state(self, data: dict):
            if self.attr in data:
                self.mode = data[self.attr]
            if "alarm_trigger" in data:
                self.trigger = data["alarm_trigger"]

            self._attr_alarm_state = AlarmControlPanelState(
                "triggered" if self.trigger else self.mode
            )

        def get_state(self) -> dict:
            return {self.attr: self._attr_alarm_state}

else:
    class XAlarmControlBase(XEntity, AlarmControlPanelEntity):
        mode: str = None
        trigger: bool = False

        def set_state(self, data: dict):
            if self.attr in data:
                self.mode = data[self.attr]
            if "alarm_trigger" in data:
                self.trigger = data["alarm_trigger"]

            self._attr_state = "triggered" if self.trigger else self.mode

        def get_state(self) -> dict:
            return {self.attr: self._attr_state}


class XAlarmControlPanel(XAlarmControlBase, RestoreEntity):
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    def on_init(self):
        # TODO: test alarm disable
        self.listen_attrs.add("alarm_trigger")

    async def async_alarm_disarm(self, code=None):
        if self.trigger:
            self.device.write({"alarm_trigger": False})
        else:
            self.device.write({self.attr: "disarmed"})

    async def async_alarm_arm_home(self, code=None):
        self.device.write({self.attr: "armed_home"})

    async def async_alarm_arm_away(self, code=None):
        self.device.write({self.attr: "armed_away"})

    async def async_alarm_arm_night(self, code=None):
        self.device.write({self.attr: "armed_night"})

    async def async_alarm_trigger(self, code: str = None):
        """code = `123,1` (duration in seconds + volume = 1-3)."""
        if code is None:
            self.device.write({"alarm_trigger": True})
            return

        params = (
            f"start_alarm,{code}" if re.match(r"^\d+,[123]$", code) else "stop_alarm"
        )
        await self.device.send_gateway.mqtt.publish(
            "miio/command", {"_to": 1, "method": "local.status", "params": params}
        )


XEntity.NEW["alarm_control_panel"] = XAlarmControlPanel
