import json

from .base import GatewayBase, SIGNAL_PREPARE_GW, SIGNAL_MQTT_CON, SIGNAL_MQTT_PUB
from .. import shell
from ..converters import GATEWAY
from ..device import XDevice, ZIGBEE
from ..mini_mqtt import MQTTMessage


class LumiGateway(GatewayBase):
    did: str = None  # filled by MainGateway

    zigbee_pair_model = None

    pair_payload = None
    pair_payload2 = None

    def lumi_init(self):
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.lumi_prepare_gateway)
        # self.dispatcher_connect(SIGNAL_MQTT_CON, self.lumi_mqtt_connect)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.lumi_mqtt_publish)

    async def lumi_read_devices(self, sh: shell.TelnetShell):
        # 2. Read zigbee devices
        raw = await sh.read_file("/data/zigbee/device.info")
        lumi = json.loads(raw)["devInfo"]

        for item in lumi:
            did = item["did"]
            device = self.devices.get(did)
            if not device:
                # adds leading zeroes to mac
                mac = f"0x{item['mac'][2:]:>016s}"
                device = XDevice(ZIGBEE, item["model"], did, mac, item["shortId"])
                device.extra = {"fw_ver": item["appVer"]}
                # 'hw_ver': item['hardVer'],
                # 'mod_ver': item['model_ver'],

            self.add_device(did, device)

    async def lumi_prepare_gateway(self, sh: shell.TelnetShell):
        if self.available is None:
            await self.lumi_read_devices(sh)

        uptime = await sh.read_file("/proc/uptime | cut -f1 -d.")
        if int(uptime) >= 3600:
            self.dispatcher_connect(SIGNAL_MQTT_CON, self.lumi_mqtt_connect)

    async def lumi_mqtt_connect(self):
        payload = {"params": [{"res_name": "8.0.2102"}]}
        for device in self.filter_devices("zigbee"):
            await self.lumi_read(device, payload)

    async def lumi_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "zigbee/send":
            await self.lumi_process_lumi(msg.json)

    async def lumi_send(self, device: XDevice, payload: dict):
        assert "params" in payload or "mi_spec" in payload, payload
        # self.debug_device(device, "send", payload, tag="LUMI")
        did = device.did if device.type != GATEWAY else "lumi.0"
        payload.update({"cmd": "write", "did": did})
        await self.mqtt.publish("zigbee/recv", payload)

    async def lumi_read(self, device: XDevice, payload: dict):
        assert "params" in payload or "mi_spec" in payload, payload
        # self.debug_device(device, "read", payload, tag="LUMI")
        payload["did"] = device.did if device.type != GATEWAY else "lumi.0"
        payload.setdefault("cmd", "read")
        await self.mqtt.publish("zigbee/recv", payload)

    async def lumi_process_lumi(self, data: dict):
        # cmd:
        # - heartbeat - from power device every 5-10 min, from battery - 55 min
        # - report - new state from device
        # - read, write - action from Hass, MiHome or Gateway software
        # - read_rsp, write_rsp - gateway execute command (device may not
        #   receive it)
        # - write_ack - response from device (device receive command)
        if data["cmd"] == "heartbeat":
            data = data["params"][0]
        elif data["cmd"] in ("report", "read_rsp"):
            pass
        elif data["cmd"] == "write_rsp":
            # process write response only from Gateway
            if data["did"] != "lumi.0":
                return
        else:
            return

        did = data["did"] if data["did"] != "lumi.0" else self.did

        # skip without callback and without data
        if did not in self.devices:
            return

        device: XDevice = self.devices[did]
        # support multiple spec in one response
        for k in ("res_list", "params", "results", "mi_spec"):
            if k not in data:
                continue

            payload = device.decode_lumi(data[k])
            device.update(payload)

            # no time in device add command
            # ts = round(time.time() - data['time'] * 0.001 + self.time_offset, 2) \
            #     if 'time' in data else '?'
            # self.debug(f"{device.did} {device.model} <= {payload} [{ts}]")
            self.debug_device(device, "recv", payload, tag="LUMI")
