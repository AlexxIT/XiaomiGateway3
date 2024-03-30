import json
import time

from .base import XGateway
from ..const import MATTER
from ..device import XDevice
from ..mini_mqtt import MQTTMessage
from ..shell.shell_mgw2 import ShellMGW2


class MatterGateway(XGateway):
    async def matter_read_devices(self, sh: ShellMGW2):
        raw = await sh.read_file("/data/matter/certification/device.json")
        for item in json.loads(raw):
            did = item["did"]
            device = self.devices.get(did)
            if not device:
                device = self.init_device(
                    item["model"], did=did, type=MATTER, fw_ver=item["fw_ver"]
                )
            self.add_device(device)

    def matter_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "local/matter/devMsg":
            if b'"properties_changed_v3"' in msg.payload:
                i = msg.payload.index(b'{"method"')
                data = json.loads(msg.payload[i:])
                self.matter_process_devmsg(data["params"])
        elif msg.topic == "local/matter/response":
            if b"properties_changed_v3" in msg.payload:
                i = msg.payload.index(b'{"result"')
                data = json.loads(msg.payload[i:].rstrip(b"\x00"))
                self.matter_process_devmsg(data["result"][0]["RPC"]["params"])

    def matter_process_devmsg(self, params: list[dict]):
        devices: dict[str, list] = {}
        for item in params:
            if item["did"] not in self.devices:
                continue
            devices.setdefault(item["did"], []).append(item)

        ts = int(time.time())

        for did, params in devices.items():
            device = self.devices[did]
            device.on_keep_alive(self, ts)
            device.on_report(params, self, ts)
            if self.stats_domain:
                device.dispatch({MATTER: ts})

    async def matter_send(self, device: XDevice, method: str, data: dict):
        assert method in ("set_properties_v3", "get_properties_v3")
        id = int(time.time())
        payload = {
            "id": id,
            "method": method,
            "params": [{"did": device.did, **i} for i in data["params"]],
        }
        payload = json.dumps(payload, separators=(",", ":"))
        payload = encode(0, id) + encode(1, "local/ot/rpcResponse") + encode(2, payload)

        await self.mqtt.publish("local/ot/rpcDown/" + method, payload)


def encode(pos: int, value: int | str) -> bytes:
    if isinstance(value, int):
        return b"\x04\x00\x00\x00" + bytes([pos]) + value.to_bytes(4, "little")
    if isinstance(value, str):
        value = value.encode() + b"\x00"
        return len(value).to_bytes(4, "little") + bytes([pos]) + value
