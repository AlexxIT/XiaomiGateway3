import asyncio

from . import core_utils
from .const import GATEWAY, ZIGBEE, MESH, GROUP, MATTER
from .device import XDevice
from .gate.base import EVENT_MQTT_PUBLISH, EVENT_TIMER
from .gate.ble import BLEGateway
from .gate.lumi import LumiGateway
from .gate.matter import MatterGateway
from .gate.mesh import MeshGateway
from .gate.miot import MIoTGateway
from .gate.openmiio import OpenMiioGateway
from .gate.silabs import SilabsGateway
from .shell.session import Session


class MultiGateway(
    BLEGateway,
    LumiGateway,
    MatterGateway,
    MeshGateway,
    MIoTGateway,
    OpenMiioGateway,
    SilabsGateway,
):
    main_task: asyncio.Task | None = None

    def start(self):
        if self.main_task:
            return
        self.debug("start")
        self.main_task = asyncio.create_task(self.run_forever())

    async def stop(self):
        if not self.main_task:
            return

        self.debug("stop")
        # wait main task for finished: mqtt disconnect and gateway available false
        # updated for all devices
        while not self.main_task.cancelled():
            self.main_task.cancel()
            await asyncio.sleep(0.1)
        self.main_task = None

    async def run_forever(self):
        while True:
            # check if telnet port OK
            if not await core_utils.check_port(self.host, 23):
                if not await self.enable_telnet():
                    await asyncio.sleep(30)
                    continue

            if not await self.prepare_gateway():
                await asyncio.sleep(60)
                continue

            await self.handle_mqtt_messages()

    async def enable_telnet(self) -> bool:
        """Enable telnet with miio protocol."""
        if not (token := self.options.get("token")):
            return False
        try:
            resp = await core_utils.enable_telnet(
                self.host, token, self.options.get("key")
            )
            self.debug("enable_telnet", data=resp)
            return resp == "ok"
        except Exception as e:
            self.debug("enable_telnet", exc_info=e)
            return False

    async def prepare_gateway(self) -> bool:
        try:
            async with Session(self.host) as sh:
                if not await sh.only_one():
                    self.debug("Connection from a second Hass detected")
                    return False

                info = await sh.get_miio_info()
                model, fw = info["model"], info["version"]

                if model == "lumi.gateway.mgl03" and fw < "1.4.7_0160":
                    self.warning(f"Unsupported firmware: {info}")

                support_ble_mesh = model in (
                    "lumi.gateway.mgl03",
                    "lumi.gateway.mcn001",
                    "lumi.gateway.mgl001",
                )
                support_matter = model == "lumi.gateway.mgl001" and fw >= "1.0.7_0019"

                await self.base_read_device(info)
                await self.lumi_read_devices(sh)
                await self.silabs_read_device(sh)
                await self.openmiio_prepare_gateway(sh)

                if support_ble_mesh:
                    await self.ble_read_devices(sh)
                    await self.mesh_read_devices(sh)

                if support_matter:
                    await self.matter_read_devices(sh)

            self.add_event_listener(EVENT_MQTT_PUBLISH, self.lumi_on_mqtt_publish)
            self.add_event_listener(EVENT_MQTT_PUBLISH, self.miot_on_mqtt_publish)
            self.add_event_listener(EVENT_MQTT_PUBLISH, self.openmiio_on_mqtt_publish)
            self.add_event_listener(EVENT_MQTT_PUBLISH, self.silabs_on_mqtt_publish)

            if support_ble_mesh:
                self.add_event_listener(EVENT_MQTT_PUBLISH, self.ble_on_mqtt_publish)
                self.add_event_listener(EVENT_MQTT_PUBLISH, self.mesh_on_mqtt_publish)

            if support_matter:
                self.add_event_listener(EVENT_MQTT_PUBLISH, self.matter_on_mqtt_publish)

            self.add_event_listener(EVENT_TIMER, self.openmiio_on_timer)
            self.add_event_listener(EVENT_TIMER, self.silabs_on_timer)

            return True
        except Exception as e:
            self.debug("Can't prepare gateway", exc_info=e)
            return False

    async def send(self, device: XDevice, data: dict):
        if device.type == GATEWAY:
            # support multispec in lumi and miot formats
            if "cmd" in data and "method" in data:
                lumi_data = {
                    "cmd": data["cmd"],
                    "did": "lumi.0",
                    "params": [i for i in data["params"] if "res_name" in i],
                }
                miot_data = {
                    "method": data["method"],
                    "params": [i for i in data["params"] if "siid" in i],
                }
                await self.lumi_send(device, lumi_data)
                await self.miot_send(device, miot_data)
            elif "cmd" in data:
                await self.lumi_send(device, data)
            elif "method" in data:
                await self.miot_send(device, data)

        elif device.type == ZIGBEE:
            # support multispec in lumi and silabs format
            if "cmd" in data and "commands" in data:
                lumi_data = {"cmd": data["cmd"], "did": data["did"]}
                if "params" in data:
                    lumi_data["params"] = data["params"]
                if "mi_spec" in data:
                    lumi_data["mi_spec"] = data["mi_spec"]
                silabs_data = {"commands": data["commands"]}
                await self.lumi_send(device, lumi_data)
                await self.silabs_send(device, silabs_data)
            elif "cmd" in data:
                await self.lumi_send(device, data)
            elif "commands" in data:
                await self.silabs_send(device, data)

        elif device.type in (MESH, GROUP):
            await self.miot_send(device, data)
        elif device.type == MATTER:
            await self.matter_send(device, data)

    async def telnet_command(self, cmd: str) -> bool | None:
        self.debug("telnet_command", data=cmd)
        try:
            async with Session(self.host) as sh:
                if cmd == "run_ftp":
                    await sh.run_ftp()
                    return True
                elif cmd == "reboot":
                    await sh.reboot()
                    return True
                elif cmd == "openmiio_restart":
                    await sh.exec("killall openmiio_agent")
                    await asyncio.sleep(1)
                    await self.openmiio_prepare_gateway(sh)
                    return True
                elif cmd == "check_firmware_lock":
                    return await sh.check_firmware_lock()
                elif cmd == "lock_firmware":
                    await sh.lock_firmware(True)
                    return await sh.check_firmware_lock() is True
                elif cmd == "unlock_firmware":
                    await sh.lock_firmware(False)
                    return await sh.check_firmware_lock() is False

        except Exception as e:
            self.error(f"Can't run telnet command: {cmd}", exc_info=e)
