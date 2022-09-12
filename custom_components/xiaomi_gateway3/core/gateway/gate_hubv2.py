from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB, SIGNAL_TIMER
from .lumi import LumiGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY
from ..mini_mqtt import MQTTMessage

MODEL = "lumi.gateway.mcn001"


class GateHubV2(LumiGateway, SilabsGateway, Z3Gateway):
    hubv2_ts = 0

    def hubv2_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.hubv2_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.hubv2_timer)

    async def hubv2_read_device(self, sh: shell.ShellHubV2):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def hubv2_prepare_gateway(self, sh: shell.ShellHubV2):
        self.hubv2_init()
        self.silabs_init()
        self.lumi_init()
        self.z3_init()

        ps = await sh.get_running_ps()

        if "/tmp/mosquitto -d" not in ps:
            self.debug("Run public mosquitto")
            await sh.run_public_mosquitto()

        # if "ntpd" not in ps:
        #     # run NTPd for sync time
        #     await sh.run_ntpd()

        if self.available is None and self.did is None:
            await self.hubv2_read_device(sh)

        sh.patch_miio_mqtt()

        await self.dispatcher_send(
            SIGNAL_PREPARE_GW, sh=sh
        )

        n = await sh.apply_patches(ps)
        self.debug(f"Applied {n} patches to daemons")

        return True

    async def hubv2_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith('/heartbeat'):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)

    async def hubv2_timer(self, ts: float):
        if ts < self.hubv2_ts:
            return
        await self.hubv2_update_stats()
        self.hubv2_ts = ts + 300  # 5 min

    async def hubv2_update_stats(self):
        try:
            async with shell.Session(self.host) as session:
                sh = await session.login()
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
