"""All different technologies divided to independent classes (modules):

gw3 and e1:
- GatewayBase - base class for all subclasses
- LumiGateway - process Zigbee devices in Lumi and MIoT spec using MQTT
- SilabsGateway - process Zigbee devices in Zigbee spec using Silabs Z3 MQTT
- Z3Gateway - process Zigbee network tables using Silabs Z3 console output
- XGateway - main class for enable Telnet and process MQTT loop

gw3:
- MIoTGateway - process Gateway and Mesh properties in MIoT spec using miio
- MainGateway - process Gateway device and some global stats using Telent
- BLEGateway - process BLE devices in MiBeacon format using MQTT
- MeshGateway - init Mesh devices but depends on MIoTGateway for control them
"""
import asyncio
import logging
import time

from .base import (
    SIGNAL_PREPARE_GW,
    SIGNAL_MQTT_CON,
    SIGNAL_MQTT_DIS,
    SIGNAL_MQTT_PUB,
    SIGNAL_TIMER,
)
from .gate_e1 import GateE1
from .gate_mgw import GateMGW
from .gate_mgw2 import GateMGW2
from .. import shell, utils
from ..converters import GATEWAY
from ..mini_miio import AsyncMiIO
from ..mini_mqtt import MiniMQTT, MQTTMessage

_LOGGER = logging.getLogger(__name__)


class XGateway(GateMGW, GateE1, GateMGW2):
    main_task: asyncio.Task = None
    timer_task: asyncio.Task = None

    def __init__(self, host: str, token: str, **options):
        self.log = _LOGGER

        self.host = host
        self.options = options

        self.dispatcher = {}
        self.setups = {}
        self.tasks = []
        self.miio_ack = {}

        self.miio = AsyncMiIO(host, token)
        self.mqtt = MiniMQTT()

        self.miio.debug = "true" in self.debug_mode

    def start(self):
        self.main_task = asyncio.create_task(self.run_forever())

    # noinspection PyUnusedLocal
    async def stop(self, *args):
        self.debug("Stop all tasks")

        self.main_task.cancel()

        for device in self.devices.values():
            if self not in device.gateways:
                continue

            # 1. Remove this XGateway from XDevice
            device.gateways.remove(self)

            # 2. Remove this XGateway from XEntity
            for entity in device.entities.values():
                if entity.gw == self:
                    entity.gw = None

            if len(device.gateways) == 0:
                continue

            # 3. Move this XDevice to another XGateway
            gw = device.gateways[0]
            device.setup_entitites(gw, gw.stats_enable)

    async def enable_telnet(self):
        """Enable telnet with miio protocol."""
        resp = await utils.enable_telnet(self.miio, self.options.get("key"))
        if not resp or resp.get("result") != ["ok"]:
            self.debug(f"Can't enable telnet")
            return False
        return True

    async def run_forever(self):
        """Main thread loop."""
        self.debug("Start main loop")

        while True:
            try:
                # if not telnet - enable it
                if (
                    not await utils.check_port(self.host, 23)
                    and not await self.enable_telnet()
                ):
                    await asyncio.sleep(30)
                    continue

                # if not mqtt - enable it (handle Mi Home and ZHA mode)
                if not await self.prepare_gateway() or not await self.mqtt.connect(
                    self.host
                ):
                    await asyncio.sleep(60)
                    continue

                await self.mqtt_connect()
                try:
                    async for msg in self.mqtt:
                        # noinspection PyTypeChecker
                        asyncio.create_task(self.mqtt_message(msg))
                except Exception as e:
                    self.debug(f"MQTT connection issue", exc_info=e)
                finally:
                    await self.mqtt.disconnect()
                    await self.mqtt.close()
                    await self.mqtt_disconnect()

            except Exception as e:
                self.error("Main loop error", exc_info=e)

        self.debug("Stop main loop")

    async def timer(self):
        while True:
            ts = time.time()
            self.check_available(ts)
            await self.dispatcher_send(SIGNAL_TIMER, ts=ts)
            await asyncio.sleep(30)

    async def mqtt_connect(self):
        self.debug("MQTT connected")

        await self.mqtt.subscribe("#")

        self.update_available(True)

        await self.dispatcher_send(SIGNAL_MQTT_CON)

        self.timer_task = asyncio.create_task(self.timer())

    async def mqtt_disconnect(self):
        self.debug("MQTT disconnected")

        self.timer_task.cancel()

        self.update_available(False)

        await self.dispatcher_send(SIGNAL_MQTT_DIS)

    async def mqtt_message(self, msg: MQTTMessage):
        # skip spam from broker/ping
        if msg.topic == "broker/ping":
            return

        if "mqtt" in self.debug_mode:
            self.debug_tag(f"{msg.topic} {msg.payload}", tag="MQTT")

        try:
            await self.mqtt_read(msg)

            await self.dispatcher_send(SIGNAL_MQTT_PUB, msg=msg)
        except Exception as e:
            self.error(f"ERROR processing MQTT: {msg.topic} {msg.payload}", exc_info=e)

    async def prepare_gateway(self) -> bool:
        """Launching the required utilities on the gw, if they are not already
        running.
        """
        try:
            async with shell.Session(self.host) as sh:
                if not await sh.only_one():
                    self.debug("Connection from a second Hass detected")
                    return False

                await sh.get_version()

                self.debug(f"Prepare gateway {sh.model} with fw {sh.ver}")
                if isinstance(sh, shell.ShellMGW):
                    return await self.gw3_prepare_gateway(sh)
                elif isinstance(sh, shell.ShellE1):
                    return await self.e1_prepare_gateway(sh)
                elif isinstance(sh, shell.ShellMGW2):
                    return await self.mgw2_prepare_gateway(sh)

        except Exception as e:
            self.error(f"Can't prepare gateway", e)
            return False

    def update_available(self, value: bool):
        self.available = value

        for device in self.devices.values():
            if self in device.gateways:
                device.update_available()

    async def telnet_send(self, command: str):
        try:
            async with shell.Session(self.host) as sh:
                if command == "ftp":
                    await sh.run_ftp()
                elif command == "tardata":
                    return await sh.tar_data()
                elif command == "reboot":
                    await sh.reboot()
                elif command == "openmiio_reload":
                    await sh.exec("killall openmiio_agent")
                    await asyncio.sleep(1)
                    await self.openmiio_prepare_gateway(sh)
                else:
                    await sh.exec(command)
                return True

        except Exception as e:
            self.error(f"Can't run telnet command: {command}", exc_info=e)
            return False

    async def tar_data(self) -> str:
        try:
            async with shell.Session(self.host) as sh:
                return await sh.tar_data()
        except Exception as e:
            return f"{type(e).__name__} {e}"

    def check_available(self, ts: float):
        for device in list(self.devices.values()):
            if self not in device.gateways or device.type == GATEWAY:
                continue

            if (
                device.poll_timeout
                and ts - device.decode_ts > device.poll_timeout
                and ts - device.encode_ts > device.poll_timeout
            ):
                for attr, entity in device.entities.items():
                    if entity.added and hasattr(entity, "async_update"):
                        self.debug_device(device, "poll state", attr)
                        asyncio.create_task(entity.update_state())
                        break

            if (
                device.available
                and device.available_timeout
                and ts - device.decode_ts > device.available_timeout
            ):
                self.debug_device(device, "set device offline")
                device.available = False
