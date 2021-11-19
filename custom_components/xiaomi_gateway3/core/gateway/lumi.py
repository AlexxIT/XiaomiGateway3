import json
import time
from typing import List

from .base import GatewayBase, SIGNAL_PREPARE_GW, SIGNAL_MQTT_CON, \
    SIGNAL_MQTT_PUB
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
        if self.zha_mode:
            return
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.lumi_prepare_gateway)
        self.dispatcher_connect(SIGNAL_MQTT_CON, self.lumi_mqtt_connect)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.lumi_mqtt_publish)

    @property
    def zigbee_devices(self) -> List[XDevice]:
        return [
            device for device in self.devices.values()
            if device.type == ZIGBEE and self in device.gateways
        ]

    async def lumi_read_devices(self, sh: shell.TelnetShell):
        # 2. Read zigbee devices
        raw = await sh.read_file('/data/zigbee/device.info')
        lumi = json.loads(raw)['devInfo']

        for item in lumi:
            did = item["did"]
            device = self.devices.get(did)
            if not device:
                # adds leading zeroes to mac
                mac = f"0x{item['mac'][2:]:>016s}"
                self.devices[did] = device = XDevice(
                    ZIGBEE, item['model'], did, mac, item['shortId']
                )
                device.extra = {'fw_ver': item['appVer']}
                # 'hw_ver': item['hardVer'],
                # 'mod_ver': item['model_ver'],

            self.add_device(device)

    async def lumi_prepare_gateway(self, sh: shell.TelnetShell):
        if self.available is None:
            await self.lumi_read_devices(sh)

    async def lumi_mqtt_connect(self):
        payload = {"params": [{"res_name": "8.0.2102"}]}
        for device in self.zigbee_devices:
            await self.lumi_read(device, payload)

    async def lumi_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == 'zigbee/send':
            await self.lumi_process_lumi(msg.json)

    async def lumi_send(self, device: XDevice, payload: dict):
        assert "params" in payload or "mi_spec" in payload, payload
        # self.debug_device(device, "send", payload, tag="LUMI")
        did = device.did if device.type != GATEWAY else "lumi.0"
        payload.update({"cmd": "write", "did": did})
        await self.mqtt.publish('zigbee/recv', payload)

    async def lumi_read(self, device: XDevice, payload: dict):
        assert "params" in payload or "mi_spec" in payload, payload
        # self.debug_device(device, "read", payload, tag="LUMI")
        payload["did"] = device.did if device.type != GATEWAY else "lumi.0"
        payload.setdefault("cmd", "read")
        await self.mqtt.publish('zigbee/recv', payload)

    async def lumi_process_lumi(self, data: dict):
        # heartbeat from power device every 5-10 min, from battery - 55 min
        if data['cmd'] == 'heartbeat':
            data = data['params'][0]
            pkey = 'res_list'
        # report - new state from device
        elif data['cmd'] == 'report':
            pkey = 'params' if 'params' in data else 'mi_spec'
        elif data['cmd'] == 'read_rsp':
            pkey = 'results'
        elif data['cmd'] == 'write_rsp':
            pkey = 'results'
            # process write response only from Gateway
            if data['did'] != 'lumi.0':
                return
        else:
            # rsp - gateway execute command (device may not receive it)
            # ack - response from device (device receive command)
            # 'write', 'write_rsp', 'write_ack', 'read_rsp'
            return

        did = data['did'] if data['did'] != 'lumi.0' else self.did

        # skip without callback and without data
        if did not in self.devices or pkey not in data:
            return

        device: XDevice = self.devices[did]
        payload = device.decode_lumi(data[pkey])

        # set device available on any message except online=False
        device.available = payload.pop('online', True)

        if not payload:
            return

        device.last_seen = time.time()
        device.update(payload)

        # no time in device add command
        # ts = round(time.time() - data['time'] * 0.001 + self.time_offset, 2) \
        #     if 'time' in data else '?'
        # self.debug(f"{device.did} {device.model} <= {payload} [{ts}]")
        self.debug_device(device, "recv", payload, tag="LUMI")
