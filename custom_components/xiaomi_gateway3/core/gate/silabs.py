import asyncio
import json
import time
from logging import DEBUG

from .base import XGateway
from ..const import ZIGBEE, GATEWAY
from ..converters import silabs
from ..converters.zigbee import ZConverter
from ..device import XDevice, hex_to_ieee
from ..mini_mqtt import MQTTMessage
from ..shell.base import ShellBase
from ..shell.session import Session


class SilabsGateway(XGateway):
    ieee: str
    new_sdk: bool
    force_pair: bool = False
    unknown: dict = {}

    # sometimes Multimode Gateway 1 stop respond on /commands (no /executed messages)
    # probably this happenes when Aqara Bulb exist in network
    # so we will restart Z3GatewayHost on next /heartbeat
    commands_ts: float = 0

    async def silabs_read_device(self, sh: ShellBase):
        # 1. Read coordinator info
        raw = await sh.read_file("/data/zigbee/coordinator.info")
        info = json.loads(raw)
        self.ieee = info["mac"][2:].upper()
        assert len(self.ieee) == 16

        self.new_sdk = info["hostVer"] >= "3.14"

        # little delay before neighbors scan
        self.silabs_neighbors_start_ts = time.time() - 3600 + 30

        # if hasattr(sh, "read_silabs_devices"):
        #     raw = await sh.read_silabs_devices()
        #     words = raw.decode().split(" ")
        #     for i in range(0, len(words) - 1, 32):
        #         w = words[i:]
        #         ieee = ":".join(
        #             i if len(i) == 2 else "0" + i for i in reversed(w[3:11])
        #         )
        #         did = "lumi." + ieee.replace(":", "").lstrip("0")
        #         device = self.devices.get(did)
        #         if not device:
        #             nwk = f"0x{w[0]:04}"
        #             device = self.init_device(
        #                 "unknown", did=did, type=ZIGBEE, ieee=ieee, nwk=nwk
        #             )
        #
        #         self.add_device(device)

    def silabs_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith("/MessageReceived"):
            self.silabs_process_recv(msg.json)
        # elif msg.topic.endswith("/MessagePreSentCallback"):
        #     self.silabs_process_send(msg.json)
        elif msg.topic == "zigbee/send" and b"8.0.2084" in msg.payload:
            data: dict = msg.json["params"][0]["value"]
            coro = self.silabs_process_join(data)
            asyncio.create_task(coro)
        elif msg.topic.endswith("/heartbeat"):
            self.silabs_process_heartbeat(msg.json)
        elif msg.topic.endswith("/commands"):
            self.commands_ts = time.time()
        elif msg.topic.endswith("/executed"):
            self.commands_ts = 0
        elif msg.topic.endswith("/deviceleft"):
            self.silabs_process_deviceleft(msg.json)

    def silabs_process_recv(self, data: dict):
        uid = data["eui64"].lower()
        nwk = data["sourceAddress"].lower()

        if self.zigb_log.isEnabledFor(DEBUG):
            # store decoded message, so we can use it later
            data["decode"] = silabs.decode(data)
            self.zigb_log.debug({"uid": uid, "nwk": nwk, "data": data["decode"]})

        ts = int(time.time())

        if nwk != "0x0000":
            if uid == "0x0000000000000000":
                # IMPORTANT. Sometimes gateway send responses with NWK but without IEEE:
                #   ==========handleUnknownDevice============
                #   {"sourceAddress":"0x4A53","eui64":"0x0000000000000000"...}
                for device in self.devices.values():
                    if device.nwk == nwk:
                        break
                else:
                    self.debug("message from unknown IEEE")
                    return  # skip unknown device
            else:
                did = "lumi." + uid.lstrip("0x")
                device: XDevice = self.devices.get(did)
                if not device:
                    if uid not in self.unknown:
                        self.debug("silabs_add_unknown", uid=uid)
                        self.unknown[uid] = {"did": did, "nwk": nwk}
                        asyncio.create_task(self.silabs_process_unknown(uid))
                    return

            device.extra["lqi"] = data["linkQuality"]
            device.extra["rssi"] = data["rssi"]
            device.extra["seq"] = int(data["APSCounter"], 0)

            device.on_keep_alive(self, ts)

            if self.stats_domain:
                device.dispatch({ZIGBEE: ts})
        else:
            # device is gateway
            device = self.device

        # process ZDO message
        if data["sourceEndpoint"] == "0x00":
            if data["clusterId"] == "0x8031":
                coro = self.silabs_process_neighbors(device, data)
                asyncio.create_task(coro)
            return

        # process ZCL message if device supports it
        if device.has_silabs():
            device.on_report(data, self, ts)

    def silabs_process_heartbeat(self, data: dict):
        if self.commands_ts and time.time() - self.commands_ts > 5:
            self.commands_ts = 0
            self.warning("Z3GatewayHost has no respond - restart it")
            asyncio.create_task(self.silabs_restart())

        payload = {
            "network_pan_id": data.get("networkPanId"),
            "radio_tx_power": data.get("radioTxPower"),
            "radio_channel": data.get("radioChannel"),
        }
        self.device.dispatch({GATEWAY: payload})

    def silabs_process_deviceleft(self, data: dict):
        uid = data["eui64"].lower()
        self.debug("silabs_process_deviceleft", uid=uid)
        self.device.dispatch({"left_uid": uid})
        self.unknown.pop(uid, None)  # remove uid from unknown

    async def silabs_process_unknown(self, uid: str):
        await asyncio.sleep(10)  # 10 sec delay before adding unknown device

        unk = self.unknown.pop(uid, {})
        if not unk or unk["did"] in self.devices:
            return

        device = self.init_device(
            None, did=unk["did"], type=ZIGBEE, ieee=hex_to_ieee(uid), nwk=unk["nwk"]
        )
        self.add_device(device)

    async def silabs_process_join(self, data: dict):
        self.debug("silabs_process_join", data=data)
        try:
            async with Session(self.host) as sh:
                # check if model should be prevented from unpairing
                if self.force_pair or not data["model"].startswith(("lumi.", "ikea.")):
                    self.force_pair = False
                    self.debug("Prevent from unpair")
                    await sh.prevent_unpair()

                if hasattr(self, "lumi_read_devices"):
                    await self.lumi_read_devices(sh)
        except Exception as e:
            self.error("Can't handle zigbee join", exc_info=e)

        if device := self.devices.get(data["did"]):
            await self.silabs_config(device)

    async def silabs_config(self, device: XDevice):
        payload = {}
        for conv in device.converters:
            if isinstance(conv, ZConverter):
                conv.config(device, payload)

        if not payload:
            return

        self.debug("silabs_config", device=device)
        await self.silabs_send(device, payload)

    async def silabs_rejoin(self, device: XDevice):
        """Emulate first join of device."""
        self.debug("rejoin", device=device)
        payload = {
            "nodeId": "0x" + device.nwk[2:].upper(),
            "deviceState": 16,
            "deviceType": "0x00FF",
            "timeSinceLastMessage": 0,
            "deviceEndpoint": {
                "eui64": "0x" + device.uid[2:].upper(),
                "endpoint": 0,
                "clusterInfo": [],
            },
            "firstjoined": 1,
        }
        await self.mqtt.publish(f"gw/{self.ieee}/devicejoined", payload)

    async def silabs_leave(self, device: XDevice):
        cmd = silabs.zdo_leave(device.nwk)
        await self.mqtt.publish(f"gw/{self.ieee}/commands", {"commands": cmd})

    async def silabs_send(self, device: XDevice, payload: dict):
        assert "commands" in payload, payload

        silabs.optimize_read(payload["commands"])

        if self.new_sdk:
            # fix payload for new SDK
            for item in payload["commands"]:
                if item["commandcli"].startswith("send "):
                    item["commandcli"] += " 65535 {0000000000000000}"

        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)

    def silabs_on_timer(self, ts: float):
        # periodic scanning only when the stats sensors are enabled
        if self.stats_domain and ts - self.silabs_neighbors_start_ts > 3600:
            asyncio.create_task(self.silabs_neighbors_scan())

    silabs_neighbors_start_ts: float = 0
    silabs_neighbors_requests: list[str] | None = None

    async def silabs_neighbors_scan(self):
        self.debug("silabs_neighbors_scan")
        self.silabs_neighbors_start_ts = time.time()
        self.silabs_neighbors_requests = []
        await self.silabs_neighbors_read("0x0000", 0)

    async def silabs_neighbors_read(self, nwk: str, index: int):
        # process reading requests only 30 second after start
        # protection from multiple Hass requests
        if time.time() - self.silabs_neighbors_start_ts > 30:
            return

        if index == 0:
            # protect from multiple requests to same nwk
            if nwk in self.silabs_neighbors_requests:
                return
            self.silabs_neighbors_requests.append(nwk)

        payload = {"commands": silabs.zdo_mgmt_lqi(nwk, index)}
        await self.silabs_send(self.device, payload)

    async def silabs_process_neighbors(self, device: XDevice, data: dict):
        payload = data.get("decode") or silabs.decode(data)
        self.debug("on_neighbors", device, data=payload)

        for neighbor in payload["neighbors"]:
            rel = neighbor["relationship"]
            if rel == "Child" or (device.nwk == "0x0000" and rel == "Sibling"):
                # search child device
                ieee: str = neighbor["ieee"]
                did = "lumi." + ieee.replace(":", "").lstrip("0")
                if child_device := self.devices.get(did):
                    # update child parent
                    if child_device.extra.get("nwk_parent") != device.nwk:
                        child_device.extra["nwk_parent"] = device.nwk
                        # update stats sensor without increasing msg counter
                        if self.stats_domain:
                            child_device.dispatch({ZIGBEE: 0})

            elif rel == "Parent":
                if device.extra.get("nwk_parent") != neighbor["nwk"]:
                    device.extra["nwk_parent"] = neighbor["nwk"]
                    # update stats sensor without increasing msg counter
                    if self.stats_domain:
                        device.dispatch({ZIGBEE: 0})

            # request neighbors search for child router
            if neighbor["device_type"] == "Router":
                await self.silabs_neighbors_read(neighbor["nwk"], 0)

        # send next request
        index = payload["start_index"] + len(payload["neighbors"])
        if index < payload["entries"]:
            await self.silabs_neighbors_read(device.nwk, index)

    async def silabs_restart(self):
        try:
            async with Session(self.host) as sh:
                # names for all supported gateway models
                await sh.exec("killall Lumi_Z3GatewayHost_MQTT mZ3GatewayHost_MQTT")
        except Exception as e:
            self.warning("Can't restart silabs", exc_info=e)
