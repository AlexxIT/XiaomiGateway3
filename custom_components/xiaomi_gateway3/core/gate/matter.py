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
        if not raw.startswith(b"["):
            return
        for item in json.loads(raw):
            did = item["did"]
            device = self.devices.get(did)
            if not device:
                device = self.init_device(
                    item["model"], did=did, type=MATTER, fw_ver=item["fw_ver"]
                )
            self.add_device(device)

    def matter_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "local/matter/response":
            if b'"properties_changed_v3"' in msg.payload:
                data = decode(msg.payload)
                self.matter_process_properties(data["result"][0]["RPC"]["params"])
        elif msg.topic == "local/ot/rpcReq":
            # {"method":"_sync.matter_dev_status","params":{"dev_list":null}}
            if b'"_sync.matter_dev_status"' in msg.payload:
                data = decode(msg.payload)
                if dev_list := data["params"].get("dev_list"):
                    self.matter_process_dev_status(dev_list)

    def matter_process_properties(self, params: list[dict]):
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

    def matter_process_dev_status(self, data: list[dict]):
        ts = int(time.time())

        for item in data:
            if device := self.devices.get(item["did"]):
                if item["status"] == "online":
                    device.extra["rssi"] = item["rssi"]
                    device.on_keep_alive(self, ts)
                else:
                    device.last_seen.pop(self.device, None)
                    device.update()

    async def matter_send(self, device: XDevice, payload: dict):
        assert payload["method"] in ("set_properties_v3", "get_properties_v3"), payload
        assert "params" in payload, payload
        payload["id"] = id = int(time.time())
        data = json.dumps(payload, separators=(",", ":"))
        data = encode(0, id) + encode(1, "local/ot/rpcResponse") + encode(2, data)
        await self.mqtt.publish("local/ot/rpcDown/" + payload["method"], data)


def encode(pos: int, value: int | str) -> bytes:
    if isinstance(value, int):
        return b"\x04\x00\x00\x00" + bytes([pos]) + value.to_bytes(4, "little")
    if isinstance(value, str):
        value = value.encode() + b"\x00"
        return len(value).to_bytes(4, "little") + bytes([pos]) + value


def decode(data: bytes) -> dict:
    i = data.index(b'\x00\x00\x02{"') + 3
    return json.loads(data[i:].rstrip(b"\x00"))
