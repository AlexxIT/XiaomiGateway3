import asyncio
import re

from . import base

CHECK_FIRMWARE = "/data/busybox lsattr /data/firmware/firmware_ota.bin"
LOCK_FIRMWARE = "mkdir -p /data/firmware && touch /data/firmware/firmware_ota.bin && /data/busybox chattr +i /data/firmware/firmware_ota.bin"
UNLOCK_FIRMWARE = "/data/busybox chattr -i /data/firmware/firmware_ota.bin"

RUN_FTP = "/data/busybox tcpsvd -E 0.0.0.0 21 /data/busybox ftpd -w &"

# c create, z gzip, O stdout, C change DIR
TAR_DATA = "tar -czO /data/miio/mible_local.db* /data/silicon_zigbee_host/*.txt /data/zigbee /data/zigbee_gw 2>/dev/null | base64"

URL_BUSYBOX = "https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel"
MD5_BUSYBOX = "099137899ece96f311ac5ab554ea6fec"


class ShellMGW(base.ShellMultimode):
    model = "mgw"

    async def login(self):
        self.writer.write(b"admin\n")

        coro = self.reader.readuntil(b"\r\n# ")
        raw = await asyncio.wait_for(coro, timeout=3)
        if b"Password:" in raw:
            raise Exception("Telnet with password don't supported")

    async def prepare(self):
        await self.exec("stty -echo")

    async def get_running_ps(self) -> str:
        return await self.exec("ps -ww | grep -v ' 0 SW'")

    async def run_ftp(self):
        if await self.check_bin("busybox", MD5_BUSYBOX, URL_BUSYBOX):
            await self.exec(RUN_FTP)

    async def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        resp = await self.exec(CHECK_FIRMWARE)
        return "-i-" in resp

    async def lock_firmware(self, enable: bool):
        if await self.check_bin("busybox", MD5_BUSYBOX, URL_BUSYBOX):
            command = LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE
            await self.exec(command)

    async def prevent_unpair(self):
        await self.exec("killall zigbee_gw")

    async def tar_data(self) -> str:
        raw = await self.exec(TAR_DATA)
        return raw.replace("\r\n", "")

    async def get_version(self):
        raw = await self.read_file("/etc/rootfs_fw_info")
        m = re.search(r"version=([0-9._]+)", raw.decode())
        self.ver = m[1]

    async def get_token(self) -> str:
        raw = await self.read_file("/data/miio/device.token")
        return raw.rstrip().hex()

    async def get_did(self):
        raw = await self.read_file("/data/miio/device.conf")
        m = re.search(r"did=(\d+)", raw.decode())
        return m[1]

    async def get_miio_info(self) -> dict:
        raw = await self.read_file("/data/miio/device.conf")
        m = re.findall(r"(did|key|mac|model)=(\S+)", raw.decode())
        return {**dict(m), "token": await self.get_token()}

    async def get_wlan_mac(self) -> str:
        raw = await self.read_file("/sys/class/net/wlan0/address")
        return raw.decode().rstrip().replace(":", "")

    @property
    def mesh_db(self) -> str:
        return "/data/miio/mible_local.db"

    @property
    def mesh_group_table(self) -> str:
        if self.ver >= "1.4.7_0160":
            return "mesh_group_v3"
        elif self.ver >= "1.4.6_0043":
            return "mesh_group_v1"
        else:
            return "mesh_group"

    @property
    def mesh_device_table(self) -> str:
        return "mesh_device_v3" if self.ver >= "1.4.7_0160" else "mesh_device"

    @property
    def openmiio_md5(self) -> str:
        return base.OPENMIIO_MD5_MIPS

    @property
    def openmiio_url(self) -> str:
        return base.OPENMIIO_URL_MIPS
