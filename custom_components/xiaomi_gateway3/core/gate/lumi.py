import json
import time

from .base import XGateway
from ..const import ZIGBEE
from ..device import XDevice, XDeviceExtra, hex_to_ieee
from ..mini_mqtt import MQTTMessage
from ..shell.shell_mgw import ShellMGW
from ..shell.shell_mgw2 import ShellMGW2


class LumiGateway(XGateway):
    async def lumi_read_devices(self, sh: ShellMGW | ShellMGW2):
        raw = await sh.read_file("/data/zigbee/device.info")
        lumi = json.loads(raw)["devInfo"]

        xiaomi_did = await sh.read_xiaomi_did()

        for item in lumi:
            did = item["did"]
            device = self.devices.get(did)
            if not device:
                extra: XDeviceExtra = {
                    "did": did,
                    "type": ZIGBEE,
                    "ieee": hex_to_ieee(item["mac"]),
                    "nwk": item["shortId"],
                    "fw_ver": item["appVer"],
                    "hw_ver": item["hardVer"],
                }
                if did in xiaomi_did:
                    extra["cloud_did"] = xiaomi_did[did]
                device = self.init_device(item["model"], **extra)

            self.add_device(device)

    def lumi_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "zigbee/send":
            self.lumi_process_lumi(msg.json)

    def lumi_process_lumi(self, data: dict):
        cmd: str = data["cmd"]
        if cmd == "heartbeat":
            # {"cmd":"heartbeat","params":[{"did":"lumi","res_list":[{"res_name":"8.0.2006","value":46}]}
            data = data["params"][0]
            items = data.get("res_list")
        elif cmd == "report":
            # {"cmd":"report","did":"lumi","params":[{"res_name":"0.3.85","value":129}],"mi_spec":[{"siid":2,"piid":1,"value":129}]}
            items = join_params(data)
        elif cmd == "read_rsp":
            # {"cmd":"read_rsp","did":"lumi","results":[{"res_name":"8.0.2022","value":68,"error_code":0}]}
            # {"cmd":"read_rsp","did":"lumi","mi_spec":[{"siid":5,"piid":2,"value":0,"code":0}]}
            items = join_params(data)
        elif cmd == "write_rsp" and data["did"] == "lumi.0":
            # process write response only from Gateway
            # {"cmd":"write_rsp","did":"lumi.0","results":[{"res_name":"8.0.2109","value":60,"error_code":0}]}
            items = join_params(data)
        else:
            return

        if not items:
            return

        did = self.device.did if data["did"] == "lumi.0" else data["did"]
        if device := self.devices.get(did):
            device.on_report(items, self, int(time.time()))

    async def lumi_send(self, device: XDevice, payload: dict):
        assert payload["cmd"] in ("write", "read"), payload
        for item in payload.get("params", []):
            data = {"cmd": payload["cmd"], "did": payload["did"], "params": [item]}
            await self.mqtt.publish("zigbee/recv", data)
        for item in payload.get("mi_spec", []):
            data = {"cmd": payload["cmd"], "did": payload["did"], "mi_spec": [item]}
            await self.mqtt.publish("zigbee/recv", data)


def join_params(data: dict) -> list | None:
    result = None
    for k in ("params", "results", "mi_spec"):
        if k in data:
            result = result + data[k] if result else data[k]
    return result
