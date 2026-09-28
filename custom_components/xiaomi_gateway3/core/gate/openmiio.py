import asyncio
import random
import time

from .base import XGateway
from .. import core_utils
from ..const import GATEWAY
from ..converters.base import encode_time
from ..device import XDevice
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
        self, device: XDevice, payload: dict | list = None, timeout: int = 5
    ):
        assert "uid" in device.extra
        fut = asyncio.get_event_loop().create_future()

        cid = random.randint(1_000_000_000, 2_147_483_647)
        self.miio_ack[cid] = fut

        if payload["cmd"] == "write":
            data = {}
            for p in payload["params"]:
                if "value" in p:
                    data[p["res_name"]] = str(p["value"])
            if len(data) < 1:
                return None
            params = {
                "name": f"/lumi/gw/res/{payload["cmd"]}",
                "value": {
                    "data": data,
                    "did": device.extra["uid"],
                    "source": ""
                },
            }
        else:
            data = []
            for p in payload["params"]:
                data.append(p["res_name"])
            params = {
                "name": f"/lumi/gw/res/{payload["cmd"]}",
                "value": {
                    "rid": data,
                    "did": device.extra["uid"],
                },
            }

        payload = {"_to": 4, "id": cid, "method": "auto.control", "params": params}
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

            if b"/lumi/res/report/attr" in msg.payload:
                self.openmiio_process_properties(msg.json, from_cache=False)

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

    def openmiio_process_properties(self, payload: dict, from_cache: bool):
        ts = int(time.time())

        if data := payload["params"].get("value", {}).get("data"):
            res_list = []
            for k, v in data.items():
                try:
                    v = int(v)
                except:
                    pass
                res_list.append({"res_name": k, "value": v})
            payload["params"]["value"].pop("data")
            payload["params"]["value"]["res_list"] = res_list

        if data := payload["params"].get("value", {}).get("res_list"):
            res_list = []
            for res in data:
                v = res["value"]
                try:
                    v = int(v)
                except:
                    pass
                res_list.append({"res_name": res["res_name"], "value": v})
            payload["params"]["value"].pop("res_list")
            payload["params"]["value"]["res_list"] = res_list

        # convert miio response format to multiple responses in lumi format
        for device in self.devices:

            if ((self.devices[device].extra.get("uid") == None) or
                    (self.devices[device].extra.get("uid") != payload["params"].get("value", {}).get("did"))):
                continue
            dev = self.devices.get(device)
            dev.on_keep_alive(self, ts)

            dev.on_report(payload["params"]["value"].get("res_list", []), self, ts)

