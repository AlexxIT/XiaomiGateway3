import json

from .base import GatewayBase, SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB
from .. import shell
from ..converters import silabs, is_mihome_zigbee
from ..converters.zigbee import ZConverter
from ..device import XDevice, ZIGBEE
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class SilabsGateway(GatewayBase):
    ieee: str = None

    silabs_pair_model = None

    pair_payload = None
    pair_payload2 = None

    def silabs_init(self):
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.silabs_prepare_gateway)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.silabs_mqtt_publish)

    async def silabs_prepare_gateway(self, sh: shell.TelnetShell):
        if self.ieee is not None:
            return
        # 1. Read coordinator info
        raw = await sh.read_file("/data/zigbee/coordinator.info")
        info = json.loads(raw)
        self.ieee = info["mac"][2:].upper()
        assert len(self.ieee) == 16

    async def silabs_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith("/MessageReceived"):
            await self.silabs_process_recv(msg.json)
        elif msg.topic.endswith("/MessagePreSentCallback"):
            await self.silabs_process_send(msg.json)
        elif msg.topic == "zigbee/send" and b"8.0.2084" in msg.payload:
            data: dict = msg.json["params"][0]["value"]
            await self.silabs_process_join(data)

    async def silabs_process_recv(self, data: dict):
        mac = data["eui64"].lower()
        nwk = data["sourceAddress"].lower()
        zb_msg = None

        # print raw zigbee if enabled in logs
        if "zigbee" in self.debug_mode:
            zb_msg = silabs.decode(data)
            self.debug_tag(f"{mac} ({nwk}) recv {zb_msg}", tag="ZIGB")

        if mac == "0x0000000000000000" or nwk == "0x0000":
            return

        did = "lumi." + mac.lstrip("0x")
        device: XDevice = self.devices.get(did)
        if not device:
            # we need to save device to know its NWK in future
            device = XDevice(ZIGBEE, None, did, mac, nwk)
            self.add_device(did, device)
            self.debug_device(device, "new unknown device", tag="SLBS")
            return

        if not device.model:
            # Sonoff Mini has a bug: it hasn't app_ver, so gw can't add it
            if data["clusterId"] == "0x0000":
                if not zb_msg:
                    zb_msg = silabs.decode(data)
                if zb_msg.get("app_version") == "Status.UNSUPPORTED_ATTRIBUTE":
                    await self.silabs_send_fake_version(device, data)
            return

        # process raw zigbee if device supports it
        if device.has_zigbee_conv:
            if not zb_msg:
                zb_msg = silabs.decode(data)
            if zb_msg and "cluster" in zb_msg:
                payload = device.decode_zigbee(zb_msg)
                device.update(payload)

        # process device stats if enabled, also works for LumiGateway
        if device and ZIGBEE in device.entities:
            payload = device.decode(ZIGBEE, data)
            device.update(payload)

    async def silabs_process_send(self, data: dict):
        if "zigbee" not in self.debug_mode:
            return
        if "eui64" in data:
            did = "lumi." + data["eui64"].lstrip("0x").lower()
            device = self.devices.get(did)
        elif "shortId" in data:
            nwk = data["shortId"].lower()
            device = next((d for d in self.devices.values() if d.nwk == nwk), None)
        else:
            return
        if not device:
            return
        zb_msg = silabs.decode(data)
        self.debug_tag(f"{device.mac} {device.nwk} send {zb_msg}", tag="ZIGB")

    async def silabs_process_join(self, data: dict):
        if not is_mihome_zigbee(data["model"]):
            self.debug("Prevent unpair 3rd party model: " + data["model"])
            await self.silabs_prevent_unpair()

        device = self.devices.get(data["did"])
        if not device.model:
            self.debug_device(device, "paired", data)
            device.update_model(data["model"])
            device.extra["fw_ver"] = parse_version(data["version"])
            self.add_device(device.did, device)
        else:
            self.debug_device(device, "model exist on pairing")

        await self.silabs_config(device)

    async def silabs_send(self, device: XDevice, payload: dict):
        assert "commands" in payload, payload
        self.debug_device(device, "send", payload, tag="SLBS")
        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)

    async def silabs_read(self, device: XDevice, payload: dict):
        assert "commands" in payload, payload
        self.debug_device(device, "read", payload, tag="SLBS")
        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)

    async def silabs_prevent_unpair(self):
        try:
            async with shell.Session(self.host) as sh:
                await sh.prevent_unpair()
        except Exception as e:
            self.error("Can't prevent unpair", e)

    async def silabs_config(self, device: XDevice):
        """Run some config converters if device spec has them. Binds, etc."""
        payload = {}
        for conv in device.converters:
            if isinstance(conv, ZConverter):
                conv.config(device, payload, self)

        if not payload:
            return

        self.debug_device(device, "config")
        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)

    async def silabs_send_fake_version(self, device: XDevice, data: dict):
        self.debug_device(device, "send fake version")
        data["APSCounter"] = "0x00"
        data["APSPlayload"] = "0x1800010100002000"
        await self.mqtt.publish(f"gw/{self.ieee}/MessageReceived", data)

    async def silabs_rejoin(self, device: XDevice):
        """Emulate first join of device."""
        self.debug_device(device, "rejoin")
        payload = {
            "nodeId": device.nwk.upper(),
            "deviceState": 16,
            "deviceType": "0x00FF",
            "timeSinceLastMessage": 0,
            "deviceEndpoint": {
                "eui64": device.mac.upper(),
                "endpoint": 0,
                "clusterInfo": [],
            },
            "firstjoined": 1,
        }
        await self.mqtt.publish(f"gw/{self.ieee}/devicejoined", payload)

    async def silabs_bind(self, bind_from: XDevice, bind_to: XDevice):
        cmd = []
        for cluster in ["on_off", "level", "light_color"]:
            cmd += silabs.zdo_bind(
                bind_from.nwk, 1, cluster, bind_from.mac[2:], bind_to.mac[2:]
            )
        await self.mqtt.publish(f"gw/{self.ieee}/commands", {"commands": cmd})

    async def silabs_unbind(self, bind_from: XDevice, bind_to: XDevice):
        cmd = []
        for cluster in ["on_off", "level", "light_color"]:
            cmd += silabs.zdo_unbind(
                bind_from.nwk, 1, cluster, bind_from.mac[2:], bind_to.mac[2:]
            )
        await self.mqtt.publish(f"gw/{self.ieee}/commands", {"commands": cmd})

    async def silabs_leave(self, device: XDevice):
        cmd = silabs.zdo_leave(device.nwk)
        await self.mqtt.publish(f"gw/{self.ieee}/commands", {"commands": cmd})


def parse_version(value: str) -> int:
    """Support version `0.0.0_0017`."""
    try:
        if "_" in value:
            _, value = value.split("_")
        return int(value)
    except Exception:
        return 0
