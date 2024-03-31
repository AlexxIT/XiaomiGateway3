import asyncio
import time

from .base import XGateway
from ..const import BLE, MESH
from ..device import XDevice
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MIoTGateway(XGateway):
    def miot_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic in ("miio/report", "central/report"):
            if b'"properties_changed"' in msg.payload:
                self.miot_process_properties(msg.json["params"], from_cache=False)
            elif b'"event_occured"' in msg.payload:
                self.miot_process_event(msg.json["params"])
        elif msg.topic == "miio/command_ack":
            # check if it is response from `get_properties` command
            result = msg.json.get("result")
            if isinstance(result, list) and any(
                "did" in i and "siid" in i and "value" in i
                for i in result
                if isinstance(i, dict)
            ):
                self.miot_process_properties(result, from_cache=True)

    def miot_process_properties(self, params: list, from_cache: bool):
        """Can receive multiple properties from multiple devices.
        data = [{'did':123,'siid':2,'piid':1,'value':True,'tid':158}]
        """
        ts = int(time.time())

        # convert miio response format to multiple responses in lumi format
        devices: dict[str, list] = {}
        for item in params:
            if not (device := self.devices.get(item["did"])):
                continue

            if from_cache:
                # won't update last_seen for messages from_cache
                # AND skip this messages if device not in last_seen
                # but only for devices with available_timeout
                if self.device not in device.last_seen and device.type in (BLE, MESH):
                    continue
            else:
                device.on_keep_alive(self, ts)

            if (seq := item.get("tid")) is not None:
                if seq == device.extra.get("seq"):
                    continue
                device.extra["seq"] = seq

            devices.setdefault(item["did"], []).append(item)

        for did, params in devices.items():
            device = self.devices[did]
            device.on_report(params, self, ts)
            if self.stats_domain and device.type in (BLE, MESH):
                device.dispatch({device.type: ts})

    def miot_process_event(self, item: dict):
        # {"did":"123","siid":8,"eiid":1,"tid":123,"ts":123,"arguments":[]}
        device = self.devices.get(item["did"])
        if not device:
            return

        ts = device.on_keep_alive(self)

        if (seq := item.get("tid")) is not None:
            if seq == device.extra.get("seq"):
                return
            device.extra["seq"] = seq

        device.on_report(item, self, ts)
        if self.stats_domain and device.type in (BLE, MESH):
            device.dispatch({device.type: ts})

    async def miot_send(self, device: XDevice, payload: dict):
        assert payload["method"] in ("set_properties", "get_properties"), payload

        # check if we can send command via any second gateway
        gw2 = next((gw for gw in device.gateways if gw != self and gw.available), None)
        if gw2:
            await self.mqtt_publish_multiple(device, payload, gw2)
        else:
            await self.mqtt.publish("miio/command", payload)

    async def mqtt_publish_multiple(
        self, device: XDevice, payload: dict, gw2, delay: float = 1.0
    ):
        fut = asyncio.get_event_loop().create_future()
        device.add_listener(fut.set_result)
        await self.mqtt.publish("miio/command", payload)
        try:
            async with asyncio.timeout(delay):
                await fut
        except TimeoutError:
            await gw2.mqtt.publish("miio/command", payload)
        finally:
            device.remove_listener(fut.set_result)
