from typing import Dict, Optional

from .base import GatewayBase, SIGNAL_MQTT_PUB
from .. import utils
from ..device import XDevice
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MIoTGateway(GatewayBase):
    def miot_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.miot_mqtt_publish)

    async def miot_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == 'log/miio':
            for data in utils.decode_miio_json(
                    msg.payload, b'properties_changed'
            ):
                await self.miot_process_data(data["params"])

    async def miot_process_data(self, data: list):
        """Can receive multiple properties from multiple devices.
           data = [{'did':123,'siid':2,'piid':1,'value:True}]
        """
        # convert miio response format to multiple responses in lumi format
        devices: Dict[str, Optional[list]] = {}
        for item in data:
            if item['did'] not in self.devices:
                continue
            devices.setdefault(item['did'], []).append(item)

        for did, payload in devices.items():
            device = self.devices[did]
            payload = device.decode_miot(payload)
            device.update(payload)

    async def miot_send(self, device: XDevice, payload: dict) -> bool:
        assert "mi_spec" in payload, payload
        self.debug_device(device, "send", payload, tag="MIOT")
        for item in payload["mi_spec"]:
            item["did"] = device.did
        # MIoT properties changes should return in
        resp = await self.miio.send("set_properties", payload["mi_spec"])
        return "result" in resp

    async def miot_read(self, device: XDevice, payload: dict) -> Optional[dict]:
        assert "mi_spec" in payload, payload
        self.debug_device(device, "read", payload, tag="MIOT")
        for item in payload["mi_spec"]:
            item["did"] = device.did
        resp = await self.miio.send("get_properties", payload["mi_spec"])
        if "result" not in resp:
            return None
        return device.decode_miot(resp['result'])
