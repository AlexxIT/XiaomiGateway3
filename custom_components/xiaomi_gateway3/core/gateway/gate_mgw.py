import re
from typing import Optional

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

MODEL = "lumi.gateway.mgl03"


class GateMGW(
    OpenmiioGateway,
    MIoTGateway,
    LumiGateway,
    MeshGateway,
    BLEGateway,
    SilabsGateway,
    Z3Gateway,
):
    async def gw3_read_device(self, sh: shell.ShellMGW):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def gw3_prepare_gateway(self, sh: shell.ShellMGW):
        # run all inits from subclasses
        self.openmiio_init()
        self.miot_init()  # GW3 and Mesh depends on MIoT
        self.silabs_init()
        self.lumi_init()
        self.mesh_init()
        self.ble_init()
        self.z3_init()

        if self.available is None and self.did is None:
            await self.gw3_read_device(sh)

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        return True

    async def gw3_send_lock(self, enable: bool) -> bool:
        try:
            async with shell.Session(self.host) as sh:
                await sh.lock_firmware(enable)
                locked = await sh.check_firmware_lock()
                return enable == locked
        except Exception as e:
            self.error(f"Can't set firmware lock", e)
            return False

    async def gw3_read_lock(self) -> Optional[bool]:
        try:
            async with shell.Session(self.host) as sh:
                return await sh.check_firmware_lock()
        except Exception as e:
            self.error(f"Can't get firmware lock", e)

    async def alarm(self, params: str):
        """Params = `123,1` (duration in seconds + volume = 1-3)"""
        params = (
            "start_alarm," + params
            if re.match(r"^\d+,[123]$", params)
            else "stop_alarm"
        )
        await self.mqtt.publish(
            "miio/command", {"_to": 1, "method": "local.status", "params": params}
        )
