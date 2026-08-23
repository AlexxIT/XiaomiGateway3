import asyncio
from . import core_utils
from .const import GATEWAY, GROUP, MATTER, MESH, ZIGBEE
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

    def __init__(self, *args, **kwargs):
        # Call all parent __init__ methods (handled automatically by MRO)
        super().__init__(*args, **kwargs)
        # Initialize instance flag to prevent duplicate listener registration
        self._listeners_added = False

    def start(self):
        if self.main_task:
            return
        self.debug("start")
        self.main_task = asyncio.create_task(self.run_forever())

    async def stop(self):
        if not self.main_task:
            return
        self.debug("stop")
        task = self.main_task
        self.main_task = None
        task.cancel()
        try:
            # Wait for the task to finish gracefully, with a 5-second timeout
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.CancelledError:
            pass  # Expected cancellation
        except asyncio.TimeoutError:
            self.warning("Main task did not stop within 5 seconds, forcing cancellation.")
            # Force cancel again and wait a short time
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.debug("Exception during force cancellation", exc_info=e)
        except Exception as e:
            self.debug("Exception during main task shutdown", exc_info=e)

    async def run_forever(self):
        while True:
            try:
                # Check if telnet port is OK
                if not await core_utils.check_port(self.host, 23):
                    if not await self.enable_telnet():
                        await asyncio.sleep(30)
                        continue
                
                if not await self.prepare_gateway():
                    await asyncio.sleep(60)
                    continue
                
                # Handle MQTT messages, catch exceptions and cooldown before retrying
                try:
                    await self.handle_mqtt_messages()
                except asyncio.CancelledError:
                    raise  # Propagate cancellation signal to stop the task
                except Exception as e:
                    self.warning(f"MQTT handler crashed, reconnecting in 10s: {e}", exc_info=e)
                    await asyncio.sleep(10)  # Cooldown to prevent busy loop
                    
            except asyncio.CancelledError:
                # Ensure the outer loop also responds to cancellation
                self.debug("run_forever cancelled, exiting")
                raise
            except Exception as e:
                # Catch unexpected outer exceptions, log them, and restart the loop
                self.error(f"Unexpected error in run_forever loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def enable_telnet(self) -> bool:
        """Enable telnet with miio protocol."""
        if not (token := self.options.get("token")):
            return False
        
        key = self.options.get("key")
        if key is None:
            self.debug("No key provided, assuming it's not required for telnet enable")
            
        try:
            resp = await core_utils.enable_telnet(self.host, token, key)
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
                
                # Core read steps, fail directly if they fail
                await self.base_read_device(info)
                await self.lumi_read_devices(sh)
                await self.silabs_read_device(sh)
                await self.openmiio_prepare_gateway(sh)
                
                # Non-critical reads, wrapped in try-except to avoid total failure
                if support_ble_mesh:
                    try:
                        await self.ble_read_devices(sh)
                    except Exception as e:
                        self.warning(f"Failed to read BLE devices: {e}", exc_info=True)
                    try:
                        await self.mesh_read_devices(sh)
                    except Exception as e:
                        self.warning(f"Failed to read Mesh devices: {e}", exc_info=True)
                        
                if support_matter:
                    try:
                        await self.matter_read_devices(sh)
                    except Exception as e:
                        self.warning(f"Failed to read Matter devices: {e}", exc_info=True)

                # Register event listeners (only once per instance lifecycle)
                if not self._listeners_added:
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
                    
                    self._listeners_added = True
                    self.debug("Event listeners registered")

                return True
        except Exception as e:
            self.debug("Can't prepare gateway", exc_info=e)
            # Reset listener flag so it can retry registration on the next attempt
            self._listeners_added = False
            return False

    async def send(self, device: XDevice, data: dict):
        # Add device None check
        if device is None:
            self.debug("Send called with None device, ignoring")
            return
            
        if device.type == GATEWAY:
            # Support multispec in lumi and miot formats
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
            # Support multispec in lumi and silabs format
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
        else:
            # Log unsupported device types for easier debugging
            self.debug(f"Send command not supported for device type: {device.type}", device=device)

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
                else:
                    self.debug(f"Unknown telnet command: {cmd}")
                    return False
        except Exception as e:
            self.error(f"Can't run telnet command: {cmd}", exc_info=e)
            return False
