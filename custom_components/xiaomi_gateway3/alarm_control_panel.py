"""Support for Xiaomi Gateway 3 alarm control panels."""

from functools import partial
import logging

from miio import DeviceException

from homeassistant.components.alarm_control_panel import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    SUPPORT_ALARM_TRIGGER,
    AlarmControlPanelEntity,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

from .core import utils
from .core.gateway3 import Gateway3
from .core.utils import DOMAIN
from .core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__name__)

XIAOMI_STATE_ALARM_DISARMED = 0
XIAOMI_STATE_ALARM_ARMED_HOME = 1
XIAOMI_STATE_ALARM_ARMED_AWAY = 2
XIAOMI_STATE_ALARM_ARMED_NIGHT = 3


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Xiaomi Gateway Alarm from a config entry."""
    entities = []
    gateway = hass.data[DOMAIN]['gateway_list'][0]
    cloud = hass.data[DOMAIN]['cloud_instance']
    entity = XiaomiGateway3Alarm(
        gateway,
        f"{gateway['name']} Alarm",
        cloud,
        config_entry.data.get("servers")
    )
    entities.append(entity)
    async_add_entities(entities, update_before_add=True)

class XiaomiGateway3Alarm(AlarmControlPanelEntity):
    """Representation of the XiaomiGatewayAlarm."""

    def __init__(
        self, gateway_device, gateway_name, cloud, server:list
    ):
        """Initialize the entity."""
        self._gateway = gateway_device
        self._name = gateway_name
        self._gateway_device_id = gateway_device['did']
        self._unique_id = f"{gateway_device['model']}-{gateway_device['mac']}"
        self._cloud_instance = cloud
        self._server = server[0]
        self._icon = "mdi:shield-home"
        self._available = None
        self._state = None

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._unique_id

    @property
    def device_id(self):
        """Return the device id of the gateway."""
        return self._gateway_device_id

    @property
    def device_info(self):
        """Return the device info of the gateway."""
        return {
            "identifiers": {(DOMAIN, self._gateway_device_id)},
        }

    @property
    def name(self):
        """Return the name of this entity, if any."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (SUPPORT_ALARM_ARM_AWAY
                | SUPPORT_ALARM_ARM_HOME
                | SUPPORT_ALARM_ARM_NIGHT
                # | SUPPORT_ALARM_TRIGGER
                )

    async def async_set_property_new(self, siid: int, piid: int, value):
        try:
            _LOGGER.info(f"Setting property for {self._name}.")
            did = self._gateway['did']
            p = [{'did': did, 'siid': siid, 'piid': piid, 'value': value}]
            if await self._cloud_instance.request_miot_api(self._server, '/prop/set', p):
                return True
            else:
                return False
        except DeviceException as ex:
            _LOGGER.error(f"Failed setting {self._name} 's property: siid {siid}, piid {piid}, value {value}: {ex}")
            return False

    async def async_get_property_new(self, siid: int, piid: int, multiparams : list = []):
        try:
            if not multiparams:
                _LOGGER.info(f"Control {self._name} by cloud.")
                did = self._gateway['did']
                p = [{'did': did, 'siid': siid, 'piid': piid}]
                results = await self._cloud_instance.request_miot_api(self._server, '/prop/get', p)
                return results
            else:
                did = self._gateway['did']
                results = await self._cloud_instance.request_miot_api(self._server, '/prop/get', multiparams)
                return results
        except DeviceException as ex:
            _LOGGER.error(f"Failed getting {self._name} 's property: {ex}")
            return None

    async def async_alarm_arm_away(self, code=None):
        """Turn on."""
        await self.async_set_property_new(
            3, 1, XIAOMI_STATE_ALARM_ARMED_AWAY
        )

    async def async_alarm_arm_home(self, code=None):
        """Turn on."""
        await self.async_set_property_new(
            3, 1, XIAOMI_STATE_ALARM_ARMED_HOME
        )

    async def async_alarm_arm_night(self, code=None):
        """Turn on."""
        await self.async_set_property_new(
            3, 1, XIAOMI_STATE_ALARM_ARMED_NIGHT
        )

    async def async_alarm_disarm(self, code=None):
        """Turn off."""
        await self.async_set_property_new(
            3, 1, XIAOMI_STATE_ALARM_DISARMED
        )

    async def async_update(self):
        """Fetch state from the device."""
        try:
            result = await self.async_get_property_new(3, 1)
            if result:
                state = result[0]['value']
                self._available = True
                if state == XIAOMI_STATE_ALARM_DISARMED:
                    self._state = STATE_ALARM_DISARMED
                elif state == XIAOMI_STATE_ALARM_ARMED_HOME:
                    self._state = STATE_ALARM_ARMED_HOME
                elif state == XIAOMI_STATE_ALARM_ARMED_AWAY:
                    self._state = STATE_ALARM_ARMED_AWAY
                elif state == XIAOMI_STATE_ALARM_ARMED_NIGHT:
                    self._state = STATE_ALARM_ARMED_NIGHT
                else:
                    _LOGGER.warning(
                        f"Gateway alarm state ({state}) doesn't match expected values."
                    )
                    self._state = None
            else:
                self._available = False
            _LOGGER.debug("State value: %s", self._state)
        except Exception as ex:
            self._available = False
            _LOGGER.error(f"Got exception while fetching the state: {ex}")
