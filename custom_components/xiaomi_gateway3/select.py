import json

from homeassistant.components import persistent_notification
from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity

from . import DOMAIN
from .core import utils
from .core.converters import Converter
from .core.device import XDevice
from .core.entity import XEntity
from .core.gateway import XGateway
from .core.utils import TITLE


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: XGateway, device: XDevice, conv: Converter):
        if conv.attr in device.entities:
            entity: XEntity = device.entities[conv.attr]
            entity.gw = gateway
        elif conv.attr == "command":
            entity = CommandSelect(gateway, device, conv)
        elif conv.attr == "data":
            entity = DataSelect(gateway, device, conv)
        else:
            entity = XiaomiSelect(gateway, device, conv)
        async_add_entities([entity])

    gw: XGateway = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup(__name__, setup)


# noinspection PyAbstractClass
class XiaomiSelectBase(XEntity, SelectEntity):
    _attr_current_option: str = None

    def __init__(self, gateway: 'XGateway', device: XDevice, conv: Converter):
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


FIRMWARE_LOCK = {
    False: "disabled",
    True: "enabled"
}


# noinspection PyAbstractClass
class CommandSelect(XiaomiSelectBase):
    async def async_select_option(self, option: str):
        self._attr_current_option = option
        self.async_write_ha_state()

        payload = self.device.encode({self.attr: option})
        command = payload[self.attr]
        if command == "idle":
            await self.device_send({"pair": False})
        elif command == "pair":
            await self.device_send({"pair": True})
        elif command == "lock":
            lock = await self.gw.gw3_read_lock()
            self.device.update({"data": command, "lock": lock})
            return
        elif command in ("reboot", "ftp", "dump"):
            await self.gw.telnet_send(command)
        elif command == "parentscan":
            await self.gw.z3_run_parent_scan()

        self.device.update({"data": command})


# noinspection PyAbstractClass
class DataSelect(XEntity, SelectEntity):
    _attr_current_option = None
    _attr_options = None
    command = None
    kwargs = None

    def set_current(self, value):
        # force update dropdown in GUI
        self._attr_current_option = None
        self._attr_options = [value] if value else None
        self.async_write_ha_state()

        if not value:
            return

        self._attr_current_option = value
        self.async_write_ha_state()

    def set_devices(self, feature: str):
        devices = [
            f"{d.mac}: {d.name}"
            for d in self.gw.filter_devices(feature)
        ]
        self._attr_current_option = None
        self._attr_options = devices
        self.async_write_ha_state()

    def process_command(self, data: json):
        self.command = data[self.attr]
        if self.command == "pair":
            self.set_current("Ready to join")

        elif self.command == "remove":
            self.set_devices("zigbee+ble")

        elif self.command in ("config", "ota"):
            self.set_devices("zigbee")

        elif self.command == "bind":
            self.kwargs = {}
            self.set_devices("bind_from")

        elif self.command == "lock":
            self._attr_current_option = FIRMWARE_LOCK.get(data["lock"])
            self._attr_options = list(FIRMWARE_LOCK.values())
            self.async_write_ha_state()

        elif self.command == "miio":
            self.set_current("Use select_option service")

        elif self.command == "idle":
            self.set_current(None)

        elif self.command in ("reboot", "ftp", "dump", "parentscan"):
            # ping-pong
            self.device.update({"command": None})

    @callback
    def async_set_state(self, data: dict):
        if not self.hass:
            return

        if self.attr in data:
            self.process_command(data)

        elif "pair" in data:
            if data["pair"]:
                self.set_current("Ready to join")
            else:
                self.device.update({"command": None})

        elif "discovered_mac" in data:
            mac = data["discovered_mac"]
            self.set_current(f"Discovered: 0x{mac:>016s}")

        elif "pair_command" in data:
            data = data["pair_command"]
            if data["install_code"]:
                self.set_current("Send network key (secure)")
            else:
                self.set_current("Send network key (legacy)")

        elif "added_device" in data:
            data = data["added_device"]
            self.set_current(f"Paired: {data['mac']} ({data['model']})")
            self.device.update({"command": None})

        elif "remove_did" in data:
            did = data['remove_did']
            device = self.gw.devices.get(did)
            utils.remove_device(self.hass, device.mac)
            self.set_current(f"Removed: {did[5:]}")
            self.device.update({"command": None})

        elif "ota_progress" in data:
            percent = data["ota_progress"]
            self.set_current(f"Update progress: {percent}%")

    async def async_select_option(self, option: str):
        if self.command == "idle":
            raise RuntimeWarning

        elif self.command == "remove":
            mac = option.split(":")[0]
            if mac.startswith("0x"):
                did = "lumi." + mac.lstrip("0x")
                device = self.gw.devices.get(did)
                if device.model:
                    await self.device_send({"remove_did": did})
                else:
                    await self.gw.silabs_leave(device)
            else:
                device = self.gw.devices.get(mac)
                utils.remove_device(self.hass, device.mac)
            self.device.update({"command": None})

        elif self.command == "config":
            did = "lumi." + option[:18].lstrip("0x")
            device = self.gw.devices.get(did)
            await self.gw.silabs_rejoin(device)

        elif self.command == "ota":
            did = "lumi." + option[:18].lstrip("0x")
            device = self.gw.devices.get(did)
            resp = await utils.run_zigbee_ota(self.hass, self.gw, device)
            self.set_current(resp)

        elif self.command == "bind":
            if "bind_from" not in self.kwargs:
                did = "lumi." + option[:18].lstrip("0x")
                self.kwargs["bind_from"] = self.gw.devices.get(did)
                self.set_devices("bind_to")

            elif "bind_to" not in self.kwargs:
                did = "lumi." + option[:18].lstrip("0x")
                self.kwargs["bind_to"] = self.gw.devices.get(did)
                self._attr_options = ["bind", "unbind"]
                self.async_write_ha_state()

            else:
                if option == "bind":
                    await self.gw.silabs_bind(**self.kwargs)
                    self.set_current("Bind command sent")
                elif option == "unbind":
                    await self.gw.silabs_unbind(**self.kwargs)
                    self.set_current("Unbind command sent")
                self.device.update({"command": None})

        elif self.command == "lock":
            lock = next(k for k, v in FIRMWARE_LOCK.items() if v == option)
            if await self.gw.gw3_send_lock(lock):
                self.set_current("Lock enabled" if lock else "Lock disabled")
            else:
                self.set_current("Can't change lock")
            self.device.update({"command": None})

        elif self.command == "miio":
            raw = json.loads(option)
            resp = await self.gw.miio.send(raw['method'], raw.get('params'))
            persistent_notification.async_create(self.hass, str(resp), TITLE)
