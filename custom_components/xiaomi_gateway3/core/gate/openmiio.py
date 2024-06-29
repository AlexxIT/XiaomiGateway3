import asyncio
import random
import time

from .base import XGateway
from .. import core_utils
from ..const import GATEWAY
from ..converters.base import encode_time
from ..mini_mqtt import MQTTMessage
from ..shell.session import Session
from ..shell.shell_mgw import ShellMGW
from ..shell.shell_mgw2 import ShellMGW2


class OpenMiioGateway(XGateway):
    miio_ack: dict[int, asyncio.Future] = {}  # TODO: init in constructor
    openmiio_last_ts: float = 0

    async def openmiio_prepare_gateway(self, sh: ShellMGW | ShellMGW2):
        latest = await sh.check_openmiio()
        if not latest:
            self.debug("openmiio: download latest version")
            await sh.download_openmiio()

            latest = await sh.check_openmiio()
            if not latest:
                raise Exception("openmiio: can't run latest version")
        else:
            self.debug("openmiio: latest version detected")

        if "openmiio_agent" not in await sh.get_running_ps():
            self.debug("openmiio: run latest version")
            await sh.run_openmiio()

            mqtt_online = await core_utils.check_port(self.host, 1883)
            if not mqtt_online:
                self.debug("openmiio: waiting for MQTT to start")
                await asyncio.sleep(2)

        # let openmiio boot
        self.openmiio_last_ts = time.time()

    async def openmiio_send(
        self, method: str, params: dict | list = None, timeout: int = 5
    ):
        fut = asyncio.get_event_loop().create_future()

        cid = random.randint(1_000_000_000, 2_147_483_647)
        self.miio_ack[cid] = fut

        payload = {"id": cid, "method": method, "params": params}
        await self.mqtt.publish("miio/command", payload)

        try:
            await asyncio.wait_for(self.miio_ack[cid], timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            del self.miio_ack[cid]

        return fut.result()

    def openmiio_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "openmiio/report":
            self.openmiio_last_ts = time.time()
            self.device.dispatch({GATEWAY: msg.json})

        elif msg.topic == "miio/command_ack":
            if ack := self.miio_ack.get(msg.json["id"]):
                ack.set_result(msg.json)

        elif msg.topic == "miio/report":
            if b'"event.gw.heartbeat"' in msg.payload:
                self.openmiio_process_gw_heartbeat(msg.json["params"][0])

    def openmiio_on_timer(self, ts: float):
        if ts - self.openmiio_last_ts < 60:
            return

        self.debug("openmiio: WARNING report timeout")
        self.device.dispatch({GATEWAY: {"openmiio": {"uptime": None}}})
        asyncio.create_task(self.openmiio_restart())

    async def openmiio_restart(self):
        try:
            async with Session(self.host) as sh:
                if await sh.only_one():
                    await self.openmiio_prepare_gateway(sh)
        except Exception as e:
            self.warning("Can't restart openmiio", exc_info=e)

    def openmiio_process_gw_heartbeat(self, data: dict):
        payload = {
            "free_mem": data["free_mem"],
            "load_avg": data["load_avg"],
            "rssi": data["rssi"] if data["rssi"] <= 0 else data["rssi"] - 100,
            "uptime": encode_time(data["run_time"]),
        }
        self.device.extra["rssi"] = payload["rssi"]
        self.device.dispatch({GATEWAY: payload})
