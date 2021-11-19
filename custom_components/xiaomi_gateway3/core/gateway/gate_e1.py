from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB
from .lumi import LumiGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY
from ..mini_mqtt import MQTTMessage

MODEL = "lumi.gateway.aqcn02"


class GateE1(LumiGateway, SilabsGateway, Z3Gateway):
    def e1_init(self):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.e1_mqtt_publish)

    async def e1_read_device(self, sh: shell.ShellE1):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        self.devices[self.did] = device = XDevice(
            GATEWAY, MODEL, did=self.did, mac=mac,
        )
        device.extra = {"fw_ver": sh.ver}
        self.add_device(device)

    async def e1_prepare_gateway(self, sh: shell.ShellE1):
        self.e1_init()
        self.silabs_init()
        self.lumi_init()
        # self.z3_init()

        ps = await sh.get_running_ps()

        if "/tmp/mosquitto -d" not in ps:
            self.debug("Run public mosquitto")
            await sh.run_public_mosquitto()

        # if "ntpd" not in ps:
        #     # run NTPd for sync time
        #     await sh.run_ntpd()

        if self.available is None and self.did is None:
            await self.e1_read_device(sh)

        await self.dispatcher_send(
            SIGNAL_PREPARE_GW, sh=sh
        )

        n = await sh.apply_patches(ps)
        self.debug(f"Applied {n} patches to daemons")

        return True

    async def e1_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic.endswith('/heartbeat'):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)
