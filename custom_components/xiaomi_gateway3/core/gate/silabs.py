import asyncio
import json

from .base import XGateway
from ..const import ZIGBEE, GATEWAY
from ..converters import silabs
from ..converters.zigbee import ZConverter
from ..device import XDevice
from ..mini_mqtt import MQTTMessage
from ..shell.base import ShellBase
from ..shell.session import Session


class SilabsGateway(XGateway):
    ieee: str
    new_sdk: bool
    force_pair: bool = False

    async def silabs_read_device(self, sh: ShellBase):
        # 1. Read coordinator info
        raw = await sh.read_file("/data/zigbee/coordinator.info")
        info = json.loads(raw)
        self.ieee = info["mac"][2:].upper()
        assert len(self.ieee) == 16

        # version 1.3.33 on all gateways
        # version 1.6.5 on lumi.gateway.mcn001 fw 1.0.7
        self.new_sdk = info["sdkVer"] > "1.3.33"

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
        #             device = XDevice(
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

    def silabs_process_heartbeat(self, data: dict):
        payload = {
            "network_pan_id": data.get("networkPanId"),
            "radio_tx_power": data.get("radioTxPower"),
            "radio_channel": data.get("radioChannel"),
        }
        self.device.dispatch({GATEWAY: payload})

    def silabs_process_recv(self, data: dict):
        ieee = data["eui64"].lower()
        nwk = data["sourceAddress"].lower()

        # skip message from coordinator
        if ieee == "0x0000000000000000" or nwk == "0x0000":
            return

        did = "lumi." + ieee.lstrip("0x")
        device: XDevice = self.devices.get(did)
        if not device:
            self.debug("message from unknown device")
            return

        device.extra["lqi"] = data["linkQuality"]
        device.extra["rssi"] = data["rssi"]
        device.extra["seq"] = int(data["APSCounter"], 0)

        if self.stats_domain:
            device.dispatch({ZIGBEE: True})

        # process raw zigbee if device supports it
        if device.has_silabs():
            device.on_report(data, self)

    async def silabs_process_join(self, data: dict):
        self.debug("Process join", data=data)
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

        device = self.devices.get(data["did"])
        if not device:
            self.warning("Can't find device after join")
            return

        payload = {}
        for conv in device.converters:
            if isinstance(conv, ZConverter):
                conv.config(device, payload, self)

        if not payload:
            return

        self.debug("config", device=device)
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
        # self.debug_device(device, "send", payload, tag="SLBS")

        if self.new_sdk:
            # fix payload for new SDK
            for item in payload["commands"]:
                if item["commandcli"].startswith("send "):
                    item["commandcli"] += " 65535 {0000000000000000}"

        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)
