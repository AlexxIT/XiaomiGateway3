from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN
from .core import utils, ezsp
from .core.converters import Converter
from .core.device import XDevice, RE_DID
from .core.entity import XEntity, setup_entity
from .core.gateway import XGateway


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    def new_entity(gateway: XGateway, device: XDevice, conv: Converter) -> XEntity:
        if conv.attr == "command":
            return CommandSelect(gateway, device, conv)
        elif conv.attr == "data":
            return DataSelect(gateway, device, conv)
        else:
            return XiaomiSelect(gateway, device, conv)

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup_entity(hass, config_entry, add_entities, new_entity))


# noinspection PyAbstractClass
class XiaomiSelectBase(XEntity, SelectEntity):
    _attr_current_option: str = None

    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)

        if hasattr(conv, "map"):
            self._attr_options = list(conv.map.values())

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_current_option = data[self.attr]


# noinspection PyAbstractClass
class XiaomiSelect(XiaomiSelectBase, RestoreEntity):
    @callback
    def async_restore_last_state(self, state: str, attrs: dict):
        self._attr_current_option = state

    async def async_select_option(self, option: str):
        await self.device_send({self.attr: option})

    async def async_update(self):
        await self.device_read(self.subscribed_attrs)


CMD_PAIR = "pair"  # zigbee_pain
CMD_BIND = "bind"  # zigbee_bind
CMD_OTA = "ota"  # zigbee_ota
CMD_CONFIG = "config"  # zigbee_config
CMD_PARENTSCAN = "parentscan"  # zigbee_parent_scan
CMD_FWLOCK = "firmwarelock"  # gateway_firmware_lock
CMD_REBOOT = "reboot"  # gateway_reboot
CMD_FTP = "ftp"  # gateway_run_ftp
CMD_FLASHZB = "flashzb"  # zigbee_flash_chip
CMD_OPENMIIO_RELOAD = "openmiio_reload"


# noinspection PyAbstractClass
class CommandSelect(XEntity, SelectEntity):
    _attr_current_option = None
    _attr_device_class = "command"
    _attr_translation_key = "command"

    def __init__(self, gateway: "XGateway", device: XDevice, conv: Converter):
        super().__init__(gateway, device, conv)
        if device.model == "lumi.gateway.mgl03":
            self._attr_options = [
                CMD_PAIR,
                CMD_BIND,
                CMD_OTA,
                CMD_CONFIG,
                CMD_PARENTSCAN,
                CMD_FLASHZB,
                CMD_FWLOCK,
                CMD_REBOOT,
                CMD_FTP,
                CMD_OPENMIIO_RELOAD,
            ]
        else:
            self._attr_options = [
                CMD_PAIR,
                CMD_BIND,
                CMD_OTA,
                CMD_CONFIG,
                CMD_PARENTSCAN,
                CMD_REBOOT,
                CMD_FTP,
                CMD_OPENMIIO_RELOAD,
            ]

    @callback
    def async_set_state(self, data: dict):
        if self.attr in data:
            self._attr_current_option = data[self.attr]

    async def async_select_option(self, option: str) -> None:
        # clear select.data
        self.device.update({"data": None})

        if option == CMD_PAIR:
            await self.device_send({"pair": True})
        elif option in (CMD_BIND, CMD_CONFIG, CMD_OTA, CMD_FLASHZB):
            self.device.update({"command": option})
        elif option == CMD_FWLOCK:
            lock = await self.gw.gw3_read_lock()
            self.device.update({"command": option, "lock": lock})
        elif option in (CMD_FTP, CMD_REBOOT, CMD_OPENMIIO_RELOAD):
            ok = await self.gw.telnet_send(option)
            self.device.update({"command": "ok", "value": ok})
        elif option == CMD_PARENTSCAN:
            await self.gw.z3_run_parent_scan()
            self.device.update({"command": "ok", "value": True})


OPT_ENABLED = "enabled"
OPT_DISABLED = "disabled"
OPT_UNKNOWN = "unknown"
OPT_OK = "ok"
OPT_ERROR = "error"
OPT_JOIN = "permit_join"
OPT_STOP_JOIN = "stop_join"
OPT_CANCEL = "cancel"
OPT_KEY_SECURE = "key_secure"
OPT_KEY_LEGACY = "key_legacy"
OPT_NO_FIRMWARE = "no_firmware"
OPT_BIND = "bind"
OPT_UNBIND = "unbind"
OPT_NO_DEVICES = "no_devices"
OPT_ORIGINAL = "original"
OPT_CUSTOM = "custom"


# noinspection PyAbstractClass,PyUnusedLocal
class DataSelect(XEntity, SelectEntity):
    _attr_current_option = None
    _attr_device_class = "data"
    _attr_options = None
    _attr_translation_key = "data"
    step_id = None
    kwargs = None

    def set_options(self, option: str = None, options: list = None):
        """Change current option with options list dynamically."""
        # always change to None first time
        self._attr_current_option = None

        if option:
            self._attr_options = options or [option]
            # important to change current option with delay after options
            self.hass.async_create_task(self.async_set_current(option))
        else:
            # better not leave options list empty
            self._attr_options = options or []

    async def async_set_current(self, option: str):
        """Delayed update current option."""
        self._attr_current_option = option
        self.async_write_ha_state()

    def set_devices(self, feature: str):
        """Set options list with devices list."""
        devices = [f"{d.mac}: {d.name}" for d in self.gw.filter_devices(feature)]
        if devices:
            self.set_options(None, devices)
        else:
            self.set_options(OPT_NO_DEVICES)

    def set_end(self, option: str):
        self.set_options(option)
        self.device.update({"command": None})

    ###########################################################################

    @callback
    def async_set_state(self, data: dict):
        """Can process:
        - command step, done by user from another select
        - event step, done by receiving some data from gateway
        """
        if "command" in data:
            self.step_id = data["command"]
            func = getattr(self, f"step_command_{self.step_id}", None)
        else:
            self.step_id = next(k for k in self.subscribed_attrs if k in data)
            data = data[self.step_id]
            func = getattr(self, f"step_event_{self.step_id}", None)

        if func:
            func(data)

    async def async_select_option(self, option: str) -> None:
        """Can process user step, done by user from this select"""
        coro = getattr(self, f"step_user_{self.step_id}", None)
        if coro:
            await coro(option)

    ###########################################################################

    def step_event_data(self, value: str):
        # update select.data value from outside
        self.set_options(value)

    def step_event_pair(self, value: bool):
        if value:
            self.set_options(OPT_JOIN, [OPT_JOIN, OPT_CANCEL])
            # change select.command
            self.device.update({"command": CMD_PAIR})
        else:
            # clear select.command
            self.device.update({"command": None})

    async def step_user_pair(self, option: str):
        assert option == OPT_CANCEL
        await self.device_send({"pair": False})

    def step_event_discovered_mac(self, value: str):
        self.set_options(f"Discovered: 0x{value:>016s}")

    def step_event_pair_command(self, value: dict):
        secure = value["install_code"]
        option = OPT_KEY_SECURE if secure else OPT_KEY_LEGACY
        self.set_options(option, self.options + [option])

    def step_event_added_device(self, value: dict):
        option = f"Paired: {value['model']}"
        self.set_options(option, self.options + [option])

    def step_event_remove_did(self, value: str):
        assert RE_DID.search(value)
        device = self.gw.devices.get(value)
        utils.remove_device(self.hass, device)
        self.set_end(f"Removed: {value[5:]}")

    def step_event_ota_progress(self, value: int):
        self.set_options(f"Update progress: {value}%")

    def step_command_config(self, value: dict):
        self.set_devices("zigbee")

    async def step_user_config(self, option: str):
        did = "lumi." + option[:18].lstrip("0x")
        device = self.gw.devices.get(did)
        await self.gw.silabs_rejoin(device)

    def step_command_ota(self, value: dict):
        self.set_devices("zigbee")

    async def step_user_ota(self, option: str):
        did = "lumi." + option[:18].lstrip("0x")
        device = self.gw.devices.get(did)
        resp = await utils.run_zigbee_ota(self.hass, self.gw, device)
        if resp is True:
            resp = OPT_OK
        elif resp is False:
            resp = OPT_NO_FIRMWARE
        else:
            resp = OPT_ERROR
        self.set_end(resp)

    def step_command_bind(self, value: dict):
        self.set_devices(self.step_id)
        self.step_id = "bind_from"

    async def step_user_bind_from(self, option: str):
        did = "lumi." + option[:18].lstrip("0x")
        self.kwargs = {"bind_from": self.gw.devices.get(did)}
        self.set_devices("bind_to")
        self.step_id = "bind_to"

    async def step_user_bind_to(self, option: str):
        did = "lumi." + option[:18].lstrip("0x")
        self.kwargs["bind_to"] = self.gw.devices.get(did)
        self.set_options(None, [OPT_BIND, OPT_UNBIND])
        self.step_id = "bind_type"

    async def step_user_bind_type(self, option: str):
        if option == OPT_BIND:
            await self.gw.silabs_bind(**self.kwargs)
        else:
            await self.gw.silabs_unbind(**self.kwargs)
        self.set_end(OPT_OK)

    def step_command_firmwarelock(self, value: dict):
        lock = value["lock"]
        if lock is None:
            self.set_options(OPT_UNKNOWN, [OPT_UNKNOWN, OPT_ENABLED, OPT_DISABLED])
        else:
            self.set_options(
                OPT_ENABLED if lock else OPT_DISABLED, [OPT_ENABLED, OPT_DISABLED]
            )

    async def step_user_firmwarelock(self, option: str):
        ok = await self.gw.gw3_send_lock(option == OPT_ENABLED)
        self.set_end(OPT_OK if ok else OPT_ERROR)

    def step_command_flashzb(self, value: dict):
        self.set_options(None, [OPT_ORIGINAL, OPT_CUSTOM])

    async def step_user_flashzb(self, option: str):
        ok = await ezsp.update_zigbee_firmware(
            self.hass, self.gw.host, option == OPT_CUSTOM
        )
        self.set_end(OPT_OK if ok else OPT_ERROR)

    def step_command_ok(self, value: dict):
        self.set_end(OPT_OK if value["value"] else OPT_ERROR)
