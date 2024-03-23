import json

from .base import XGateway
from ..const import ZIGBEE, GATEWAY
from ..device import XDevice, XDeviceExtra
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
                    "ieee": as_ieee(item["mac"][2:]),  # adds leading zeroes to mac
                    "nwk": item["shortId"],
                    "fw_ver": item["appVer"],
                    "hw_ver": item["hardVer"],
                }
                if did in xiaomi_did:
                    extra["cloud_did"] = xiaomi_did[did]
                device = XDevice(item["model"], **extra)

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
            items = data.get("params") or data.get("mi_spec")
        elif cmd == "read_rsp":
            # {"cmd":"read_rsp","did":"lumi","results":[{"res_name":"8.0.2022","value":68,"error_code":0}]}
            items = data.get("results")
        elif cmd == "write_rsp" and data["did"] == "lumi.0":
            # process write response only from Gateway
            # {"cmd":"write_rsp","did":"lumi.0","results":[{"res_name":"8.0.2109","value":60,"error_code":0}]}
            items = data.get("results")
        else:
            return

        if not items:
            return

        did = self.device.did if data["did"] == "lumi.0" else data["did"]
        if device := self.devices.get(did):
            device.on_report(items, self)

    async def lumi_send(self, device: XDevice, command: str, data: dict):
        assert command in ("write", "read")
        assert "params" in data or "mi_spec" in data
        did = device.did if device.type != GATEWAY else "lumi.0"
        # key = next(i for i in ("params", "mi_spec") if i in data)
        # for item in data[key]:
        #     command = "write" if "value" in item else "read"
        #     await self.mqtt.publish(
        #         "zigbee/recv", {"cmd": command, "did": did, key: [item]}
        #     )
        await self.mqtt.publish("zigbee/recv", {"cmd": command, "did": did, **data})


def as_ieee(s: str):
    s = s.rjust(16, "0")
    return (
        f"{s[:2]}:{s[2:4]}:{s[4:6]}:{s[6:8]}:{s[8:10]}:{s[10:12]}:{s[12:14]}:{s[14:]}"
    )
