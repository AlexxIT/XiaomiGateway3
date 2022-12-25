from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB, SIGNAL_TIMER
from .ble import BLEGateway
from .lumi import LumiGateway
from .mesh import MeshGateway
from .miot import MIoTGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY
from ..mini_mqtt import MQTTMessage

MODEL = "lumi.gateway.mcn001"


class GateMGW2(
    MIoTGateway, LumiGateway, MeshGateway, BLEGateway, SilabsGateway, Z3Gateway
):
    mgw2_ts = 0

    def mgw2_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.mgw2_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.mgw2_timer)

    async def mgw2_prepare_gateway(self, sh: shell.ShellMGW2):
        self.mgw2_init()
        self.miot_init()  # Gateway and Mesh depends on MIoT
        self.silabs_init()
        self.lumi_init()
        self.mesh_init()
        self.ble_init()

        msg = await sh.run_openmiio_agent()
        self.debug("openmiio_agent: " + msg)

        if self.available is None and self.did is None:
            await self.mgw2_read_device(sh)

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        return True

    async def mgw2_read_device(self, sh: shell.ShellMGW2):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def mgw2_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith('/heartbeat'):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)

    async def mgw2_timer(self, ts: float):
        if ts < self.mgw2_ts:
            return
        await self.mgw2_update_stats()
        self.mgw2_ts = ts + 300  # 5 min

    async def mgw2_update_stats(self):
        try:
            async with shell.Session(self.host) as sh:
                serial = await sh.read_file(
                    "/proc/tty/driver/ms_uart | sed 's/1:/2=/' | sed 's/2:/1=/' | sed 's/=/:/' | sort -k1 -g"
                )
                free_mem = await sh.read_file(
                    "/proc/meminfo | grep MemFree: | awk '{print $2}'"
                )
                load_avg = await sh.read_file("/proc/loadavg | sed 's/ /|/g'")
                run_time = await sh.read_file("/proc/uptime | cut -f1 -d.")
                rssi = await sh.read_file(
                    "/proc/net/wireless | grep wlan0 | awk '{print $4}' | cut -f1 -d."
                )
                payload = self.device.decode(GATEWAY, {
                    "serial": serial.decode(),
                    "free_mem": int(free_mem),
                    "load_avg": load_avg.decode(),
                    "run_time": int(run_time),
                    "rssi": int(rssi) + 100 if len(rssi) >=1 else 0
                })
                self.device.update(payload)

        except Exception as e:
            self.warning("Can't update gateway stats", e)
