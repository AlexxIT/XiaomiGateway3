from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB
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
    async def mgw2_prepare_gateway(self, sh: shell.ShellMGW2):
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.mgw2_mqtt_publish)

        self.miot_init()  # Gateway and Mesh depends on MIoT
        self.silabs_init()
        self.lumi_init()
        self.mesh_init()
        self.ble_init()

        ps = await sh.get_running_ps()

        if "/tmp/mosquitto -d" not in ps:
            self.debug("Run public mosquitto")
            await sh.run_public_mosquitto()

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

    async def ble_prepare_gateway(self, sh: shell.ShellMGW):
        if self.available is None:
            await self.ble_read_devices(sh)
