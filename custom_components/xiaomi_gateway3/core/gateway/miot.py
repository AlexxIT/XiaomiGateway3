import json
import re
from typing import Dict, List, Optional

from .base import GatewayBase, SIGNAL_MQTT_PUB
from ..device import XDevice
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MIoTGateway(GatewayBase):
    def miot_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.miot_mqtt_publish)

    async def miot_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == 'log/miio':
            for data in decode_miio_json(
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
        return resp and "result" in resp

    async def miot_read(self, device: XDevice, payload: dict) \
            -> Optional[dict]:
        assert "mi_spec" in payload, payload
        self.debug_device(device, "read", payload, tag="MIOT")
        for item in payload["mi_spec"]:
            item["did"] = device.did
        resp = await self.miio.send("get_properties", payload["mi_spec"])
        if resp is None or "result" not in resp:
            return None
        return device.decode_miot(resp['result'])


# new miio adds colors to logs
RE_JSON1 = re.compile(b'msg:(.+) length:([0-9]+) bytes')
RE_JSON2 = re.compile(b'{.+}')
EMPTY_RESPONSE = []


def decode_miio_json(raw: bytes, search: bytes) -> List[dict]:
    """There can be multiple concatenated json on one line. And sometimes the
    length does not match the message."""
    if search not in raw:
        return EMPTY_RESPONSE
    m = RE_JSON1.search(raw)
    if m:
        length = int(m[2])
        raw = m[1][:length]
    else:
        m = RE_JSON2.search(raw)
        raw = m[0]
    items = raw.replace(b'}{', b'}\n{').split(b'\n')
    return [json.loads(raw) for raw in items if search in raw]
