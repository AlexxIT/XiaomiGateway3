import asyncio
import json

from .base import XGateway
from ..const import ZIGBEE, GATEWAY
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
        zb_msg = None

        # skip message from coordinator
        if ieee == "0x0000000000000000" or nwk == "0x0000":
            return

        did = "lumi." + ieee.lstrip("0x")
        device: XDevice = self.devices.get(did)
        if not device:
            # we need to save device to know its NWK in future
            # device = XDevice(did, ZIGBEE, None, mac=mac, nwk=nwk)
            # self.add_device(device)
            # self.debug_device(device, "new unknown device", tag="SLBS")
            return

        device.extra["lqi"] = data["linkQuality"]
        device.extra["rssi"] = data["rssi"]
        device.extra["seq"] = int(data["APSCounter"], 0)

        if self.stats_domain:
            device.dispatch({ZIGBEE: True})

        # process raw zigbee if device supports it
        if device.has_silabs():
            # if not zb_msg:
            #     zb_msg = silabs.decode(data)
            # if zb_msg and "cluster" in zb_msg:
            device.on_report(data, self)

        # process device stats if enabled, also works for LumiGateway
        # if device and ZIGBEE in device.entities:
        #     payload = device.decode(ZIGBEE, data)
        #     device.update(payload)

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
            "nodeId": device.nwk.upper(),
            "deviceState": 16,
            "deviceType": "0x00FF",
            "timeSinceLastMessage": 0,
            "deviceEndpoint": {
                "eui64": device.uid.upper(),
                "endpoint": 0,
                "clusterInfo": [],
            },
            "firstjoined": 1,
        }
        await self.mqtt.publish(f"gw/{self.ieee}/devicejoined", payload)

    async def silabs_send(self, device: XDevice, payload: dict):
        assert "commands" in payload, payload
        # self.debug_device(device, "send", payload, tag="SLBS")

        if self.new_sdk:
            # fix payload for new SDK
            for item in payload["commands"]:
                if item["commandcli"].startswith("send "):
                    item["commandcli"] += " 65535 {0000000000000000}"

        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)
