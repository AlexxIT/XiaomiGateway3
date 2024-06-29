from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .core import ezsp
from .core.const import GATEWAY, ZIGBEE, MESH, MATTER
from .core.gateway import MultiGateway
from .hass import hass_utils
from .hass.entity import XEntity


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry, async_add_entities) -> None:
    XEntity.ADD[entry.entry_id + "select"] = async_add_entities


class XSelect(XEntity, SelectEntity, RestoreEntity):
    _attr_current_option: str = None
    _attr_options = None

    def on_init(self):
        conv = next(i for i in self.device.converters if i.attr == self.attr)
        if hasattr(conv, "map"):
            self._attr_options = list(conv.map.values())

    def set_state(self, data: dict):
        self._attr_current_option = data[self.attr]

    def get_state(self) -> dict:
        return {self.attr: self._attr_current_option}

    async def async_select_option(self, option: str):
        self.device.write({self.attr: option})


CMD_NONE = "-"
CMD_INFO = "info"
CMD_UPDATE = "update"
# GATEWAY
CMD_DISABLE = "disable"
CMD_ENABLE = "enable"
CMD_PAIR = "pair"
CMD_FORCE_PAIR = "force_pair"
CMD_PARENT_SCAN = "parent_scan"
CMD_FLASH_EZSP = "flash_ezsp"
CMD_FW_LOCK = "firmware_lock"
CMD_OPENMIIO_RESTART = "openmiio_restart"
CMD_RUN_FTP = "run_ftp"
CMD_REBOOT = "reboot"
# ZIGBEE
CMD_RECONFIG = "reconfig"
CMD_REMOVE = "remove"


class XCommandSelect(XEntity, SelectEntity):
    gw: MultiGateway

    def on_init(self):
        self._attr_current_option = CMD_NONE
        self._attr_options = [CMD_NONE, CMD_INFO]
        self._attr_translation_key = self.attr

        # noinspection PyTypeChecker
        self.gw = self.device.gateways[0]

        if self.device.type == GATEWAY:
            self._attr_options += [
                CMD_UPDATE,
                CMD_RUN_FTP,
                CMD_REBOOT,
                CMD_DISABLE,
                CMD_ENABLE,
            ]
            if self.device.model == "lumi.gateway.mgl03":
                self._attr_options += [
                    CMD_FW_LOCK,
                    CMD_OPENMIIO_RESTART,
                    CMD_PAIR,
                    CMD_FORCE_PAIR,
                    CMD_PARENT_SCAN,
                    CMD_FLASH_EZSP,
                ]
            else:
                self._attr_options += [
                    CMD_OPENMIIO_RESTART,
                    CMD_PAIR,
                    CMD_FORCE_PAIR,
                    CMD_PARENT_SCAN,
                ]
        elif self.device.type == ZIGBEE:
            if self.device.has_controls():
                self._attr_options.append(CMD_UPDATE)
            self._attr_options += [CMD_RECONFIG, CMD_REMOVE]
        elif self.device.type in (MESH, MATTER):
            self._attr_options += [CMD_UPDATE]

    @property
    def available(self) -> bool:
        return True  # always ON

    def clear_state(self):
        self._attr_current_option = CMD_NONE
        self._async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option == CMD_INFO:
            await hass_utils.show_device_info(
                self.hass, self.device, self.device.human_name, self.entity_id
            )
        elif option == CMD_UPDATE:
            self.device.read()

        # ZIGBEE
        elif option == CMD_RECONFIG:
            await self.gw.silabs_config(self.device)
        elif option == CMD_REMOVE:
            if self.device.model:
                await self.gw.device.write({"remove_did": self.device.did})
            else:
                await self.gw.silabs_leave(self.device)

        # GATEWAY
        elif option == CMD_PAIR:
            self.gw.force_pair = False
            self.device.write({"pair": True})
        elif option == CMD_FORCE_PAIR:
            self.gw.force_pair = True
            self.device.write({"pair": True})
        elif option == CMD_DISABLE:
            await self.gw.stop()
        elif option == CMD_ENABLE:
            self.gw.start()
        elif option in (CMD_RUN_FTP, CMD_REBOOT, CMD_OPENMIIO_RESTART):
            ok = await self.gw.telnet_command(option)
            self.device.dispatch({"data": OPT_OK if ok else OPT_ERROR})
        elif option == CMD_FW_LOCK:
            ok = await self.gw.telnet_command("check_firmware_lock")
            if isinstance(ok, bool):
                payload = {
                    "data": OPT_ENABLED if ok else OPT_DISABLED,
                    "options": [OPT_ENABLED, OPT_DISABLED],
                }
                self.device.dispatch(payload)
            else:
                self.device.dispatch({"data": OPT_ERROR})
        elif option == CMD_FLASH_EZSP:
            self.device.dispatch({"data": None, "options": [OPT_ORIGINAL, OPT_CUSTOM]})
        elif option == CMD_PARENT_SCAN:
            await self.gw.silabs_neighbors_scan()

        # self._attr_current_option = option
        # self._async_write_ha_state()
        # self.hass.loop.call_later(0.5, self.clear_state)


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


class XDataSelect(XEntity, SelectEntity):
    gw: MultiGateway

    def on_init(self):
        self._attr_current_option = None
        self._attr_options = []
        self._attr_translation_key = self.attr

        self.listen_attrs = {
            "data",
            "pair",
            "discovered_mac",
            "pair_command",
            "added_device",
            "remove_did",
            "left_uid",
        }

        # noinspection PyTypeChecker
        self.gw = self.device.gateways[0]

    def set_option(self, option: str, options: list[str] = None):
        self._attr_current_option = option
        self._attr_options = options or [option]

    def append_option(self, option: str):
        self._attr_current_option = option
        if option not in self._attr_options:
            # VERY important to create new array and not to append item to old
            self._attr_options = self._attr_options + [option]

    def set_result(self, ok: bool):
        self.set_option(OPT_OK if ok else OPT_ERROR)
        self._async_write_ha_state()

    def set_state(self, data: dict):
        if self.attr in data:
            self.set_option(data[self.attr], data.get("options"))
        elif data.get("pair") is True:
            self.set_option(OPT_JOIN, [OPT_JOIN, OPT_STOP_JOIN])
        elif data.get("pair") is False:
            self.append_option(OPT_STOP_JOIN)
        elif value := data.get("discovered_mac"):
            self.append_option(f"Discovered: 0x{value:>016s}")
        elif value := data.get("pair_command"):
            secure = value["install_code"]
            self.append_option(OPT_KEY_SECURE if secure else OPT_KEY_LEGACY)
        elif value := data.get("added_device"):
            self.append_option(f"Paired: {value['model']}")
        elif value := data.get("remove_did"):
            # "res_name":"8.0.2082","value":{"did":"lumi.1234567890"}"
            # "res_name":"8.0.2082","value":"lumi.1234567890"
            did = value["did"] if isinstance(value, dict) else value
            self.append_option(f"Removed: 0x{did[5:]:>016s}")
        elif uid := data.get("left_uid"):
            did = "lumi." + uid.lstrip("0x")
            if device := self.gw.devices.get(did):
                hass_utils.remove_device(self.hass, device)
            self.append_option(f"Left: {uid}")

    async def async_select_option(self, option: str) -> None:
        if option == OPT_JOIN:
            self.device.write({"pair": True})
        elif option == OPT_STOP_JOIN:
            self.device.write({"pair": False})
        elif option == OPT_ENABLED:
            ok = await self.gw.telnet_command("lock_firmware")
            self.set_result(ok)
        elif option == OPT_DISABLED:
            ok = await self.gw.telnet_command("unlock_firmware")
            self.set_result(ok)
        elif option == OPT_ORIGINAL:
            ok = await ezsp.update_zigbee_firmware(self.hass, self.gw.host, False)
            self.set_result(ok)
        elif option == OPT_CUSTOM:
            ok = await ezsp.update_zigbee_firmware(self.hass, self.gw.host, True)
            self.set_result(ok)


XEntity.NEW["select"] = XSelect
XEntity.NEW["select.attr.command"] = XCommandSelect
XEntity.NEW["select.attr.data"] = XDataSelect
