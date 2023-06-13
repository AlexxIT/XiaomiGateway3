from .base import SIGNAL_PREPARE_GW
from .ble import BLEGateway
from .lumi import LumiGateway
from .mesh import MeshGateway
from .miot import MIoTGateway
from .openmiio import OpenmiioGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY

MODEL = "lumi.gateway.mcn001"


class GateMGW2(
    OpenmiioGateway,
    MIoTGateway,
    LumiGateway,
    MeshGateway,
    BLEGateway,
    SilabsGateway,
    Z3Gateway,
):
    async def mgw2_prepare_gateway(self, sh: shell.ShellMGW2):
        self.openmiio_init()
        self.miot_init()  # Gateway and Mesh depends on MIoT
        self.silabs_init()
        self.lumi_init()
        self.mesh_init()
        self.ble_init()
        self.z3_init()

        if self.available is None and self.did is None:
            await self.mgw2_read_device(sh)

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        return True

    async def mgw2_read_device(self, sh: shell.ShellMGW2):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        mac2 = await sh.get_lan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver, "mac2": mac2}
        self.add_device(self.did, device)
