import asyncio
import time
from typing import Optional

from .base import SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB, SIGNAL_TIMER
from .ble import BLEGateway
from .lumi import LumiGateway
from .mesh import MeshGateway
from .miot import MIoTGateway, decode_miio_json
from .silabs import SilabsGateway
from .z3 import Z3Gateway
from .. import shell
from ..device import XDevice, GATEWAY
from ..mini_mqtt import MQTTMessage

MODEL = "lumi.gateway.mgl03"


class GateGW3(
    MIoTGateway, LumiGateway, MeshGateway, BLEGateway, SilabsGateway, Z3Gateway
):
    gw3_ts = 0

    def gw3_init(self):
        # self.dispatcher_connect(SIGNAL_MQTT_CON, self.gw3_mqtt_connect)
        # self.dispatcher_connect(SIGNAL_MQTT_DIS, self.gw3_mqtt_disconnect)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.gw3_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.gw3_timer)

    async def gw3_read_device(self, sh: shell.ShellGw3):
        self.did = await sh.get_did()
        mac = await sh.get_wlan_mac()
        device = self.devices.get(self.did)
        if not device:
            device = XDevice(GATEWAY, MODEL, self.did, mac)
            device.extra = {"fw_ver": sh.ver}
        self.add_device(self.did, device)

    async def gw3_prepare_gateway(self, sh: shell.ShellGw3):
        # run all inits from subclasses
        self.miot_init()  # GW3 and Mesh depends on MIoT
        self.gw3_init()
        self.silabs_init()
        self.lumi_init()
        self.mesh_init()
        self.ble_init()
        self.z3_init()

        ps = await sh.get_running_ps()

        if "mosquitto -d" not in ps:
            self.debug("Run public mosquitto")
            await sh.run_public_mosquitto()

        if "ntpd" not in ps:
            # run NTPd for sync time
            await sh.run_ntpd()

        if self.available is None and self.did is None:
            await self.gw3_read_device(sh)

        # global patch from GW3, BLE and Mesh
        sh.patch_miio_mqtt()

        if not self.zha_mode:
            # buzzer problem only in MiHome mode
            if self.options.get('buzzer'):
                self.debug("Disable Buzzer")
                sh.patch_disable_buzzer()

            if self.options.get('memory'):
                self.debug("Init Zigbee in memory storage")
                sh.patch_memory_zigbee()

        elif await sh.check_zigbee_tcp():
            self.debug("Init ZHA mode")
            sh.patch_zigbee_tcp()

        else:
            self.error("Can't run ZHA mode")
            return False

        await self.dispatcher_send(SIGNAL_PREPARE_GW, sh=sh)

        if sh.ver >= "1.4.7_0000":
            n = await sh.apply_patches(ps)
            self.debug(f"Applied {n} patches to daemons")
        else:
            await sh.patch_miio_mqtt_fw146(ps)
            self.warning(f"Firmware {sh.ver} support is very limited!")

        return True

    # async def gw3_mqtt_connect(self):
    #     # change gateway online state
    #     self.device.update({GATEWAY: True})
    #     await self.gw3_update_time_offset()

    # async def gw3_mqtt_disconnect(self):
    #     # change gateway online state
    #     self.device.update({GATEWAY: False})

    async def gw3_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == 'log/miio':
            payload = decode_miio_json(msg.payload, b'event.gw.heartbeat')
            if payload:
                payload = payload[0]['params'][0]
                payload = self.device.decode(GATEWAY, payload)
                self.device.update(payload)

                # time offset may changed right after gw.heartbeat
                await self.gw3_update_time_offset()

        elif msg.topic.endswith('/heartbeat'):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)

    async def gw3_timer(self, ts: float):
        if ts < self.gw3_ts:
            return
        await self.gw3_update_serial_stats()
        self.gw3_ts = ts + 300  # 5 min

    def _time_delta(self) -> float:
        t = shell.ntp_time(self.host)
        return t - time.time() if t else 0

    async def gw3_update_time_offset(self):
        self.time_offset = await asyncio.get_event_loop().run_in_executor(
            None, self._time_delta
        )
        self.debug(f"Gateway time offset: {self.time_offset}")

    async def gw3_update_serial_stats(self):
        try:
            async with shell.Session(self.host) as session:
                sh = await session.login()
                serial = await sh.read_file('/proc/tty/driver/serial')
                payload = self.device.decode(
                    GATEWAY, {"serial": serial.decode()}
                )
                self.device.update(payload)
        except Exception as e:
            self.warning("Can't update gateway stats", e)

    async def gw3_memory_sync(self):
        try:
            async with shell.Session(self.host) as session:
                sh = await session.login()
                await sh.memory_sync()
        except Exception as e:
            self.error(f"Can't memory sync", e)

    async def gw3_send_lock(self, enable: bool) -> bool:
        try:
            async with shell.Session(self.host) as session:
                sh = await session.login()
                await sh.lock_firmware(enable)
                locked = await sh.check_firmware_lock()
                return enable == locked
        except Exception as e:
            self.error(f"Can't set firmware lock", e)
            return False

    async def gw3_read_lock(self) -> Optional[bool]:
        try:
            async with shell.Session(self.host) as session:
                sh = await session.login()
                return await sh.check_firmware_lock()
        except Exception as e:
            self.error(f"Can't get firmware lock", e)
