import re
import time

from .base import (
    GatewayBase,
    SIGNAL_PREPARE_GW,
    SIGNAL_MQTT_CON,
    SIGNAL_MQTT_PUB,
    SIGNAL_TIMER,
)
from .. import shell
from ..device import ZIGBEE, XDevice
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class Z3Gateway(GatewayBase):
    ieee: str = None

    z3_parent_scan: float = 0
    # collected data from MQTT topic log/z3 (zigbee console)
    z3_buffer: dict = None

    def z3_init(self):
        if not self.stats_enable:
            return
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.z3_prepare_gateway)
        self.dispatcher_connect(SIGNAL_MQTT_CON, self.z3_mqtt_connect)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.z3_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.z3_timer)

    async def z3_prepare_gateway(self, sh: shell.TelnetShell):
        assert self.ieee, "Z3Gateway depends on SilabsGateway"

    async def z3_mqtt_connect(self):
        # delay first scan
        self.z3_parent_scan = time.time() + 10

    async def z3_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "log/z3":
            await self.z3_process_log(msg.text)

    async def z3_timer(self, ts: float):
        if ts >= self.z3_parent_scan:
            await self.z3_run_parent_scan()

    async def z3_run_parent_scan(self):
        self.debug("Run zigbee parent scan process")

        # block any auto updates in 10 seconds
        self.z3_parent_scan = time.time() + 10

        payload = {
            "commands": [
                {"commandcli": "debugprint all_on"},
                {"commandcli": "plugin device-table print"},
                {"commandcli": "plugin stack-diagnostics child-table"},
                {"commandcli": "plugin stack-diagnostics neighbor-table"},
                {"commandcli": "plugin concentrator print-table"},
                {"commandcli": "debugprint all_off"},
            ]
        }
        await self.mqtt.publish(f"gw/{self.ieee}/commands", payload)

    async def z3_process_log(self, payload: str):
        if payload.startswith("CLI command executed"):
            cmd = payload[22:]
            if cmd == "debugprint all_on" or self.z3_buffer is None:
                # reset all buffers
                self.z3_buffer = {}
            else:
                self.z3_buffer[cmd] = self.z3_buffer["buffer"]

            self.z3_buffer["buffer"] = ""

            if cmd == "plugin concentrator print-table":
                await self.z3_process_parent_scan()

        elif self.z3_buffer:
            self.z3_buffer["buffer"] += payload + "\n"

    async def z3_process_parent_scan(self):
        self.debug("Process zigbee parent scan response")
        try:
            raw = self.z3_buffer["plugin device-table print"]
            dt = re.findall(
                r"\d+ ([A-F0-9]{4}): {2}([A-F0-9]{16}) 0 {2}(\w+) (\d+)", raw
            )

            raw = self.z3_buffer["plugin stack-diagnostics child-table"]
            ct = re.findall(r"\(>\)([A-F0-9]{16})", raw)

            raw = self.z3_buffer["plugin stack-diagnostics neighbor-table"]
            rt = re.findall(r"\(>\)([A-F0-9]{16})", raw)

            raw = self.z3_buffer["plugin concentrator print-table"]
            pt = re.findall(r": (.+?) \(Me\)", raw)
            pt = [i.replace("0x", "").split(" -> ") for i in pt]
            pt = {i[0]: i[1:] for i in pt}

            self.debug(f"Total zigbee devices: {len(dt)}")

            # nwk: FFFF, ieee: FFFFFFFFFFFFFFFF, ago: int
            # state: JOINED, LEAVE_SENT (32)
            for nwk, ieee, state, ago in dt:
                if state == "LEAVE_SENT":
                    continue

                if ieee in ct:
                    type_ = "device"
                elif ieee in rt:
                    type_ = "router"
                elif nwk in pt:
                    type_ = "device"
                else:
                    type_ = "?"

                if nwk in pt:
                    if len(pt[nwk]) > 1:
                        parent = "0x" + pt[nwk][0].lower()
                    else:
                        parent = "-"
                elif ieee in ct:
                    parent = "-"
                else:
                    parent = "?"

                nwk = "0x" + nwk.lower()  # 0xffff

                payload = {
                    # 'eui64': '0x' + ieee,
                    # 'nwk': nwk,
                    # 'ago': int(ago),
                    "type": type_,
                    "parent": parent,
                }

                did = "lumi." + ieee.lstrip("0").lower()
                device = self.devices.get(did)
                if not device:
                    mac = "0x" + ieee.lower()
                    device = XDevice(ZIGBEE, None, did, mac, nwk)
                    self.add_device(did, device)
                    self.debug_device(device, "new unknown device", tag=" Z3 ")
                    continue

                if ZIGBEE not in device.entities:
                    continue

                # the device remains in the gateway database after
                # deletion and may appear on another gw with another nwk
                if nwk == device.nwk:
                    # payload = device.decode(ZIGBEE, payload)
                    device.update(payload)
                else:
                    self.debug(f"Zigbee device with wrong NWK: {ieee}")

            # one hour later
            self.z3_parent_scan = time.time() + 3600

        except Exception as e:
            self.debug(f"Can't update parents", exc_info=e)
