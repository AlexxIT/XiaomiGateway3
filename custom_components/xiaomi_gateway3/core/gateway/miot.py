from typing import Dict, Optional

from .base import GatewayBase, SIGNAL_MQTT_PUB
from ..device import XDevice
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MIoTGateway(GatewayBase):
    def miot_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.miot_mqtt_publish)

    async def miot_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic in ("miio/report", "central/report"):
            if b'"properties_changed"' in msg.payload:
                await self.miot_process_properties(msg.json["params"])
            elif b'"event_occured"' in msg.payload:
                await self.miot_process_event(msg.json["params"])

    async def miot_process_properties(self, data: list):
        """Can receive multiple properties from multiple devices.
        data = [{'did':123,'siid':2,'piid':1,'value:True}]
        """
        # convert miio response format to multiple responses in lumi format
        devices: Dict[str, Optional[list]] = {}
        for item in data:
            device = self.devices.get(item["did"])
            if not device:
                continue

            if seq := item.get("tid"):
                if device.extra.get("seq") == seq:
                    return
                device.extra["seq"] = seq

            devices.setdefault(item["did"], []).append(item)

        for did, payload in devices.items():
            device = self.devices[did]
            payload = device.decode_miot(payload)
            device.update(payload)

    async def miot_process_event(self, data: dict):
        # {"did":"123","siid":8,"eiid":1,"tid":123,"ts":123,"arguments":[]}
        device = self.devices.get(data["did"])
        if not device:
            return

        if seq := data.get("tid"):
            if device.extra.get("seq") == seq:
                return
            device.extra["seq"] = seq

        payload = device.decode_miot([data])
        device.update(payload)

    async def miot_send(self, device: XDevice, payload: dict) -> bool:
        assert "mi_spec" in payload, payload
        self.debug_device(device, "send", payload, tag="MIOT")
        for item in payload["mi_spec"]:
            item["did"] = device.did
        # MIoT properties changes should return in
        resp = await self.miio_send("set_properties", payload["mi_spec"])
        return resp and "result" in resp

    async def miot_read(self, device: XDevice, payload: dict) -> Optional[dict]:
        assert "mi_spec" in payload, payload
        self.debug_device(device, "read", payload, tag="MIOT")
        for item in payload["mi_spec"]:
            item["did"] = device.did
        resp = await self.miio_send("get_properties", payload["mi_spec"])
        if resp is None or "result" not in resp:
            return None
        return device.decode_miot(resp["result"])
