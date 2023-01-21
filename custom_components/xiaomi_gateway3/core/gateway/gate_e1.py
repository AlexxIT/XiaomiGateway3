from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB, SIGNAL_TIMER
from .lumi import LumiGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY
from ..mini_mqtt import MQTTMessage

MODEL = "lumi.gateway.aqcn02"


class GateE1(LumiGateway, SilabsGateway, Z3Gateway):
    e1_ts = 0

    def e1_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.e1_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.e1_timer)

    async def e1_read_device(self, sh: shell.ShellE1):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def e1_prepare_gateway(self, sh: shell.ShellE1):
        self.e1_init()
        self.silabs_init()
        self.lumi_init()
        self.z3_init()

        msg = await sh.run_openmiio_agent()
        self.debug("openmiio_agent: " + msg)

        if self.available is None and self.did is None:
            await self.e1_read_device(sh)

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        return True

    async def e1_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith("/heartbeat"):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)

    async def e1_timer(self, ts: float):
        if ts < self.e1_ts:
            return
        await self.e1_update_stats()
        self.e1_ts = ts + 300  # 5 min

    async def e1_update_stats(self):
        try:
            async with shell.Session(self.host) as sh:
                serial = await sh.read_file(
                    "/proc/tty/driver/ms_uart | grep -v ^0 | sort -r"
                )
                free_mem = await sh.read_file(
                    "/proc/meminfo | grep MemFree: | awk '{print $2}'"
                )
                load_avg = await sh.read_file("/proc/loadavg | sed 's/ /|/g'")
                run_time = await sh.read_file("/proc/uptime | cut -f1 -d.")
                rssi = await sh.read_file(
                    "/proc/net/wireless | grep wlan0 | awk '{print $4}' | cut -f1 -d."
                )
                payload = self.device.decode(
                    GATEWAY,
                    {
                        "serial": serial.decode(),
                        "free_mem": int(free_mem),
                        "load_avg": load_avg.decode(),
                        "run_time": int(run_time),
                        "rssi": int(rssi) + 100,
                    },
                )
                self.device.update(payload)

        except Exception as e:
            self.warning("Can't update gateway stats", e)
