from .base import SIGNAL_PREPARE_GW
from .lumi import LumiGateway
from .openmiio import OpenmiioGateway
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY

MODEL = "lumi.gateway.aqcn02"


class GateE1(OpenmiioGateway, LumiGateway, SilabsGateway, Z3Gateway):
    async def e1_read_device(self, sh: shell.ShellE1):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def e1_prepare_gateway(self, sh: shell.ShellE1):
        self.openmiio_init()
        self.silabs_init()
        self.lumi_init()
        self.z3_init()

        if self.available is None and self.did is None:
            await self.e1_read_device(sh)

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        return True
